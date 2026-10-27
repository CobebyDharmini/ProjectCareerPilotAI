from services.job_matching import score_job_match
from services.job_search import normalize_job


def make_job(description: str) -> object:
    return normalize_job(
        {
            "id": "job-1",
            "title": "Python Data Engineer",
            "description": description,
            "redirect_url": "https://jobs.example/apply",
            "company": {"display_name": "Example Company"},
            "location": {"display_name": "Hyderabad"},
        }
    )


def test_job_match_reports_confirmed_missing_and_unclassified_skills() -> None:
    job = make_job("Python and SQL are required. Docker is preferred. Uses Git and AWS with cloud pipelines.")
    match = score_job_match("Python developer with Git project experience and data projects", ("Python", "Git"), job)

    assert match.score is not None
    assert set(match.matching_skills) == {"Python", "Git"}
    assert match.missing_required_skills == ("SQL",)
    assert match.preferred_skills_found == ()
    assert match.unconfirmed_skills == ("AWS",)
    assert "1 of 2" in match.explanation


def test_unclassified_skills_are_not_claimed_as_required() -> None:
    job = make_job("Work with Python, SQL, and Docker on backend services.")
    match = score_job_match("Python backend service developer", ("Python",), job)

    assert match.missing_required_skills == ()
    assert set(match.unconfirmed_skills) == {"SQL", "Docker"}


def test_candidate_resume_is_compared_only_locally() -> None:
    resume_text = "Python SQL data services and backend engineering projects"
    job = make_job("Python and SQL are required for backend data services.")
    match = score_job_match(resume_text, ("Python", "SQL"), job)

    assert match.description_similarity is not None
    assert match.score is not None
    assert match.score >= 60