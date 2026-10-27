"""Settings and privacy controls."""
import streamlit as st

from database import DB_PATH, reset_database
from config import public_demo_mode


def render_settings() -> None:
    demo_mode = public_demo_mode()
    st.title("Settings & Privacy")
    st.write("CareerPilot AI keeps your resume analysis in the current session and can store tracker data locally when run on your computer.")
    st.subheader("Application information")
    st.write("**Version:** 0.1.0  ·  **Supported resume formats:** PDF and TXT")
    st.subheader("Local storage")
    st.code(str(DB_PATH), language=None)
    if demo_mode:
        st.caption("This public demo has database writes disabled. Cloud storage is temporary; do not enter sensitive information.")
    else:
        st.caption("The SQLite database is local and is not encrypted. Keep this computer and its backups secure. Database files are excluded from Git.")
    st.subheader("Privacy")
    if demo_mode:
        st.write("Resume and job description analysis runs in this app session. Database saving is disabled in this public demo. There are no user accounts, so do not enter sensitive information.")
    else:
        st.write("Resume and job description analysis runs locally. The tracker saves the application details you enter in SQLite. Do not enter information you do not want stored on this device; tracker notes and contact details are not encrypted. CareerPilot does not provide accounts or authentication.")
    st.subheader("Clear temporary session text")
    if st.button("Clear resume matcher text from this session"):
        keys = ("resume_input_text", "resume_uploaded_file", "job_description_input", "resume_analysis", "resume_profile")
        for key in keys:
            if key in st.session_state:
                del st.session_state[key]
        st.success("Temporary resume and analysis session values were cleared.")
    st.subheader("Reset local application data")
    if demo_mode:
        st.caption("No records are saved in public demo mode, so there is no shared database to reset.")
    else:
        st.warning("This permanently deletes application records, saved learning progress, and saved interview practice notes from the local database.")
        confirmed = st.checkbox("I understand that all locally saved records will be deleted.", key="confirm_reset_tracker")
        if st.button("Delete all local records", type="primary", disabled=not confirmed):
            reset_database()
            st.session_state["confirm_reset_tracker"] = False
            st.success("All locally saved records have been deleted.")
