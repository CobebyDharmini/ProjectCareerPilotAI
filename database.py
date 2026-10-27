"""Local SQLite storage for application tracker records."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(os.environ.get("CAREERPILOT_DB_PATH", Path(__file__).parent / "data" / "careerpilot.db"))
STATUSES = ("Interested", "Preparing", "Applied", "Online Assessment", "Interview Scheduled", "Interview Completed", "Offer Received", "Rejected", "Withdrawn", "Closed")
FIELDS = ("company", "role", "job_type", "location", "work_arrangement", "application_url", "date_applied", "deadline", "status", "follow_up_date", "interview_date", "contact_person", "contact_details", "notes")


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database() -> None:
    with connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL, role TEXT NOT NULL, job_type TEXT NOT NULL,
            location TEXT, work_arrangement TEXT, application_url TEXT,
            date_applied TEXT, deadline TEXT, status TEXT NOT NULL,
            follow_up_date TEXT, interview_date TEXT, contact_person TEXT,
            contact_details TEXT, notes TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_applications_deadline ON applications(deadline)")
        conn.execute("""CREATE TABLE IF NOT EXISTS learning_progress (
            skill TEXT PRIMARY KEY, priority TEXT NOT NULL DEFAULT 'Medium',
            status TEXT NOT NULL DEFAULT 'Not started', estimate TEXT NOT NULL DEFAULT '2-4 weeks',
            recommendation TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS interview_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT, role TEXT NOT NULL,
            interview_type TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")


def list_applications(search: str = "", status: str = "All") -> list[dict[str, Any]]:
    initialize_database()
    query = "SELECT * FROM applications WHERE 1=1"
    params: list[Any] = []
    if search.strip():
        query += " AND (company LIKE ? OR role LIKE ? OR location LIKE ?)"
        like = f"%{search.strip()}%"
        params.extend([like, like, like])
    if status != "All":
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY CASE WHEN deadline IS NULL OR deadline = '' THEN 1 ELSE 0 END, deadline, updated_at DESC"
    with connect() as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def save_application(values: dict[str, Any], record_id: int | None = None) -> None:
    missing = [name for name in ("company", "role", "job_type", "status") if not str(values.get(name, "")).strip()]
    if missing:
        raise ValueError("Company, role, job type, and status are required.")
    if values["status"] not in STATUSES:
        raise ValueError("Choose a supported application status.")
    payload = {field: str(values.get(field) or "").strip() for field in FIELDS}
    initialize_database()
    with connect() as conn:
        if record_id is None:
            columns = ", ".join(FIELDS)
            marks = ", ".join("?" for _ in FIELDS)
            conn.execute(f"INSERT INTO applications ({columns}) VALUES ({marks})", [payload[f] for f in FIELDS])
        else:
            assignments = ", ".join(f"{field} = ?" for field in FIELDS)
            conn.execute(f"UPDATE applications SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", [payload[f] for f in FIELDS] + [record_id])


def delete_application(record_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM applications WHERE id = ?", (record_id,))


def reset_database() -> None:
    with connect() as conn:
        conn.execute("DELETE FROM applications")
        conn.execute("DELETE FROM learning_progress")
        conn.execute("DELETE FROM interview_notes")
        conn.execute("DELETE FROM sqlite_sequence WHERE name = 'applications'")


def get_learning_progress() -> dict[str, dict[str, str]]:
    initialize_database()
    with connect() as conn:
        return {row["skill"]: dict(row) for row in conn.execute("SELECT * FROM learning_progress")}


def save_learning_progress(skill: str, priority: str, status: str, estimate: str, recommendation: str) -> None:
    initialize_database()
    with connect() as conn:
        conn.execute("""INSERT INTO learning_progress(skill, priority, status, estimate, recommendation)
            VALUES (?, ?, ?, ?, ?) ON CONFLICT(skill) DO UPDATE SET priority=excluded.priority,
            status=excluded.status, estimate=excluded.estimate, recommendation=excluded.recommendation,
            updated_at=CURRENT_TIMESTAMP""", (skill, priority, status, estimate, recommendation))


def save_interview_notes(company: str, role: str, interview_type: str, notes: str) -> None:
    initialize_database()
    with connect() as conn:
        conn.execute("INSERT INTO interview_notes(company, role, interview_type, notes) VALUES (?, ?, ?, ?)", (company, role, interview_type, notes))


def list_interview_notes() -> list[dict[str, Any]]:
    initialize_database()
    with connect() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM interview_notes ORDER BY created_at DESC")]
