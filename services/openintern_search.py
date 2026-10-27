"""Client for OpenIntern's public technology internship API."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
import json
import re
import socket

OPENINTERN_API_URL = "https://openintern.dev/api/v1/jobs"
OPENINTERN_SOURCE_URL = "https://openintern.dev/jobs"
REQUEST_TIMEOUT_SECONDS = 12
MAX_RESPONSE_BYTES = 2_000_000


class OpenInternSearchError(Exception):
    """User-safe public feed error."""


@dataclass(frozen=True)
class OpenInternPosting:
    id: str
    title: str
    company: str
    location: str
    posted_at: str
    application_url: str
    excerpt: str
    roles: tuple[str, ...]
    regions: tuple[str, ...]
    is_remote: bool


@dataclass(frozen=True)
class OpenInternCatalog:
    jobs: tuple[OpenInternPosting, ...]
    total_count: int
    fetched_at: str


def _safe_link(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value.strip())
        if parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password:
            return value.strip()
    except ValueError:
        pass
    return None


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item.strip()[:80] for item in value if isinstance(item, str) and item.strip())[:20]


def _normalize_family(family: object) -> tuple[OpenInternPosting, ...]:
    if not isinstance(family, dict):
        return ()
    title = family.get("title")
    company = family.get("company")
    postings = family.get("postings")
    if not isinstance(title, str) or not title.strip() or not isinstance(postings, list):
        return ()
    clean_title = re.sub(r"\s+", " ", title).strip()[:200]
    clean_company = re.sub(r"\s+", " ", company).strip()[:160] if isinstance(company, str) else "Company not listed"
    roles = _strings(family.get("roles"))
    regions = _strings(family.get("regions"))
    excerpt = family.get("excerpt")
    clean_excerpt = re.sub(r"\s+", " ", excerpt).strip()[:600] if isinstance(excerpt, str) else ""
    result = []
    for posting in postings:
        if not isinstance(posting, dict):
            continue
        apply_url = _safe_link(posting.get("apply_url"))
        if not apply_url:
            continue
        location = posting.get("location")
        result.append(OpenInternPosting(
            id=str(posting.get("id", ""))[:120],
            title=clean_title,
            company=clean_company,
            location=re.sub(r"\s+", " ", location).strip()[:160] if isinstance(location, str) else "Location not listed",
            posted_at=posting.get("posted_at", "") if isinstance(posting.get("posted_at"), str) else "",
            application_url=apply_url,
            excerpt=clean_excerpt,
            roles=roles,
            regions=regions,
            is_remote=bool(family.get("is_remote")),
        ))
    return tuple(result)


def fetch_openintern_jobs(query: str = "", limit: int = 30) -> OpenInternCatalog:
    """Fetch and normalize a page of publicly available tech internships."""
    query = re.sub(r"[\x00-\x1f\x7f]", " ", query).strip()
    query = re.sub(r"\s+", " ", query)[:100]
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("Results per page must be between 1 and 100.")
    params = {"limit": limit}
    if query:
        params["q"] = query
    request = Request(
        f"{OPENINTERN_API_URL}?{urlencode(params)}",
        headers={"Accept": "application/json", "User-Agent": "CareerPilotAI/0.1 (public internship search)"},
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read(MAX_RESPONSE_BYTES + 1).decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 429:
            raise OpenInternSearchError("OpenIntern is rate limiting requests. Wait a little and try again.") from None
        raise OpenInternSearchError("OpenIntern could not return internship listings right now.") from None
    except (URLError, TimeoutError, socket.timeout):
        raise OpenInternSearchError("Could not connect to OpenIntern. Check your connection and retry.") from None
    except (UnicodeDecodeError, json.JSONDecodeError, OSError):
        raise OpenInternSearchError("OpenIntern returned data that could not be read.") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        raise OpenInternSearchError("OpenIntern returned an unexpected listing format.")
    raw_jobs = payload["jobs"]
    jobs = tuple(posting for family in raw_jobs for posting in _normalize_family(family))
    total = payload.get("total", len(jobs))
    total_count = total if isinstance(total, int) and not isinstance(total, bool) else len(jobs)
    return OpenInternCatalog(jobs, total_count, datetime.now(timezone.utc).isoformat())
