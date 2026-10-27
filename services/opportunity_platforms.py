"""Safe outbound searches for established external opportunity platforms."""
from urllib.parse import urlencode
import re

GOOGLE_SEARCH_URL = "https://www.google.com/search"

PLATFORM_PATHS = {
    "LinkedIn Jobs": "linkedin.com/jobs/view",
    "Unstop Internships": "unstop.com/internship",
    "Unstop Jobs": "unstop.com/job",
    "Unstop Competitions": "unstop.com/competitions",
    "Internshala Internships": "internshala.com/internship",
    "Internshala Jobs": "internshala.com/jobs",
    "National Career Service": "ncs.gov.in/job-seeker",
}


def build_platform_search_url(platform: str, role: str = "", location: str = "India") -> str:
    """Return a Google domain-restricted search; never include resume text."""
    if platform not in PLATFORM_PATHS:
        raise ValueError("Choose a supported opportunity platform.")
    clean = lambda value: re.sub(r"\s+", " ", re.sub(r"[\x00-\x1f\x7f]", " ", value)).strip()[:100]
    terms = [f"site:{PLATFORM_PATHS[platform]}"]
    if role_clean := clean(role):
        terms.append(role_clean)
    if location_clean := clean(location):
        terms.append(location_clean)
    if "Internship" in platform:
        terms.append("internship")
    elif "Competition" in platform:
        terms.append("hackathon OR competition")
    return f"{GOOGLE_SEARCH_URL}?{urlencode({'q': ' '.join(terms)})}"
