from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import json
import socket

from services.job_search import JobListing, deduplicate_jobs
from services.skill_extractor import extract_skills


REMOTIVE_API_URL = "https://remotive.com/api/remote-jobs"
REMOTIVE_SOURCE_URL = "https://remotive.com/"
REMOTIVE_RESULT_LIMIT = 100
REQUEST_TIMEOUT_SECONDS = 15
MAX_RESPONSE_BYTES = 20 * 1024 * 1024
MAX_LISTINGS = 2_000
INDIA_LOCATIONS = {
    "bengaluru",
    "bangalore",
    "chennai",
    "delhi",
    "guntur",
    "hyderabad",
    "mumbai",
    "pune",
}


class RemoteJobSearchError(Exception):
    """Recoverable Remotive provider errors without leaking response details."""


@dataclass(frozen=True)
class RemoteJobCatalog:
    jobs: tuple[JobListing, ...]
    fetched_at: str


class _TextExtractor(HTMLParser):
    _BLOCK_TAGS = {"br", "div", "h1", "h2", "h3", "h4", "li", "ol", "p", "tr", "ul"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def html_to_text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value)
    return "\n".join(line.strip() for line in "".join(parser.parts).splitlines() if line.strip())


def _safe_https_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value.strip())
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            return None
    except ValueError:
        return None
    return value.strip()


def normalize_remotive_job(record: object, fetched_at: str | None = None) -> JobListing | None:
    """Normalize a Remotive remote listing without inferring unknown job fields."""
    if not isinstance(record, dict):
        return None
    title = record.get("title")
    application_url = _safe_https_url(record.get("url"))
    if not isinstance(title, str) or not title.strip() or application_url is None:
        return None

    description_html = record.get("description")
    description = html_to_text(description_html) if isinstance(description_html, str) else ""
    raw_tags = record.get("tags", [])
    tags = tuple(
        tag.strip()
        for tag in raw_tags
        if isinstance(tag, str) and tag.strip()
    ) if isinstance(raw_tags, list) else ()
    skills = tuple(extract_skills(" ".join((title, description, *tags))))
    job_type = record.get("job_type")
    allowed_types = {"full_time", "part_time", "contract", "freelance", "internship"}
    normalized_type = job_type if isinstance(job_type, str) and job_type in allowed_types else None
    contract_time = normalized_type if normalized_type in {"full_time", "part_time"} else None
    contract_type = normalized_type if normalized_type in {"contract", "freelance", "internship"} else None
    posted_at = record.get("publication_date")
    if not isinstance(posted_at, str) or not posted_at.strip():
        posted_at = None
    salary = record.get("salary")
    salary_display = salary.strip() if isinstance(salary, str) and salary.strip() else None
    required_location = record.get("candidate_required_location")
    required_location = (
        required_location.strip()
        if isinstance(required_location, str) and required_location.strip()
        else "Location not specified by source"
    )
    company_value = record.get("company_name")
    company = company_value.strip() if isinstance(company_value, str) and company_value.strip() else "Company not listed by source"
    category_value = record.get("category")
    category = category_value.strip() if isinstance(category_value, str) and category_value.strip() else None
    source_id = record.get("id")
    company_logo_url = _safe_https_url(record.get("company_logo"))

    return JobListing(
        source_job_id=str(source_id or ""),
        source="Remotive",
        title=title.strip(),
        company=company,
        location=required_location,
        description=description,
        application_url=application_url,
        source_url=REMOTIVE_SOURCE_URL,
        posted_at=posted_at,
        fetched_at=fetched_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        salary_min=None,
        salary_max=None,
        salary_currency="",
        salary_is_predicted=False,
        contract_time=contract_time,
        contract_type=contract_type,
        category=category,
        skills_mentioned=skills,
        required_skills=(),
        preferred_skills=(),
        unclassified_skills=skills,
        salary_display=salary_display,
        company_logo_url=company_logo_url,
        work_mode="Remote",
    )


def fetch_remotive_jobs(limit: int = REMOTIVE_RESULT_LIMIT) -> RemoteJobCatalog:
    """Fetch the public active-remote-jobs list without credentials."""
    if not 1 <= limit <= MAX_LISTINGS:
        raise ValueError(f"Remotive result limit must be between 1 and {MAX_LISTINGS}.")
    request = Request(
        f"{REMOTIVE_API_URL}?limit={limit}",
        headers={"Accept": "application/json", "User-Agent": "CareerPilotAI/0.1"},
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            payload_bytes = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as error:
        if error.code == 429:
            raise RemoteJobSearchError("Remotive rate limit reached. Try again after the listing cache refreshes.") from error
        raise RemoteJobSearchError(f"Remotive could not complete the search (HTTP {error.code}). Try again later.") from error
    except (URLError, TimeoutError, socket.timeout) as error:
        raise RemoteJobSearchError("Could not connect to Remotive. Check your connection and try again.") from error

    if len(payload_bytes) > MAX_RESPONSE_BYTES:
        raise RemoteJobSearchError("Remotive returned an unexpectedly large listing response.")
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RemoteJobSearchError("Remotive returned an unreadable response. Try again later.") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        raise RemoteJobSearchError("Remotive returned an unexpected listing response.")

    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    jobs = deduplicate_jobs(
        job
        for record in payload["jobs"][:MAX_LISTINGS]
        if (job := normalize_remotive_job(record, fetched_at)) is not None
    )
    return RemoteJobCatalog(jobs=jobs, fetched_at=fetched_at)


def filter_remotive_jobs(
    jobs: tuple[JobListing, ...],
    *,
    query: str = "",
    location: str = "",
    company: str = "",
    employment_type: str = "",
    posted_within_days: int | None = None,
    salary_filter: str = "any",
) -> tuple[JobListing, ...]:
    """Filter a cached catalog locally; never sends resume text to the provider."""
    query_words = query.casefold().split()
    normalized_location = location.casefold().strip()
    normalized_company = company.casefold().strip()
    if salary_filter not in {"any", "listed", "not_listed"}:
        raise ValueError("Choose a supported salary visibility filter.")
    if posted_within_days is not None and not 1 <= posted_within_days <= 365:
        raise ValueError("Posting date limit must be between 1 and 365 days.")

    today = datetime.now(timezone.utc)
    results = []
    for job in jobs:
        searchable_text = " ".join((job.title, job.company, job.description, job.category or "", *job.skills_mentioned)).casefold()
        if query_words and not all(word in searchable_text for word in query_words):
            continue
        if normalized_company and normalized_company not in job.company.casefold():
            continue
        if normalized_location:
            allowed_location = job.location.casefold()
            location_terms = {normalized_location}
            if normalized_location in INDIA_LOCATIONS:
                location_terms.add("india")
            is_worldwide = any(term in allowed_location for term in ("worldwide", "anywhere", "global"))
            if not is_worldwide and not any(term in allowed_location for term in location_terms):
                continue
        if employment_type and employment_type != (job.contract_time or job.contract_type or ""):
            continue
        salary_is_listed = bool(job.salary_display)
        if salary_filter == "listed" and not salary_is_listed:
            continue
        if salary_filter == "not_listed" and salary_is_listed:
            continue
        if posted_within_days is not None:
            if not job.posted_at:
                continue
            try:
                posted_at = datetime.fromisoformat(job.posted_at.replace("Z", "+00:00"))
                if posted_at.tzinfo is None:
                    posted_at = posted_at.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if posted_at < today - timedelta(days=posted_within_days):
                continue
        results.append(job)
    return tuple(results)