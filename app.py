import streamlit as st
from datetime import date, timedelta

from database import STATUSES, list_applications


st.set_page_config(
    page_title="CareerPilot AI",
    page_icon="CP",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root { --ink: #172b34; --muted: #61747b; --accent: #176b78; --line: #dce6e7; }
    [data-testid="stAppViewContainer"] { background: #f4f7f7; }
    [data-testid="stMainBlockContainer"] { max-width: 1440px; padding-top: 2.2rem; }
    [data-testid="stSidebar"] { background: #172b34; border-right: 1px solid #29414a; min-width: 18rem !important; }
    [data-testid="stSidebar"] * {
        color: #f2f6f5;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] > label { color: #d4e0e3 !important; font-size: .8rem; font-weight: 700; }
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] { gap: .2rem; }
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label {
        width: 100%; min-height: 2.65rem; box-sizing: border-box; padding: .52rem .7rem;
        border: 1px solid transparent; border-radius: 8px; white-space: normal;
        line-height: 1.3; overflow-wrap: anywhere; align-items: center;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label p {
        color: #eef5f6 !important; font-size: .92rem; font-weight: 500; margin: 0;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label:hover { background: #233d47; }
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
        background: #24505a; border-color: #4e7c83;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p {
        color: #ffffff !important; font-weight: 700;
    }
    h1, h2, h3 {
        color: var(--ink); font-family: "Segoe UI", sans-serif; letter-spacing: -.025em;
    }
    [data-testid="stMarkdownContainer"] p { color: #40545c; line-height: 1.6; }
    [data-testid="stButton"] > button, [data-testid="stDownloadButton"] > button { border-radius: 8px; border-color: #b9c9cc; min-height: 2.65rem; font-weight: 600; }
    [data-testid="stButton"] > button[kind="primary"] { background: var(--accent); border-color: var(--accent); }
    [data-testid="stMetric"] { background: #fff; border: 1px solid var(--line); border-radius: 12px; padding: 1rem 1.1rem; box-shadow: 0 2px 7px #20363d0a; }
    [data-testid="stMetricLabel"] { color: var(--muted); }
    [data-testid="stExpander"] { background: #fff; border: 1px solid var(--line); border-radius: 10px; }
    [data-testid="stForm"] { background: #fff; border: 1px solid var(--line); border-radius: 12px; padding: 1rem; }
    [data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }
    hr { border-color: var(--line); }
    .eyebrow { color: var(--accent); font-size: .77rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }
    .hero { background: linear-gradient(120deg, #e8f2f2, #f8fbfa); border: 1px solid #d8e6e6; border-radius: 16px; padding: 1.4rem 1.6rem; margin-bottom: 1rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


PAGE_DETAILS = {
    "Resume Matcher": "Compare resume text with a job description.",
    "Job Opportunities": "Search current Adzuna listings and compare them locally with your analyzed resume.",
    "Application Tracker": "Track application status, interviews, and follow-ups.",
    "Skills & Learning": "Review detected skill gaps and track a practical learning plan.",
    "Interview Preparation": "Practice role-related questions and save session notes.",
    "Reports": "Export filtered application records and learning results.",
    "Settings & Privacy": "Review local storage and privacy controls.",
}


def navigate_to(page_name: str) -> None:
    st.session_state["active_page"] = page_name


st.sidebar.markdown("### CareerPilot AI")
st.sidebar.caption("Local-first career planning")
st.sidebar.markdown("---")
st.sidebar.radio(
    "Workspace",
    options=["Dashboard", *PAGE_DETAILS],
    key="active_page",
    label_visibility="collapsed",
)

active_page = st.session_state["active_page"]

if active_page == "Dashboard":
    records = list_applications()
    today = date.today()
    end_date = today + timedelta(days=14)
    active = [r for r in records if r["status"] not in ("Offer Received", "Rejected", "Withdrawn", "Closed")]
    interviews = [r for r in records if r["status"] in ("Interview Scheduled", "Interview Completed")]
    offers = [r for r in records if r["status"] == "Offer Received"]
    upcoming = [r for r in records if r.get("deadline") and today.isoformat() <= r["deadline"] <= end_date.isoformat() and r["status"] not in ("Offer Received", "Rejected", "Withdrawn", "Closed")]
    followups = [r for r in records if r.get("follow_up_date") and r["follow_up_date"] <= today.isoformat() and r["status"] not in ("Offer Received", "Rejected", "Withdrawn", "Closed")]

    st.markdown('<div class="hero"><div class="eyebrow">CareerPilot AI · Workspace</div><h1 style="margin:.35rem 0">Your career, in motion.</h1><p style="margin:0">A clear view of applications, upcoming actions, and interview practice.</p></div>', unsafe_allow_html=True)
    metrics = st.columns(5)
    metrics[0].metric("Applications", len(records))
    metrics[1].metric("In progress", len(active))
    metrics[2].metric("Interviews", len(interviews))
    metrics[3].metric("Offers", len(offers))
    metrics[4].metric("Follow-ups due", len(followups))

    left, right = st.columns([1.15, 1])
    with left:
        st.subheader("Application pipeline")
        status_counts = {status: sum(row["status"] == status for row in records) for status in STATUSES}
        nonzero = {label: value for label, value in status_counts.items() if value}
        if nonzero:
            st.bar_chart(nonzero, horizontal=True, color="#176b78")
        else:
            st.info("Your pipeline is ready when you are. Add your first opportunity to see progress here.")
        st.subheader("Upcoming deadlines")
        if upcoming:
            st.dataframe([{"Company": r["company"], "Role": r["role"], "Deadline": r["deadline"], "Status": r["status"]} for r in upcoming], use_container_width=True, hide_index=True)
        else:
            st.caption("No active deadlines in the next 14 days.")
    with right:
        st.subheader("Follow-up queue")
        if followups:
            st.dataframe([{"Company": r["company"], "Role": r["role"], "Follow up": r["follow_up_date"], "Status": r["status"]} for r in followups], use_container_width=True, hide_index=True)
        else:
            st.success("You’re up to date. No follow-ups are due.")
        st.subheader("Quick actions")
        for label, destination in (("Analyze a resume", "Resume Matcher"), ("Add or update an application", "Application Tracker"), ("Build a learning plan", "Skills & Learning"), ("Practice for an interview", "Interview Preparation")):
            st.button(label, key=f"quick_{destination}", use_container_width=True, on_click=navigate_to, args=(destination,))
else:
    if active_page == "Resume Matcher":
        from ui.resume_matcher import render_resume_matcher

        render_resume_matcher()
    elif active_page == "Job Opportunities":
        from ui.job_opportunities import render_job_opportunities

        render_job_opportunities()
    elif active_page == "Application Tracker":
        from ui.application_tracker import render_application_tracker

        render_application_tracker()
    elif active_page == "Settings & Privacy":
        from ui.settings import render_settings

        render_settings()
    elif active_page == "Skills & Learning":
        from ui.skills_learning import render_skills_learning

        render_skills_learning()
    elif active_page == "Interview Preparation":
        from ui.interview_preparation import render_interview_preparation

        render_interview_preparation()
    elif active_page == "Reports":
        from ui.reports import render_reports

        render_reports()
    else:
        st.title(active_page)
        st.write(PAGE_DETAILS[active_page])
        st.info("This section is not available yet. Its implementation is scheduled in the milestone shown above.")
