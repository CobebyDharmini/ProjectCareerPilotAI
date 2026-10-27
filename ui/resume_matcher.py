import streamlit as st

from services.analysis_advisor import SkillAction, build_skill_action_plan
from services.resume_matcher import MAX_INPUT_CHARS, ResumeAnalysis, analyze_resume
from services.resume_parser import extract_resume_text


def _show_skill_list(title: str, skills: tuple[str, ...], empty_message: str) -> None:
    st.subheader(title)
    if skills:
        st.write(" · ".join(skills))
    else:
        st.caption(empty_message)


def _show_analysis(analysis: ResumeAnalysis) -> None:
    st.subheader("Analysis results")
    similarity_column, coverage_column = st.columns(2)
    with similarity_column:
        if analysis.text_similarity is None:
            st.metric("Text Similarity", "Not available")
        else:
            st.metric("Text Similarity", f"{analysis.text_similarity:.0%}")
            st.progress(analysis.text_similarity)
    with coverage_column:
        if analysis.required_skills:
            skill_coverage = len(analysis.matched_skills) / len(analysis.required_skills)
            st.metric(
                "Detected required skills covered",
                f"{len(analysis.matched_skills)} of {len(analysis.required_skills)}",
            )
            st.progress(skill_coverage)
        else:
            st.metric("Detected required skills covered", "No recognized skills found")

    with st.expander("What these scores mean", expanded=True):
        st.write(
            "Text Similarity uses TF-IDF-weighted word overlap between the two texts. "
            "A score closer to 100% means the wording is more similar; it does not mean the resume is a better candidate."
        )
        st.write(
            "Detected required skills covered is the fraction of skills from CareerPilot AI's built-in dictionary "
            "that appeared in both texts. It does not measure how well you know those skills."
        )
        st.caption(analysis.similarity_note)
        st.caption("There is no universal passing score. These indicators do not predict interviews or hiring outcomes.")
        st.caption(
            "A missing skill means it was not detected in the supplied text; it does not prove you lack that skill."
        )

    matched_column, missing_column, additional_column = st.columns(3)
    with matched_column:
        _show_skill_list("Matched skills", analysis.matched_skills, "No recognized required skills matched.")
    with missing_column:
        _show_skill_list("Not detected", analysis.missing_skills, "No recognized required skills were missing.")
    with additional_column:
        _show_skill_list("Additional skills", analysis.additional_skills, "No other recognized skills detected.")

    st.subheader("How to improve your resume")
    st.markdown(
        "- For a matched skill, add one accurate example showing where you used it. A useful bullet structure is "
        "**action + task + tool + result**; include numbers only when you can support them.\n"
        "- For a skill marked not detected, add it only if you have actually used it. Name the project or task that "
        "demonstrates it; otherwise, leave it out and work on the gap first.\n"
        "- Reuse relevant wording from the job description naturally when it accurately describes your experience. "
        "Avoid keyword stuffing or changing facts to raise a score.\n"
        "- Put the most relevant project and experience evidence near the top, and make your role and contribution clear."
    )

    action_plan = build_skill_action_plan(analysis.missing_skills)
    if action_plan:
        st.subheader("Practical skill-gap plan")
        st.write("Work through the gaps that matter most to this role. These suggestions are starting points, not guarantees.")
        for action in action_plan[:5]:
            _show_skill_action(action)
        if len(action_plan) > 5:
            with st.expander(f"More ideas for {len(action_plan) - 5} additional gaps"):
                for action in action_plan[5:]:
                    _show_skill_action(action)
    else:
        st.success("No skills from the current dictionary were missing. Review the role-specific requirements manually too.")

    report_lines = [
        "CareerPilot AI - Resume Match Summary",
        "Text Similarity: "
        + (f"{analysis.text_similarity:.0%}" if analysis.text_similarity is not None else "Not available"),
        "Detected required skills covered: "
        + (
            f"{len(analysis.matched_skills)} of {len(analysis.required_skills)}"
            if analysis.required_skills
            else "No recognized required skills found"
        ),
        "Matched skills: " + (", ".join(analysis.matched_skills) or "None detected"),
        "Skills not detected: " + (", ".join(analysis.missing_skills) or "None"),
        "Additional resume skills: " + (", ".join(analysis.additional_skills) or "None detected"),
        "",
        "Resume improvement checklist:",
        "- Add accurate examples for matched skills, including outcomes only when supportable.",
        "- Add a not-detected skill only if you can demonstrate real experience with it.",
        "- Use relevant job-description wording naturally; do not keyword stuff or alter facts.",
        "",
        "Skill-gap practice plan:",
        *[
            f"{action.skill}: Practice: {action.practice_activity} Project: {action.project_idea} "
            f"Learn: {action.learning_resource}"
            for action in action_plan
        ],
        "",
        analysis.similarity_note,
        "Skill detection is based only on supplied text and does not verify proficiency.",
        "This report is guidance, not a prediction of interviews, hiring, or qualification.",
    ]
    st.download_button(
        "Download analysis summary",
        data="\n".join(report_lines),
        file_name="careerpilot_resume_analysis.txt",
        mime="text/plain",
    )
    st.caption("This analysis is held in this browser session only and is not saved to a database.")


def _show_skill_action(action: SkillAction) -> None:
    with st.expander(action.skill):
        st.markdown(f"**Practice:** {action.practice_activity}")
        st.markdown(f"**Project idea:** {action.project_idea}")
        if action.learning_url:
            st.markdown(f"**Learn:** [{action.learning_resource}]({action.learning_url})")
        else:
            st.markdown(f"**Learn:** {action.learning_resource}")
        st.caption("Only add this skill to your resume after gaining and being able to demonstrate the experience.")


def render_resume_matcher() -> None:
    st.title("Resume and job matcher")
    st.write("Compare the wording and recognized skills in your resume with a job description.")

    if "resume_analysis" not in st.session_state:
        st.session_state["resume_analysis"] = None

    input_method = st.radio("Resume input", ("Paste text", "Upload PDF or TXT"), horizontal=True)
    with st.form("resume_match_form"):
        resume_text = ""
        uploaded_file = None
        if input_method == "Paste text":
            resume_text = st.text_area(
                "Resume text",
                height=220,
                max_chars=MAX_INPUT_CHARS,
                help="Your resume stays in this app session and is not sent to an external service.",
                key="resume_input_text",
            )
        else:
            uploaded_file = st.file_uploader(
                "Choose a PDF or UTF-8 TXT file (5 MB maximum)",
                type=["pdf", "txt"],
                max_upload_size=5,
                key="resume_uploaded_file",
            )

        job_description = st.text_area(
            "Job description",
            height=220,
            max_chars=MAX_INPUT_CHARS,
            key="job_description_input",
        )
        submitted = st.form_submit_button("Analyze match", type="primary")

    if submitted:
        st.session_state["resume_analysis"] = None
        st.session_state["resume_profile"] = None
        try:
            with st.spinner("Reading your resume and analyzing the match..."):
                if input_method == "Upload PDF or TXT":
                    if uploaded_file is None:
                        raise ValueError("Choose a resume file, or switch to Paste text.")
                    resume_text = extract_resume_text(uploaded_file.name, uploaded_file.getvalue())
                analysis = analyze_resume(resume_text, job_description)
        except ValueError as error:
            st.error(str(error))
        else:
            st.session_state["resume_analysis"] = analysis
            st.session_state["resume_profile"] = {
                "text": resume_text,
                "skills": analysis.resume_skills,
            }

    analysis = st.session_state["resume_analysis"]
    if analysis is not None:
        _show_analysis(analysis)
