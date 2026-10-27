import json
from urllib.error import HTTPError

import pytest

from services import job_search
from services.job_search import JobSearchError, deduplicate_jobs, normalize_job, search_adzuna


def adzuna_record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "id": "source-123",
        "title": "Python Developer",
        "description": "Python and SQL are required. Docker preferred.",
        "redirect_url": "https://jobs.example/apply/123",
        "created": "2026-10-25T10:00:00Z",
        "company": {"display_name": "Example Company"},
        "location": {"display_name": "Hyderabad"},
        "salary_min": 500000,
        "salary_max": 800000,
        "salary_is_predicted": "0",
        "contract_time": "full_time",
        "contract_type": "permanent",
        "category": {"label": "IT Jobs"},
    }
    record.update(overrides)
    return record


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self.content = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> bool:
        return exc_type is None and exc_value is None and traceback is None

    def read(self) -> bytes:
        return self.content


def test_normalize_job_maps_provider_fields_and_skill_classification() -> None:
    job = normalize_job(adzuna_record(), "2026-10-26T12:00:00+00:00")

    assert job is not None
    assert job.source == "Adzuna"
    assert job.source_job_id == "source-123"
    assert job.company == "Example Company"
    assert job.location == "Hyderabad"
    assert job.salary_min == 500000
    assert job.salary_currency == "INR"
    assert job.required_skills == ("Python", "SQL")
    assert job.preferred_skills == ("Docker",)
    assert job.fetched_at == "2026-10-26T12:00:00+00:00"


@pytest.mark.parametrize("unsafe_url", ["javascript:alert(1)", "file:///tmp/job", "https://user:pass@example.com"])
def test_normalize_job_rejects_unsafe_application_url(unsafe_url: str) -> None:
    assert normalize_job(adzuna_record(redirect_url=unsafe_url)) is None


def test_normalize_job_handles_missing_optional_provider_fields() -> None:
    job = normalize_job({"id": "minimal", "title": "Developer", "redirect_url": "https://jobs.example/apply"})

    assert job is not None
    assert job.company == "Company not listed by source"
    assert job.location == "Location not listed by source"
    assert job.salary_min is None
    assert job.posted_at is None


def test_deduplicate_jobs_by_provider_id_and_job_identity() -> None:
    first = normalize_job(adzuna_record())
    second = normalize_job(adzuna_record())
    assert first is not None and second is not None
    assert deduplicate_jobs((first, second)) == (first,)


def test_search_sends_country_location_filters_and_secret_parameters(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def fake_urlopen(request: object, timeout: int) -> FakeResponse:
        captured["url"] = request.full_url
        captured["timeout"] = str(timeout)
        return FakeResponse({"count": 1, "results": [adzuna_record()]})

    monkeypatch.setattr(job_search, "urlopen", fake_urlopen)
    result = search_adzuna(
        app_id="private-id",
        app_key="private-key",
        query="Python developer",
        location="Hyderabad",
        max_days_old=14,
        salary_min=300000,
        salary_max=900000,
        employment_filter="full_time",
        company="Example Company",
    )

    assert "/jobs/in/search/1?" in captured["url"]
    assert "where=Hyderabad" in captured["url"]
    assert "max_days_old=14" in captured["url"]
    assert "salary_min=300000" in captured["url"]
    assert "salary_max=900000" in captured["url"]
    assert "company=Example+Company" in captured["url"]
    assert "full_time=1" in captured["url"]
    assert "private-key" in captured["url"]
    assert captured["timeout"] == str(job_search.API_TIMEOUT_SECONDS)
    assert result.total_count == 1
    assert len(result.jobs) == 1


def test_search_requires_credentials_and_valid_parameters() -> None:
    with pytest.raises(JobSearchError, match="credentials are missing"):
        search_adzuna(app_id="", app_key="", query="developer")
    with pytest.raises(ValueError, match="search phrase"):
        search_adzuna(app_id="id", app_key="key", query=" ")
    with pytest.raises(ValueError, match="Page"):
        search_adzuna(app_id="id", app_key="key", query="developer", page=0)
    with pytest.raises(ValueError, match="cannot exceed"):
        search_adzuna(app_id="id", app_key="key", query="developer", salary_min=500, salary_max=100)


def test_search_reports_provider_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    def rate_limited(request: object, timeout: int) -> None:
        assert timeout == job_search.API_TIMEOUT_SECONDS
        raise HTTPError(str(getattr(request, "full_url", "https://api.example")), 429, "Too many requests", {}, None)

    monkeypatch.setattr(job_search, "urlopen", rate_limited)
    with pytest.raises(JobSearchError, match="rate limit"):
        search_adzuna(app_id="id", app_key="key", query="developer")