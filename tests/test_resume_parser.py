import pymupdf
import pytest

from services.resume_parser import MAX_UPLOAD_BYTES, extract_resume_text
from services.resume_matcher import analyze_resume


def make_pdf(text: str = "") -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    if text:
        page.insert_text((72, 72), text)
    content = document.tobytes()
    document.close()
    return content


def test_extracts_selectable_text_from_pdf() -> None:
    extracted = extract_resume_text("resume.pdf", make_pdf("Python engineer with SQL experience"))
    assert "Python engineer" in extracted


def test_pdf_extraction_flows_into_resume_analysis() -> None:
    resume_text = extract_resume_text(
        "resume.pdf",
        make_pdf("Python data projects with pandas and Git version control"),
    )
    analysis = analyze_resume(
        resume_text,
        "Python and pandas experience required, along with SQL and Docker for data engineering projects.",
    )
    assert analysis.matched_skills == ("Python", "pandas")
    assert analysis.missing_skills == ("Docker", "SQL")


def test_empty_or_scanned_pdf_explains_text_is_unavailable() -> None:
    with pytest.raises(ValueError, match="No selectable text"):
        extract_resume_text("scan.pdf", make_pdf())


def test_malformed_pdf_returns_recoverable_error() -> None:
    with pytest.raises(ValueError, match="valid, unencrypted PDF"):
        extract_resume_text("broken.pdf", b"not a PDF")


def test_extracts_utf8_text_file() -> None:
    assert extract_resume_text("resume.txt", b"\xef\xbb\xbfPython developer") == "Python developer"


def test_rejects_non_utf8_text_file() -> None:
    with pytest.raises(ValueError, match="UTF-8"):
        extract_resume_text("resume.txt", b"\xff\xfe\x00")


def test_rejects_unsupported_file_type() -> None:
    with pytest.raises(ValueError, match=".txt or .pdf"):
        extract_resume_text("resume.docx", b"content")


def test_rejects_empty_upload() -> None:
    with pytest.raises(ValueError, match="file is empty"):
        extract_resume_text("resume.pdf", b"")


def test_rejects_upload_over_size_limit() -> None:
    with pytest.raises(ValueError, match="5 MB"):
        extract_resume_text("resume.pdf", b"x" * (MAX_UPLOAD_BYTES + 1))


def test_rejects_pdf_with_too_much_extracted_text(monkeypatch: pytest.MonkeyPatch) -> None:
    class Page:
        def get_text(self, format: str) -> str:
            assert format == "text"
            return "x" * 60_000

    class Document:
        def __enter__(self) -> "Document":
            return self

        def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> bool:
            return exc_type is None and exc_value is None and traceback is None

        def __iter__(self) -> iter:
            return iter((Page(), Page()))

    def fake_open(*, stream: bytes, filetype: str) -> Document:
        assert stream == b"test PDF"
        assert filetype == "pdf"
        return Document()

    monkeypatch.setattr("services.resume_parser.pymupdf.open", fake_open)
    with pytest.raises(ValueError, match="100,000 characters"):
        extract_resume_text("resume.pdf", b"test PDF")