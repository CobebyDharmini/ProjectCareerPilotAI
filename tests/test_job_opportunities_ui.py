from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from streamlit.testing.v1 import AppTest
from services.remotive_search import RemoteJobCatalog, RemoteJobSearchError, normalize_remotive_job
import ui.job_opportunities as opportunities_page


def mock_remotive_catalog(monkeypatch: pytest.MonkeyPatch, catalog: RemoteJobCatalog) -> None:
    def get_catalog(limit: int = 100) -> RemoteJobCatalog:
        assert limit == 100
        return catalog

    monkeypatch.setattr(opportunities_page, "_cached_remotive_catalog", get_catalog)


def test_opportunities_page_shows_empty_remote_catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_remotive_catalog(
        monkeypatch,
        RemoteJobCatalog((), "2026-10-27T00:00:00+00:00"),
    )
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(app_path).run(timeout=20)
    app.radio[0].set_value("Job Opportunities").run(timeout=20)

    assert not app.exception
    assert any(item.label == "Role or keywords" for item in app.text_input)
    assert any(item.label == "India location" for item in app.text_input)
    assert any(item.label == "Salary" for item in app.selectbox)
    assert any("No remote jobs match" in item.value for item in app.info)
    assert any(item.label == "Search Google" for item in app.button)


def test_remote_provider_failure_keeps_google_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable(limit: int = 100) -> RemoteJobCatalog:
        assert limit == 100
        raise RemoteJobSearchError("Remotive service unavailable for this test.")

    monkeypatch.setattr(opportunities_page, "_cached_remotive_catalog", unavailable)
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(app_path).run(timeout=20)
    app.radio[0].set_value("Job Opportunities").run(timeout=20)

    assert not app.exception
    assert any("Remotive service unavailable" in item.value for item in app.error)
    assert any(item.label == "Search Google" for item in app.button)


def test_missing_internships_explains_feed_gap_and_offers_google(monkeypatch: pytest.MonkeyPatch) -> None:
    non_internship = normalize_remotive_job(
        {
            "id": 88,
            "title": "Python Developer",
            "description": "Build Python software services.",
            "url": "https://remotive.com/remote-jobs/software/python-developer-88",
            "publication_date": "2026-10-25T10:00:00",
            "company_name": "Test Fixture Company",
            "candidate_required_location": "Worldwide",
            "job_type": "full_time",
        },
        "2026-10-26T10:00:00+00:00",
    )
    assert non_internship is not None
    mock_remotive_catalog(
        monkeypatch,
        RemoteJobCatalog((non_internship,), "2026-10-26T10:00:00+00:00"),
    )
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(app_path).run(timeout=20)
    app.radio[0].set_value("Job Opportunities").run(timeout=20)
    next(selectbox for selectbox in app.selectbox if selectbox.label == "Employment").set_value("Internship")
    next(button for button in app.button if button.label == "Search remote jobs").click().run(timeout=20)

    assert not app.exception
    assert any("current public feed has no internships" in item.value for item in app.info)
    internship_link = next(item.url for item in app.get("link_button") if item.label == "Search Google for internships")
    internship_query = parse_qs(urlsplit(internship_link).query)["q"][0]
    assert "internship" in internship_query


def test_google_search_link_updates_from_selected_role_and_location() -> None:
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(app_path).run(timeout=20)
    app.radio[0].set_value("Job Opportunities").run(timeout=20)
    app.text_input[0].set_value("Backend Developer")
    app.text_input[1].set_value("Hyderabad")
    next(button for button in app.button if button.label == "Search Google").click().run(timeout=20)

    google_links = [item.url for item in app.get("link_button") if item.label == "Open Google results"]
    assert len(google_links) == 1
    query = parse_qs(urlsplit(google_links[0]).query)["q"][0]
    assert query == "Backend Developer jobs in Hyderabad India"

    app.text_input[0].set_value("Backend Developer")
    app.text_input[1].set_value("")
    next(button for button in app.button if button.label == "Search Google").click().run(timeout=20)
    updated_link = next(item.url for item in app.get("link_button") if item.label == "Open Google results")
    updated_query = parse_qs(urlsplit(updated_link).query)["q"][0]
    assert updated_query == "Backend Developer jobs in India"


def test_fixture_remote_result_renders_listing_and_apply_link(monkeypatch: pytest.MonkeyPatch) -> None:
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    fixture_job = normalize_remotive_job(
        {
            "id": 71,
            "title": "Python Developer",
            "description": "<p>Python and SQL required for data applications.</p>",
            "url": "https://remotive.com/remote-jobs/software/python-developer-71",
            "publication_date": "2026-10-25T10:00:00",
            "company_name": "Test Fixture Company",
            "candidate_required_location": "Worldwide",
            "job_type": "full_time",
            "salary": "$80k USD",
            "tags": ["Python", "SQL"],
        },
        "2026-10-26T10:00:00+00:00",
    )
    assert fixture_job is not None

    mock_remotive_catalog(
        monkeypatch,
        RemoteJobCatalog((fixture_job,), "2026-10-26T10:00:00+00:00"),
    )

    app = AppTest.from_file(app_path).run(timeout=20)
    app.radio[0].set_value("Job Opportunities").run(timeout=20)

    assert not app.exception
    assert "All matching remote jobs" in [item.value for item in app.subheader]
    assert any(item.value == "Python Developer" for item in app.subheader)
    apply_links = [item.url for item in app.get("link_button") if item.label == "Apply on listing site"]
    assert apply_links == ["https://remotive.com/remote-jobs/software/python-developer-71"]


def test_unmatched_role_shows_broader_eligible_remote_results(monkeypatch: pytest.MonkeyPatch) -> None:
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    fixture_job = normalize_remotive_job(
        {
            "id": 81,
            "title": "Python Developer",
            "description": "Build Python software services.",
            "url": "https://remotive.com/remote-jobs/software/python-developer-81",
            "publication_date": "2026-10-25T10:00:00",
            "company_name": "Test Fixture Company",
            "candidate_required_location": "Worldwide",
            "job_type": "full_time",
            "tags": ["Python"],
        },
        "2026-10-26T10:00:00+00:00",
    )
    assert fixture_job is not None
    mock_remotive_catalog(
        monkeypatch,
        RemoteJobCatalog((fixture_job,), "2026-10-26T10:00:00+00:00"),
    )

    app = AppTest.from_file(app_path).run(timeout=20)
    app.radio[0].set_value("Job Opportunities").run(timeout=20)
    next(text_input for text_input in app.text_input if text_input.label == "Role or keywords").set_value("Full Stack Developer")
    next(button for button in app.button if button.label == "Search remote jobs").click().run(timeout=20)

    assert not app.exception
    assert any("No exact role/keyword matches" in item.value for item in app.info)
    assert any(item.value == "Python Developer" for item in app.subheader)
