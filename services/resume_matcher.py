from collections import Counter
from dataclasses import dataclass
import math
import re

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except (ImportError, OSError):
    TfidfVectorizer = None
    cosine_similarity = None

from services.skill_extractor import extract_skills
from services.text_cleaner import normalize_text


MAX_INPUT_CHARS = 100_000
MIN_COMPARISON_TERMS = 3


@dataclass(frozen=True)
class ResumeAnalysis:
    text_similarity: float | None
    similarity_note: str
    resume_skills: tuple[str, ...]
    required_skills: tuple[str, ...]
    matched_skills: tuple[str, ...]
    missing_skills: tuple[str, ...]
    additional_skills: tuple[str, ...]


def _validate_text(text: str, field_name: str) -> None:
    if not text.strip():
        raise ValueError(f"{field_name} cannot be empty.")
    if len(text) > MAX_INPUT_CHARS:
        raise ValueError(f"{field_name} must be {MAX_INPUT_CHARS:,} characters or fewer.")


def _tokenize(text: str) -> list[str]:
    return re.findall(r"(?u)\b\w\w+\b", text)


def _fallback_similarity(resume_text: str, job_description: str) -> float:
    documents = [_tokenize(resume_text), _tokenize(job_description)]
    document_frequency = Counter(
        term for document in documents for term in set(document)
    )
    inverse_document_frequency = {
        term: math.log((1 + len(documents)) / (1 + frequency)) + 1
        for term, frequency in document_frequency.items()
    }
    vectors = []
    for document in documents:
        term_counts = Counter(document)
        vector = {
            term: count * inverse_document_frequency[term]
            for term, count in term_counts.items()
        }
        magnitude = math.sqrt(sum(weight * weight for weight in vector.values()))
        vectors.append({term: weight / magnitude for term, weight in vector.items()})

    return sum(
        weight * vectors[1].get(term, 0.0)
        for term, weight in vectors[0].items()
    )


def _calculate_similarity(resume_text: str, job_description: str) -> tuple[float | None, str]:
    resume = normalize_text(resume_text)
    job = normalize_text(job_description)
    if TfidfVectorizer is None or cosine_similarity is None:
        resume_terms = _tokenize(resume)
        job_terms = _tokenize(job)
    else:
        analyzer = TfidfVectorizer().build_analyzer()
        resume_terms = analyzer(resume)
        job_terms = analyzer(job)

    if min(len(resume_terms), len(job_terms)) < MIN_COMPARISON_TERMS:
        return None, "Not enough text to calculate a meaningful similarity score. Add more detail to both inputs."

    if TfidfVectorizer is None or cosine_similarity is None:
        score = _fallback_similarity(resume, job)
        note = (
            "Scikit-learn could not load in this environment, so a local TF-IDF fallback was used. "
            "This compares wording and topic overlap; it is not a hiring probability or a measure of qualification."
        )
    else:
        vectorizer = TfidfVectorizer()
        try:
            vectors = vectorizer.fit_transform([resume, job])
        except ValueError:
            return None, "Text similarity could not be calculated for these inputs. Add more descriptive wording and try again."
        score = float(cosine_similarity(vectors[0:1], vectors[1:2])[0, 0])
        note = "This compares wording and topic overlap. It is not a hiring probability or a measure of qualification."

    return score, note


def calculate_text_similarity(first_text: str, second_text: str) -> float | None:
    """Return local TF-IDF cosine similarity when both texts are long enough."""
    return _calculate_similarity(first_text, second_text)[0]


def analyze_resume(resume_text: str, job_description: str) -> ResumeAnalysis:
    """Compare resume and job-description text without modifying or transmitting it."""
    _validate_text(resume_text, "Resume text")
    _validate_text(job_description, "Job description")

    resume_skills = extract_skills(resume_text)
    required_skills = extract_skills(job_description)
    resume_skill_set = set(resume_skills)
    required_skill_set = set(required_skills)

    text_similarity, similarity_note = _calculate_similarity(resume_text, job_description)
    return ResumeAnalysis(
        text_similarity=text_similarity,
        similarity_note=similarity_note,
        resume_skills=tuple(resume_skills),
        required_skills=tuple(required_skills),
        matched_skills=tuple(skill for skill in required_skills if skill in resume_skill_set),
        missing_skills=tuple(skill for skill in required_skills if skill not in resume_skill_set),
        additional_skills=tuple(skill for skill in resume_skills if skill not in required_skill_set),
    )