from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
import json
import re
import socket

from services.skill_extractor import SKILL_PATTERNS, extract_skills


ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api"
ADZUNA_SOURCE_URL = "https://www.adzuna.in/"
MAX_PAGE_NUMBER = 100
MAX_RESULTS_PER_PAGE = 50
API_TIMEOUT_SECONDS = 12


class JobSearchError(Exception):
    """A user-safe job provider error without request URLs or credential details."""


@dataclass(frozen=True)
class JobListing:
    source_job_id: str
    source: str
    title: str
    company: str
    location: str
    description: str
    application_url: str
    source_url: str
    posted_at: str | None
    fetched_at: str
    salary_min: float | None
    salary_max: float | None
    salary_currency: str
    salary_is_predicted: bool
    contract_time: str | None
    contract_type: str | None
    category: str | None
    skills_mentioned: tuple[str, ...]
    required_skills: tuple[str, ...]
    preferred_skills: tuple[str, ...]
    unclassified_skills: tuple[str, ...]
    salary_display: str | None = None
    company_logo_url: str | None = None
    work_mode: str | None = None


@dataclass(frozen=True)
class JobSearchResult:
    jobs: tuple[JobListing, ...]
    total_count: int
    page: int
    results_per_page: int
    fetched_at: str


def _clean_search_value(value: str, field_name: str, max_length: int, required: bool = False) -> str:
    cleaned = re.sub(r"[\x00-\x1f\x7f]", " ", value).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if required and not cleaned:
        raise ValueError(f"Enter a {field_name} to search.")
    if len(cleaned) > max_length:
        raise ValueError(f"{field_name.capitalize()} must be {max_length} characters or fewer.")
    return cleaned


def _safe_http_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    url = value.strip()
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return None
        if parsed.username or parsed.password:
            return None
    except ValueError:
        return None
    return url


def _read_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _read_category(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    label = value.get("label")
    return label.strip() if isinstance(label, str) and label.strip() else None


def _read_display_name(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    display_name = value.get("display_name")
    return display_name.strip() if isinstance(display_name, str) and display_name.strip() else None


def _classify_job_skills(description: str, skills: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
    required: list[str] = []
    preferred: list[str] = []
    unclassified: list[str] = []
    required_terms = re.compile(r"\b(required|must[- ]have|mandatory|essential)\b", re.IGNORECASE)
    preferred_terms = re.compile(r"\b(preferred|nice[- ]to[- ]have|desirable|bonus)\b", re.IGNORECASE)

    for skill in skills:
        pattern = SKILL_PATTERNS[skill]
        match = pattern.search(description)
        if match is None:
            unclassified.append(skill)
            continue
        sentence_start = max(
            description.rfind(mark, 0, match.start())
            for mark in (".", "!", "?", "\n")
        ) + 1
        sentence_end_candidates = [
            description.find(mark, match.end())
            for mark in (".", "!", "?", "\n")
            if description.find(mark, match.end()) >= 0
        ]
        sentence_end = min(sentence_end_candidates) if sentence_end_candidates else len(description)
        context = description[sentence_start:sentence_end]
        is_required = bool(required_terms.search(context))
        is_preferred = bool(preferred_terms.search(context))
        if is_required and not is_preferred:
            required.append(skill)
        elif is_preferred and not is_required:
            preferred.append(skill)
        else:
            unclassified.append(skill)

    return tuple(required), tuple(preferred), tuple(unclassified)


def normalize_job(record: object, fetched_at: str | None = None) -> JobListing | None:
    """Convert one Adzuna ad into the internal model; discard unsafe or incomplete ads."""
    if not isinstance(record, dict):
        return None
    title = record.get("title")
    if not isinstance(title, str) or not title.strip():
        return None
    application_url = _safe_http_url(record.get("redirect_url"))
    if application_url is None:
        return None

    description_value = record.get("description")
    description = description_value.strip() if isinstance(description_value, str) else ""
    company = _read_display_name(record.get("company")) or "Company not listed by source"
    location = _read_display_name(record.get("location")) or "Location not listed by source"
    skills = tuple(extract_skills(f"{title} {description}"))
    required, preferred, unclassified = _classify_job_skills(description, skills)
    posted_at = record.get("created")
    if not isinstance(posted_at, str) or not posted_at.strip():
        posted_at = None

    salary_flag = str(record.get("salary_is_predicted", "0")) == "1"
    contract_time = record.get("contract_time")
    contract_type = record.get("contract_type")
    return JobListing(
        source_job_id=str(record.get("id", "")),
        source="Adzuna",
        title=title.strip(),
        company=company,
        location=location,
        description=description,
        application_url=application_url,
        source_url=ADZUNA_SOURCE_URL,
        posted_at=posted_at,
        fetched_at=fetched_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        salary_min=_read_number(record.get("salary_min")),
        salary_max=_read_number(record.get("salary_max")),
        salary_currency="INR",
        salary_is_predicted=salary_flag,
        contract_time=contract_time if contract_time in {"full_time", "part_time"} else None,
        contract_type=contract_type if contract_type in {"permanent", "contract"} else None,
        category=_read_category(record.get("category")),
        skills_mentioned=skills,
        required_skills=required,
        preferred_skills=preferred,
        unclassified_skills=unclassified,
    )


def deduplicate_jobs(jobs: Iterable[JobListing]) -> tuple[JobListing, ...]:
    seen: set[tuple[str, ...]] = set()
    unique_jobs = []
    for job in jobs:
        normalized_url = job.application_url.casefold().rstrip("/")
        identity = (
            job.source_job_id.casefold(),
            normalized_url,
            job.company.casefold().strip(),
            job.title.casefold().strip(),
            job.location.casefold().strip(),
        )
        if identity not in seen:
            seen.add(identity)
            unique_jobs.append(job)
    return tuple(unique_jobs)


def search_adzuna(
    *,
    app_id: str,
    app_key: str,
    query: str,
    location: str = "",
    page: int = 1,
    results_per_page: int = 20,
    sort_by: str = "relevance",
    max_days_old: int | None = None,
    salary_min: int | None = None,
    salary_max: int | None = None,
    company: str = "",
    employment_filter: str = "",
) -> JobSearchResult:
    """Fetch a single page of India jobs; secrets are never included in user-facing errors."""
    if not app_id.strip() or not app_key.strip():
        raise JobSearchError("Adzuna credentials are missing. Set ADZUNA_APP_ID and ADZUNA_APP_KEY on the server.")
    query = _clean_search_value(query, "search phrase", 100, required=True)
    location = _clean_search_value(location, "location", 80)
    company = _clean_search_value(company, "company", 80)
    if not 1 <= page <= MAX_PAGE_NUMBER:
        raise ValueError(f"Page must be between 1 and {MAX_PAGE_NUMBER}.")
    if not 1 <= results_per_page <= MAX_RESULTS_PER_PAGE:
        raise ValueError(f"Results per page must be between 1 and {MAX_RESULTS_PER_PAGE}.")
    if sort_by not in {"relevance", "date", "salary", "default"}:
        raise ValueError("Choose a supported job sort order.")
    if max_days_old is not None and not 1 <= max_days_old <= 365:
        raise ValueError("Posting date limit must be between 1 and 365 days.")
    if salary_min is not None and salary_min < 0:
        raise ValueError("Minimum salary cannot be negative.")
    if salary_max is not None and salary_max < 0:
        raise ValueError("Maximum salary cannot be negative.")
    if salary_min is not None and salary_max is not None and salary_min > salary_max:
        raise ValueError("Minimum salary cannot exceed maximum salary.")
    employment_parameters = {
        "full_time": {"full_time": "1"},
        "part_time": {"part_time": "1"},
        "permanent": {"permanent": "1"},
        "contract": {"contract": "1"},
        "": {},
    }
    if employment_filter not in employment_parameters:
        raise ValueError("Choose a supported employment type.")

    parameters = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": str(results_per_page),
        "what": query,
        "sort_by": sort_by,
        "content-type": "application/json",
    }
    if location:
        parameters["where"] = location
    if company:
        parameters["company"] = company
    if max_days_old is not None:
        parameters["max_days_old"] = str(max_days_old)
    if salary_min is not None:
        parameters["salary_min"] = str(salary_min)
        parameters["salary_include_unknown"] = "1"
    if salary_max is not None:
        parameters["salary_max"] = str(salary_max)
    parameters.update(employment_parameters[employment_filter])
    url = f"{ADZUNA_BASE_URL}/jobs/in/search/{page}?{urlencode(parameters)}"
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "CareerPilotAI/0.1"})

    try:
        with urlopen(request, timeout=API_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        if error.code == 429:
            raise JobSearchError("Adzuna rate limit reached. Wait a few minutes and try again.") from error
        if error.code in {401, 403, 410}:
            raise JobSearchError("Adzuna rejected the credentials. Check the server-side app ID and key.") from error
        raise JobSearchError(f"Adzuna could not complete the search (HTTP {error.code}). Try again later.") from error
    except (URLError, TimeoutError, socket.timeout) as error:
        raise JobSearchError("Could not connect to Adzuna. Check your connection and try again.") from error
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise JobSearchError("Adzuna returned an unreadable response. Try the search again later.") from error

    if not isinstance(payload, dict):
        raise JobSearchError("Adzuna returned an unexpected response. Try the search again later.")
    raw_jobs = payload.get("results", [])
    if not isinstance(raw_jobs, list):
        raise JobSearchError("Adzuna returned an unexpected job list. Try the search again later.")

    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    jobs = deduplicate_jobs(
        job
        for record in raw_jobs
        if (job := normalize_job(record, fetched_at)) is not None
    )
    total_count = payload.get("count", len(jobs))
    if not isinstance(total_count, int) or total_count < 0:
        total_count = len(jobs)
    return JobSearchResult(
        jobs=jobs,
        total_count=total_count,
        page=page,
        results_per_page=results_per_page,
        fetched_at=fetched_at,
    )