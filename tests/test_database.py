import pytest

from database import (STATUSES, delete_application, get_learning_progress, list_applications,
                      list_interview_notes, reset_database, save_application,
                      save_interview_notes, save_learning_progress)


def test_application_crud_and_filters(monkeypatch, tmp_path):
    import database
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.sqlite")
    data = {"company": "Example, Inc.", "role": "Developer", "job_type": "Internship", "status": "Applied", "notes": "Asked for a follow-up"}
    save_application(data)
    results = list_applications("Example", "Applied")
    assert len(results) == 1
    record_id = results[0]["id"]
    data["status"] = "Interview Scheduled"
    save_application(data, record_id)
    assert list_applications(status="Applied") == []
    assert list_applications(status="Interview Scheduled")[0]["company"] == "Example, Inc."
    delete_application(record_id)
    assert list_applications() == []


def test_validation_and_reset(monkeypatch, tmp_path):
    import database
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.sqlite")
    try:
        save_application({"company": "", "role": "Dev", "job_type": "Internship", "status": STATUSES[0]})
    except ValueError as exc:
        assert "required" in str(exc)
    else:
        raise AssertionError("Expected required-field validation")
    save_application({"company": "Example", "role": "Dev", "job_type": "Internship", "status": "Interested"})
    save_learning_progress("SQL", "High", "In progress", "2 weeks", "Practice joins")
    save_interview_notes("Example", "Dev", "Technical", "Review query tradeoffs")
    assert get_learning_progress()["SQL"]["status"] == "In progress"
    assert list_interview_notes()[0]["notes"] == "Review query tradeoffs"
    reset_database()
    assert list_applications() == []
    assert get_learning_progress() == {}
    assert list_interview_notes() == []


def test_public_demo_mode_blocks_database_writes(monkeypatch, tmp_path):
    import database
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "demo.sqlite")
    monkeypatch.setenv("CAREERPILOT_DEMO_MODE", "true")
    with pytest.raises(RuntimeError, match="public demo"):
        save_application({"company": "Example", "role": "Dev", "job_type": "Internship", "status": "Applied"})
    with pytest.raises(RuntimeError, match="public demo"):
        save_learning_progress("Python", "High", "In progress", "2 weeks", "Practice")
    with pytest.raises(RuntimeError, match="public demo"):
        save_interview_notes("Example", "Dev", "Technical", "Notes")
    with pytest.raises(RuntimeError, match="public demo"):
        delete_application(1)
    with pytest.raises(RuntimeError, match="public demo"):
        reset_database()
