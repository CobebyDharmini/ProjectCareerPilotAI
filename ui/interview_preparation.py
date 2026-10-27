"""Rule-based interview practice prompts and local practice notes."""
import streamlit as st

from database import list_interview_notes, save_interview_notes
from services.skill_extractor import extract_skills
from config import public_demo_mode

BASE_QUESTIONS = [
    ("Project explanation", "Tell me about a project you worked on. What problem did it solve, what was your contribution, and what would you improve?", "Medium", "Clear ownership, technical choices, and reflection."),
    ("Behavioral", "Describe a time you had to learn something unfamiliar. How did you approach it?", "Medium", "A specific example, learning process, and outcome."),
    ("Problem-solving", "How do you break an unfamiliar technical problem into smaller steps?", "Easy", "A structured approach, assumptions, and checking edge cases."),
    ("Resume-based", "Which experience on your resume best demonstrates your fit for this role?", "Medium", "Accurate evidence tied to the role's requirements."),
    ("Python fundamentals", "Explain the difference between a list and a tuple in Python. When might you use each?", "Easy", "Mutability, typical use, and a relevant example."),
    ("Programming logic", "How would you find duplicate values in a list? Explain your approach and its tradeoffs.", "Medium", "Correctness, data structures, and complexity awareness."),
]


def render_interview_preparation() -> None:
    st.title("Interview Preparation")
    st.write("Practice with locally generated prompts based on your target role and detected skills.")
    demo_mode = public_demo_mode()
    if demo_mode:
        st.info("Public demo mode: answers stay in your current session, but practice notes cannot be saved to shared storage.")
    with st.form("interview_setup"):
        a, b = st.columns(2)
        company = a.text_input("Company (optional)")
        role = b.text_input("Role", value=st.session_state.get("interview_role", ""))
        interview_type = st.selectbox("Interview type", ["General", "Behavioral", "Technical", "Project discussion", "Online assessment review"])
        description = st.text_area("Job description or role requirements (optional)", height=130)
        start = st.form_submit_button("Generate practice questions", type="primary")
    if start:
        skills = extract_skills(description)
        questions = list(BASE_QUESTIONS)
        if interview_type in ("General", "Behavioral"):
            questions.insert(1, ("Behavioral", "Tell me about a time you received feedback. What did you do with it?", "Medium", "Openness, a concrete response, and learning."))
        for skill in skills[:5]:
            questions.append(("Role-specific technical", f"Describe how you have used {skill}. What challenge came up, and how did you address it?", "Medium", f"A truthful example demonstrating {skill}; do not claim experience you do not have."))
        st.session_state["practice_questions"] = questions
        st.session_state["practice_context"] = {"company": company.strip(), "role": role.strip(), "type": interview_type}
    questions = st.session_state.get("practice_questions", [])
    if questions:
        context = st.session_state.get("practice_context", {})
        st.subheader(f"Practice set · {context.get('role') or 'General role'} · {context.get('type', 'General')}")
        if context.get("company"):
            st.caption("Practice prompts for " + context["company"] + ". These are generated templates, not verified company questions.")
        else:
            st.caption("These are generated practice prompts, not verified questions from a specific employer.")
        for index, (category, question, difficulty, evaluation) in enumerate(questions, 1):
            with st.expander(f"{index}. {category} · {difficulty}", expanded=index == 1):
                st.write(question)
                st.caption("The interviewer may be evaluating: " + evaluation)
                st.caption("Hint: Use a specific example, explain your reasoning, and be clear about your own contribution.")
                st.text_area("Draft your answer", key=f"interview_answer_{index}", height=130)
                st.checkbox("I answered with a specific example", key=f"interview_check_example_{index}")
                st.checkbox("I explained my reasoning and outcome", key=f"interview_check_reasoning_{index}")
        notes = st.text_area("Practice session notes", key="interview_session_notes", height=100)
        if st.button("Save practice notes", disabled=demo_mode):
            if notes.strip():
                save_interview_notes(context.get("company", ""), context.get("role", "") or "Unspecified role", context.get("type", "General"), notes.strip())
                st.success("Practice notes saved locally.")
            else:
                st.info("Add notes before saving.")
    saved = list_interview_notes()
    if saved:
        with st.expander(f"Saved practice notes ({len(saved)})"):
            for note in saved:
                st.markdown(f"**{note['role']} · {note['interview_type']} · {note['created_at']}**")
                st.write(note["notes"])
