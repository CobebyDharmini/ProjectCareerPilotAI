from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_upload_selection_shows_file_picker_instead_of_resume_text() -> None:
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(app_path).run(timeout=20)
    app.radio[0].set_value("Resume Matcher").run(timeout=20)
    app.radio[0].set_value("Upload PDF or TXT").run(timeout=20)

    assert not app.exception
    assert len(app.file_uploader) == 1
    assert [text_area.label for text_area in app.text_area] == ["Job description"]