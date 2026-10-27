import pytest

from services.resume_matcher import MAX_INPUT_CHARS, analyze_resume
from services.skill_extractor import extract_skills
from services.text_cleaner import normalize_text


def test_normalize_text_handles_case_and_whitespace() -> None:
    assert normalize_text("  PYTHON\tDeveloper  ") == "python developer"


def test_skill_extraction_normalizes_javascript_alias() -> None:
    assert extract_skills("Built tools with JS") == ["JavaScript"]


def test_java_and_javascript_are_distinct_and_partial_words_do_not_match() -> None:
    skills = extract_skills("Java, JavaScript, JavaScripted, NoSQL, and MySQL")
    assert skills == ["Java", "JavaScript"]


def test_skill_extraction_handles_punctuation_aliases() -> None:
    assert extract_skills("C++, C sharp, and node.js") == ["C#", "C++", "Node.js"]


@pytest.mark.parametrize(
    ("resume_text", "job_description", "field_name"),
    [
        ("", "A role with enough detail to compare", "Resume text"),
        ("A resume with enough detail to compare", "  ", "Job description"),
    ],
)
def test_empty_inputs_are_rejected(
    resume_text: str,
    job_description: str,
    field_name: str,
) -> None:
    with pytest.raises(ValueError, match=field_name):
        analyze_resume(resume_text, job_description)


def test_oversized_input_is_rejected() -> None:
    with pytest.raises(ValueError, match="100,000"):
        analyze_resume("x" * (MAX_INPUT_CHARS + 1), "job details")


def test_repeated_words_and_identical_text_have_full_similarity() -> None:
    text = "Python Python data analysis and machine learning projects"
    result = analyze_resume(text, text)
    assert result.text_similarity == pytest.approx(1.0)


def test_short_input_uses_explicit_similarity_fallback() -> None:
    result = analyze_resume("Python", "Python")
    assert result.text_similarity is None
    assert "Not enough text" in result.similarity_note


def test_unrelated_text_has_zero_similarity() -> None:
    result = analyze_resume(
        "Python pandas database coding projects",
        "Garden soil watering flowers seasonal care",
    )
    assert result.text_similarity == pytest.approx(0.0)


def test_analysis_separates_matched_missing_and_additional_skills() -> None:
    result = analyze_resume(
        "Python and Git experience building small applications",
        "Python, SQL, and Java experience for software development",
    )
    assert result.matched_skills == ("Python",)
    assert result.missing_skills == ("Java", "SQL")
    assert result.additional_skills == ("Git",)