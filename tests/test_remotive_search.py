import json
from urllib.error import HTTPError

import pytest

from services import remotive_search
from services.remotive_search import (
    RemoteJobSearchError,
    fetch_remotive_jobs,
    filter_remotive_jobs,
    html_to_text,
    normalize_remotive_job,
)


def remotive_record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "id": 71,
        "title": "Python Developer",
        "company_name": "Example Remote Co",
        "url": "https://remotive.com/remote-jobs/software/python-developer-71",
        "category": "Software Development",
        "job_type": "full_time",
        "publication_date": "2026-10-27T10:00:00",
        "candidate_required_location": "Worldwide",
        "salary": "$80k USD",
        "description": "<h2>Required</h2><p>Python and SQL services.</p>",
        "tags": ["Python", "API"],
        "company_logo": "https://remotive.com/job/71/logo",
    }
    record.update(overrides)
    return record


class FakeResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> bool:
        return exc_type is None and exc_value is None and traceback is None

    def read(self, limit: int) -> bytes:
        return self.content[:limit]


def test_remotive_normalization_keeps_source_fields_and_cleans_html() -> None:
    job = normalize_remotive_job(remotive_record(), "2026-10-27T11:00:00+00:00")

    assert job is not None
    assert job.source == "Remotive"
    assert job.title == "Python Developer"
    assert job.company == "Example Remote Co"
    assert job.work_mode == "Remote"
    assert job.location == "Worldwide"
    assert job.salary_display == "$80k USD"
    assert job.description == "Required\nPython and SQL services."
    assert job.skills_mentioned == ("Python", "SQL")
    assert job.application_url == "https://remotive.com/remote-jobs/software/python-developer-71"


@pytest.mark.parametrize("bad_url", ["http://remotive.com/job", "javascript:alert(1)", "https://user:pass@remotive.com/job"])
def test_remotive_normalization_rejects_unsafe_urls(bad_url: str) -> None:
    assert normalize_remotive_job(remotive_record(url=bad_url)) is None


def test_remotive_internship_type_is_preserved() -> None:
    job = normalize_remotive_job(remotive_record(job_type="internship"))

    assert job is not None
    assert job.contract_type == "internship"


def test_filter_remotive_jobs_for_india_includes_worldwide_but_not_europe_only() -> None:
    worldwide = normalize_remotive_job(remotive_record())
    india = normalize_remotive_job(remotive_record(id=72, candidate_required_location="India"))
    europe = normalize_remotive_job(remotive_record(id=73, candidate_required_location="Europe only"))
    assert worldwide is not None and india is not None and europe is not None

    results = filter_remotive_jobs(
        (worldwide, india, europe),
        query="Python Developer",
        location="Hyderabad",
        company="example",
        employment_type="full_time",
        salary_filter="listed",
    )

    assert {job.source_job_id for job in results} == {"71", "72"}


def test_filter_remotive_jobs_salary_disclosure() -> None:
    with_salary = normalize_remotive_job(remotive_record())
    without_salary = normalize_remotive_job(remotive_record(id=74, salary=""))
    assert with_salary is not None and without_salary is not None

    assert filter_remotive_jobs((with_salary, without_salary), salary_filter="listed") == (with_salary,)
    assert filter_remotive_jobs((with_salary, without_salary), salary_filter="not_listed") == (without_salary,)


def test_fetch_remotive_jobs_parses_public_api_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    request_data: dict[str, object] = {}

    def fake_urlopen(request: object, timeout: int) -> FakeResponse:
        request_data["url"] = request.full_url
        request_data["timeout"] = timeout
        return FakeResponse(json.dumps({"jobs": [remotive_record()]}).encode("utf-8"))

    monkeypatch.setattr(remotive_search, "urlopen", fake_urlopen)
    catalog = fetch_remotive_jobs()

    assert request_data["url"] == f"{remotive_search.REMOTIVE_API_URL}?limit={remotive_search.REMOTIVE_RESULT_LIMIT}"
    assert request_data["timeout"] == remotive_search.REQUEST_TIMEOUT_SECONDS
    assert len(catalog.jobs) == 1
    assert catalog.jobs[0].source == "Remotive"


def test_fetch_remotive_jobs_handles_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    def rate_limited(request: object, timeout: int) -> None:
        assert timeout == remotive_search.REQUEST_TIMEOUT_SECONDS
        assert getattr(request, "full_url", "") == f"{remotive_search.REMOTIVE_API_URL}?limit={remotive_search.REMOTIVE_RESULT_LIMIT}"
        raise HTTPError(remotive_search.REMOTIVE_API_URL, 429, "Too many requests", {}, None)

    monkeypatch.setattr(remotive_search, "urlopen", rate_limited)
    with pytest.raises(RemoteJobSearchError, match="rate limit"):
        fetch_remotive_jobs()


def test_html_to_text_does_not_return_markup() -> None:
    assert html_to_text("<p>First</p><p><strong>Second</strong></p>") == "First\nSecond"