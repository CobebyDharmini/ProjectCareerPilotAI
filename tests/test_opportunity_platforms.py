from urllib.parse import parse_qs, urlsplit

import pytest

from services.opportunity_platforms import build_platform_search_url


@pytest.mark.parametrize("platform,domain", [
    ("LinkedIn Jobs", "linkedin.com/jobs/view"),
    ("Unstop Internships", "unstop.com/internship"),
    ("Unstop Jobs", "unstop.com/job"),
    ("Unstop Competitions", "unstop.com/competitions"),
    ("Internshala Internships", "internshala.com/internship"),
    ("National Career Service", "ncs.gov.in/job-seeker"),
])
def test_platform_query_is_domain_restricted_and_uses_selected_terms(platform, domain):
    parsed = urlsplit(build_platform_search_url(platform, "Python Developer", "Pune"))
    assert parsed.scheme == "https"
    assert parsed.hostname == "www.google.com"
    query = parse_qs(parsed.query)["q"][0]
    assert f"site:{domain}" in query
    assert "Python Developer" in query
    assert "Pune" in query
    assert "resume" not in query.casefold()


def test_platform_query_rejects_unknown_platform():
    with pytest.raises(ValueError):
        build_platform_search_url("Unknown")
