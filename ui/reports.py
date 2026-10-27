"""Local exports for tracker, skill-gap, and resume-analysis results."""
import pandas as pd
import streamlit as st

from database import list_applications, get_learning_progress, list_interview_notes


def render_reports() -> None:
    st.title("Reports & Exports")
    st.write("Export local records and current-session analysis summaries.")
    st.subheader("Application tracker export")
    a, b = st.columns(2)
    search = a.text_input("Filter by company, role, or location")
    status = b.selectbox("Filter status", ["All", "Interested", "Preparing", "Applied", "Online Assessment", "Interview Scheduled", "Interview Completed", "Offer Received", "Rejected", "Withdrawn", "Closed"])
    records = list_applications(search, status)
    st.caption(f"This export includes {len(records)} matching application record(s).")
    if records:
        frame = pd.DataFrame(records).drop(columns=["created_at", "updated_at"], errors="ignore")
        st.dataframe(frame, use_container_width=True, hide_index=True)
        st.download_button("Download filtered applications (CSV)", frame.to_csv(index=False).encode("utf-8-sig"), "careerpilot_applications.csv", "text/csv")
    else:
        st.info("No records match these filters.")

    st.subheader("Resume analysis summary")
    analysis = st.session_state.get("resume_analysis")
    if analysis:
        report = ["CareerPilot AI — Resume Match Summary", f"Text Similarity: {analysis.text_similarity:.0%}" if analysis.text_similarity is not None else "Text Similarity: Not available", "Matched skills: " + (", ".join(analysis.matched_skills) or "None detected"), "Skills not detected: " + (", ".join(analysis.missing_skills) or "None"), "Additional resume skills: " + (", ".join(analysis.additional_skills) or "None"), "", "This compares supplied text and recognized keywords; it is not a hiring prediction."]
        st.download_button("Download current-session analysis (TXT)", "\n".join(report), "careerpilot_analysis_summary.txt", "text/plain")
    else:
        st.info("Run Resume Matcher to create a current-session analysis summary.")

    st.subheader("Saved learning plan")
    progress = list(get_learning_progress().values())
    if progress:
        skills = pd.DataFrame(progress)
        st.dataframe(skills, use_container_width=True, hide_index=True)
        st.download_button("Download learning plan (CSV)", skills.to_csv(index=False).encode("utf-8-sig"), "careerpilot_learning_plan.csv", "text/csv")
    else:
        st.info("No learning progress has been saved yet.")
    notes = list_interview_notes()
    st.caption(f"Saved interview practice note entries: {len(notes)}. Practice answers remain in the current session; saved entries are available on Interview Preparation.")
