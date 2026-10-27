"""Resume and job description skill-gap review with saved learning progress."""
import pandas as pd
import streamlit as st

from database import get_learning_progress, save_learning_progress
from services.skill_extractor import extract_skills

ESTIMATES = {"Python": "2-4 weeks", "SQL": "1-3 weeks", "Git": "1-2 weeks", "HTML": "1-2 weeks", "CSS": "1-2 weeks", "JavaScript": "3-6 weeks", "Data Structures and Algorithms": "4-8 weeks", "Machine Learning": "4-8 weeks"}
IDEAS = {"Python": "Complete beginner exercises, then automate one small task.", "SQL": "Practice SELECT, JOIN, GROUP BY, and build a small database report.", "Git": "Practice commits, branches, merges, and resolving a simple conflict.", "HTML": "Build a semantic one-page portfolio.", "CSS": "Style a responsive portfolio page using flexbox and grid.", "JavaScript": "Build a small interactive project and explain its state changes.", "Data Structures and Algorithms": "Work through progressively harder array, string, and hash map problems.", "Machine Learning": "Train and evaluate a small model on a public dataset."}


def render_skills_learning() -> None:
    st.title("Skills & Learning")
    st.write("Review skills detected in your current resume analysis and track a practical learning plan.")
    analysis = st.session_state.get("resume_analysis")
    if analysis is None:
        st.info("Run an analysis in Resume Matcher first. This page uses that session's resume and job description; it does not infer skills from your application records.")
        st.subheader("Start here")
        st.write("Practice Python fundamentals, SQL queries, Git version control, and explain one project clearly. Adapt this list to your target role.")
        return
    detected = list(analysis.resume_skills)
    required = list(analysis.required_skills)
    matched = list(analysis.matched_skills)
    missing = list(analysis.missing_skills)
    c1, c2, c3 = st.columns(3)
    c1.metric("Resume skills detected", len(detected))
    c2.metric("Required skills matched", len(matched))
    c3.metric("Required skills not detected", len(missing))
    st.caption("Keyword detection reflects supplied text only; it does not verify proficiency. A skill marked missing may simply be phrased differently.")
    st.write("**Detected in resume:** " + (", ".join(detected) or "None recognized"))
    st.write("**Detected in job description:** " + (", ".join(required) or "None recognized"))
    st.write("**Matched:** " + (", ".join(matched) or "None"))
    if not missing:
        st.success("No dictionary skills were detected as missing in this comparison. Review the job requirements manually too.")
        return
    st.subheader("Learning plan")
    st.caption("Duration is a rough estimate and varies by prior experience and practice time. Recommendations are editable and do not guarantee an internship.")
    saved = get_learning_progress()
    for skill in missing:
        prior = saved.get(skill, {})
        with st.expander(skill):
            with st.form(f"learning_{skill}"):
                priority = st.selectbox("Priority", ["High", "Medium", "Low"], index=["High", "Medium", "Low"].index(prior.get("priority", "Medium")))
                status = st.selectbox("Progress", ["Not started", "In progress", "Practiced", "Completed"], index=["Not started", "In progress", "Practiced", "Completed"].index(prior.get("status", "Not started")))
                estimate = st.text_input("Estimated time (your estimate)", value=prior.get("estimate", ESTIMATES.get(skill, "2-4 weeks")))
                recommendation = st.text_area("Practice recommendation", value=prior.get("recommendation", IDEAS.get(skill, f"Build a small project that demonstrates {skill}, then explain your decisions.")))
                if st.form_submit_button("Save learning progress"):
                    save_learning_progress(skill, priority, status, estimate, recommendation)
                    st.success("Learning progress saved locally.")
                    st.rerun()
    current = get_learning_progress()
    plan_rows = [current[s] for s in missing if s in current]
    if plan_rows:
        st.subheader("Saved plan overview")
        st.dataframe(pd.DataFrame(plan_rows)[["skill", "priority", "status", "estimate", "recommendation"]], use_container_width=True, hide_index=True)
