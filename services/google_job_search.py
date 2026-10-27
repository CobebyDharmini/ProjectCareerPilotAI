from urllib.parse import urlencode
import re


GOOGLE_SEARCH_URL = "https://www.google.com/search"
MAX_SEARCH_TERM_LENGTH = 100


def build_google_job_search_url(
    role: str,
    location: str,
    skills: tuple[str, ...] = (),
    employment_keyword: str = "",
) -> str:
    """Build a Google jobs query from selected profile terms, never from full resume text."""
    safe_role = _clean_term(role, "Software Engineer")
    safe_location = _clean_term(location, "")
    if safe_location and "india" not in safe_location.casefold():
        safe_location = f"{safe_location} India"
    safe_location = safe_location or "India"
    safe_skills = [_clean_term(skill, "") for skill in skills[:5]]
    safe_employment_keyword = _clean_term(employment_keyword, "")
    query_terms = [safe_role, "jobs"]
    if safe_employment_keyword:
        query_terms.append(safe_employment_keyword)
    query_terms.extend(("in", safe_location, *[skill for skill in safe_skills if skill]))
    return f"{GOOGLE_SEARCH_URL}?{urlencode({'q': ' '.join(query_terms)})}"


def _clean_term(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[\x00-\x1f\x7f]", " ", value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = cleaned[:MAX_SEARCH_TERM_LENGTH]
    return cleaned or fallback