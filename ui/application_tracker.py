"""Application tracker interface."""
from __future__ import annotations

from datetime import date
import io
import pandas as pd
import streamlit as st

from database import STATUSES, delete_application, list_applications, save_application


def render_application_tracker() -> None:
    st.title("Application Tracker")
    st.write("Keep application details, deadlines, interviews, and follow-ups in one place.")
    with st.expander("Add an application", expanded=not bool(list_applications())):
        with st.form("application_add", clear_on_submit=True):
            a, b = st.columns(2)
            company = a.text_input("Company *")
            role = b.text_input("Role *")
            job_type = a.selectbox("Job type *", ["Internship", "Full-time", "Part-time", "Contract", "Other"])
            status = b.selectbox("Status", STATUSES)
            location = a.text_input("Location")
            arrangement = b.selectbox("Work arrangement", ["Not specified", "Remote", "Hybrid", "Onsite"])
            url = st.text_input("Application URL")
            c, d, e = st.columns(3)
            applied = c.date_input("Date applied", value=None)
            deadline = d.date_input("Application deadline", value=None)
            follow = e.date_input("Next follow-up", value=None)
            interview = st.date_input("Interview date", value=None)
            contact = st.text_input("Contact person (optional)")
            details = st.text_input("Contact details (optional)")
            notes = st.text_area("Notes")
            submitted = st.form_submit_button("Save application", type="primary")
        if submitted:
            try:
                date_text = lambda d: d.isoformat() if isinstance(d, date) else ""
                save_application(dict(company=company, role=role, job_type=job_type, status=status, location=location, work_arrangement=arrangement, application_url=url, date_applied=date_text(applied), deadline=date_text(deadline), follow_up_date=date_text(follow), interview_date=date_text(interview), contact_person=contact, contact_details=details, notes=notes))
                st.success("Application saved.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

    top1, top2, top3 = st.columns([2, 1, 1])
    search = top1.text_input("Search company, role, or location", key="tracker_search")
    selected = top2.selectbox("Filter status", ["All", *STATUSES])
    rows = list_applications(search, selected)
    top3.metric("Applications", len(rows))
    if not rows:
        st.info("No matching applications yet. Add one above to start tracking.")
        return

    today = date.today().isoformat()
    for row in rows:
        heading = f"{row['company']} — {row['role']} · {row['status']}"
        with st.expander(heading):
            if row.get("deadline"):
                if row["deadline"] < today and row["status"] not in ("Offer Received", "Rejected", "Withdrawn", "Closed"):
                    st.warning(f"Deadline passed: {row['deadline']}")
                elif row["deadline"] >= today:
                    st.caption(f"Deadline: {row['deadline']}")
            st.write(f"**Type:** {row['job_type']}  ·  **Location:** {row.get('location') or 'Not specified'}  ·  **Arrangement:** {row.get('work_arrangement') or 'Not specified'}")
            if row.get("application_url", "").startswith(("https://", "http://")):
                st.markdown(f"[Open application page]({row['application_url']})")
            st.write(f"Applied: {row.get('date_applied') or '—'} · Follow-up: {row.get('follow_up_date') or '—'} · Interview: {row.get('interview_date') or '—'}")
            if row.get("contact_person") or row.get("contact_details"):
                st.caption(f"Contact: {row.get('contact_person') or ''} {row.get('contact_details') or ''}")
            if row.get("notes"):
                st.write(row["notes"])
            with st.form(f"edit_{row['id']}"):
                new_status = st.selectbox("Update status", STATUSES, index=STATUSES.index(row["status"]))
                new_follow = st.text_input("Update follow-up date (YYYY-MM-DD)", value=row.get("follow_up_date") or "")
                new_notes = st.text_area("Update notes", value=row.get("notes") or "")
                save = st.form_submit_button("Save updates")
                if save:
                    updated = {key: row.get(key, "") for key in ("company", "role", "job_type", "location", "work_arrangement", "application_url", "date_applied", "deadline", "interview_date", "contact_person", "contact_details")}
                    updated.update(status=new_status, follow_up_date=new_follow, notes=new_notes)
                    save_application(updated, row["id"])
                    st.success("Application updated.")
                    st.rerun()
            confirm = st.checkbox("Confirm deletion", key=f"confirm_delete_{row['id']}")
            if st.button("Delete application", key=f"delete_{row['id']}", disabled=not confirm):
                delete_application(row["id"])
                st.success("Application deleted.")
                st.rerun()

    csv_bytes = pd.DataFrame(rows).drop(columns=["created_at", "updated_at"], errors="ignore").to_csv(index=False).encode("utf-8-sig")
    st.download_button("Download these filtered applications as CSV", data=csv_bytes, file_name="careerpilot_applications.csv", mime="text/csv")
