from urllib.parse import parse_qs, urlsplit

from services.google_job_search import build_google_job_search_url


def test_google_job_query_uses_role_location_and_profile_skills() -> None:
    url = build_google_job_search_url("Python Developer", "Hyderabad", ("Python", "pandas"))
    parsed = urlsplit(url)

    assert parsed.scheme == "https"
    assert parsed.hostname == "www.google.com"
    assert parse_qs(parsed.query)["q"] == ["Python Developer jobs in Hyderabad India Python pandas"]


def test_google_job_query_has_safe_defaults_and_caps_skill_terms() -> None:
    url = build_google_job_search_url("", "", ("Python", "SQL", "Git", "AWS", "Docker", "React"))
    query = parse_qs(urlsplit(url).query)["q"][0]

    assert query == "Software Engineer jobs in India Python SQL Git AWS Docker"
    assert "React" not in query


def test_google_job_query_strips_control_characters() -> None:
    url = build_google_job_search_url("Java\nDeveloper", "Pune\x00", ())
    query = parse_qs(urlsplit(url).query)["q"][0]

    assert query == "Java Developer jobs in Pune India"