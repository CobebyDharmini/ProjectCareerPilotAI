from dataclasses import dataclass

from services.job_search import JobListing
from services.resume_matcher import calculate_text_similarity


@dataclass(frozen=True)
class JobMatch:
    score: int | None
    matching_skills: tuple[str, ...]
    missing_required_skills: tuple[str, ...]
    unconfirmed_skills: tuple[str, ...]
    preferred_skills_found: tuple[str, ...]
    description_similarity: float | None
    explanation: str


def score_job_match(
    resume_text: str,
    resume_skills: tuple[str, ...],
    job: JobListing,
) -> JobMatch:
    """Score visible skill and wording overlap; never send resume text to the job provider."""
    resume_skill_set = set(resume_skills)
    matching_skills = tuple(skill for skill in job.skills_mentioned if skill in resume_skill_set)
    missing_required = tuple(skill for skill in job.required_skills if skill not in resume_skill_set)
    unconfirmed = tuple(skill for skill in job.unclassified_skills if skill not in resume_skill_set)
    preferred_found = tuple(skill for skill in job.preferred_skills if skill in resume_skill_set)
    description_similarity = calculate_text_similarity(
        resume_text,
        f"{job.title}. {job.description}",
    )

    weighted_components: list[tuple[float, float]] = []
    if job.required_skills:
        matched_required_count = len(job.required_skills) - len(missing_required)
        weighted_components.append((0.60, matched_required_count / len(job.required_skills)))
    if job.preferred_skills:
        weighted_components.append((0.10, len(preferred_found) / len(job.preferred_skills)))
    if job.unclassified_skills:
        confirmed_count = len(job.unclassified_skills) - len(unconfirmed)
        weighted_components.append((0.10, confirmed_count / len(job.unclassified_skills)))
    if description_similarity is not None:
        weighted_components.append((0.20, description_similarity))

    if weighted_components:
        available_weight = sum(weight for weight, _ in weighted_components)
        score = round(
            sum(weight * value for weight, value in weighted_components)
            / available_weight
            * 100
        )
    else:
        score = None

    if missing_required:
        explanation = (
            f"{len(job.required_skills) - len(missing_required)} of {len(job.required_skills)} "
            "detected required skills appear in the resume; some required skills were not confirmed."
        )
    elif job.required_skills:
        explanation = "All skills explicitly marked required in the available listing text were detected in the resume."
    elif matching_skills:
        explanation = (
            f"{len(matching_skills)} listed skill(s) appear in the resume. The source did not clearly classify "
            "skills as required or preferred."
        )
    else:
        explanation = "No recognized skills overlapped; review the job text because the source may provide only a snippet."

    return JobMatch(
        score=score,
        matching_skills=matching_skills,
        missing_required_skills=missing_required,
        unconfirmed_skills=unconfirmed,
        preferred_skills_found=preferred_found,
        description_similarity=description_similarity,
        explanation=explanation,
    )