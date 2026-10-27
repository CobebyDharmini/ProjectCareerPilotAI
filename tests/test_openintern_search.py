import json
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import pytest

from services import openintern_search
from services.openintern_search import OpenInternSearchError, fetch_openintern_jobs


def payload():
    return {"total": 1, "jobs": [{
        "title": "Software Engineer Intern", "company": "Example Labs",
        "excerpt": "Build developer tools.", "roles": ["software"], "regions": ["us"],
        "is_remote": False,
        "postings": [{"id": "p-1", "location": "New York", "posted_at": "2026-10-20", "apply_url": "https://careers.example/apply"}],
    }]}


class FakeResponse:
    def __init__(self, body): self.body = body
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, limit): return self.body[:limit]


def test_fetch_openintern_normalizes_public_feed_and_encodes_query(monkeypatch):
    request_info = {}
    def fake_urlopen(request, timeout):
        request_info["url"] = request.full_url
        request_info["timeout"] = timeout
        return FakeResponse(json.dumps(payload()).encode())
    monkeypatch.setattr(openintern_search, "urlopen", fake_urlopen)
    result = fetch_openintern_jobs("Python Developer")
    assert parse_qs(urlsplit(request_info["url"]).query) == {"limit": ["30"], "q": ["Python Developer"]}
    assert request_info["timeout"] == openintern_search.REQUEST_TIMEOUT_SECONDS
    assert result.total_count == 1
    assert result.jobs[0].company == "Example Labs"
    assert result.jobs[0].application_url == "https://careers.example/apply"


def test_fetch_openintern_discards_unsafe_application_links(monkeypatch):
    content = payload()
    content["jobs"][0]["postings"][0]["apply_url"] = "javascript:alert(1)"
    monkeypatch.setattr(openintern_search, "urlopen", lambda *args, **kwargs: FakeResponse(json.dumps(content).encode()))
    assert fetch_openintern_jobs().jobs == ()


def test_fetch_openintern_handles_rate_limit(monkeypatch):
    def rate_limited(*args, **kwargs):
        raise HTTPError(openintern_search.OPENINTERN_API_URL, 429, "rate limited", {}, None)
    monkeypatch.setattr(openintern_search, "urlopen", rate_limited)
    with pytest.raises(OpenInternSearchError, match="rate limiting"):
        fetch_openintern_jobs()
