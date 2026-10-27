from datetime import datetime

import streamlit as st

from services.job_matching import JobMatch, score_job_match
from services.google_job_search import build_google_job_search_url
from services.opportunity_platforms import PLATFORM_PATHS, build_platform_search_url
from services.openintern_search import (
    OPENINTERN_SOURCE_URL,
    OpenInternSearchError,
    fetch_openintern_jobs,
)
from services.job_search import JobListing
from services.remotive_search import (
    REMOTIVE_SOURCE_URL,
    RemoteJobCatalog,
    RemoteJobSearchError,
    fetch_remotive_jobs,
    filter_remotive_jobs,
)


EMPLOYMENT_OPTIONS = {
    "Any": "",
    "Full time": "full_time",
    "Part time": "part_time",
    "Contract": "contract",
    "Freelance": "freelance",
    "Internship": "internship",
}
FRESHNESS_OPTIONS = {"Any date": None, "Past week": 7, "Past 14 days": 14, "Past month": 30, "Past 90 days": 90}
SORT_OPTIONS = {
    "Best match": "hybrid",
    "Newest": "date",
    "Company A–Z": "company",
}
SALARY_FILTERS = {
    "Any salary": "any",
    "Salary disclosed": "listed",
    "No salary disclosed": "not_listed",
}


@st.cache_data(ttl=8 * 60 * 60, max_entries=1, show_spinner=False)
def _cached_remotive_catalog(limit: int = 100) -> RemoteJobCatalog:
    return fetch_remotive_jobs(limit=limit)


@st.cache_data(ttl=6 * 60 * 60, max_entries=20, show_spinner=False)
def _cached_openintern(query: str):
    return fetch_openintern_jobs(query=query, limit=30)


def _format_salary(job: JobListing) -> str:
    if job.salary_display:
        return f"Salary as listed: {job.salary_display}"
    if job.salary_min is None and job.salary_max is None:
        return "Salary not listed by source"
    minimum = f"₹{job.salary_min:,.0f}" if job.salary_min is not None else None
    maximum = f"₹{job.salary_max:,.0f}" if job.salary_max is not None else None
    if minimum and maximum:
        salary = f"{minimum}–{maximum}"
    else:
        salary = minimum or f"Up to {maximum}"
    period = "; source-predicted" if job.salary_is_predicted else ""
    return f"{salary} INR (period not specified{period})"


def _format_date(value: str | None) -> str:
    if not value:
        return "Posting date not provided"
    try:
        posted = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return f"Listed {posted.strftime('%d %b %Y')}"
    except ValueError:
        return f"Source date: {value}"


def _profile_match(job: JobListing, profile: dict[str, object] | None) -> JobMatch | None:
    if profile is None:
        return None
    resume_text = profile.get("text")
    resume_skills = profile.get("skills")
    if not isinstance(resume_text, str) or not isinstance(resume_skills, tuple):
        return None
    return score_job_match(resume_text, resume_skills, job)


def _render_job(job: JobListing, match: JobMatch | None, fetched_at: str) -> None:
    with st.container(border=True):
        logo_column, title_column, score_column = st.columns([0.6, 3.4, 1])
        with logo_column:
            if job.company_logo_url:
                st.image(job.company_logo_url, width=44)
        with title_column:
            st.subheader(job.title)
            st.write(f"**{job.company}** · {job.location}")
        with score_column:
            if match is not None and match.score is not None:
                st.metric("Resume match", f"{match.score}%")
            elif match is not None:
                st.metric("Resume match", "Not enough data")

        employment = " · ".join(
            value.replace("_", " ").title()
            for value in (job.contract_time, job.contract_type)
            if value
        ) or "Employment type not listed"
        work_mode = job.work_mode or "Work mode not provided"
        st.write(f"{_format_date(job.posted_at)} · {work_mode} · {employment} · {_format_salary(job)}")
        if job.source == "Remotive":
            st.caption(
                f"Fetched {fetched_at} UTC. Remotive states its public API data may be delayed by 24 hours; "
                "check the linked posting for current availability and eligibility."
            )
        else:
            st.caption(
                f"Fetched {fetched_at} UTC. Availability is not independently verified; confirm on the source page. "
                "Experience and work mode are not provided as structured fields by this source."
            )

        if match is not None:
            st.write(match.explanation)
            if match.matching_skills:
                st.write("**Resume skills also mentioned:** " + ", ".join(match.matching_skills))
            if match.missing_required_skills:
                st.write("**Required in available text, not confirmed in resume:** " + ", ".join(match.missing_required_skills))
            if match.preferred_skills_found:
                st.write("**Preferred skills found in resume:** " + ", ".join(match.preferred_skills_found))
            if match.unconfirmed_skills:
                st.caption("Other listed skills not confirmed in resume: " + ", ".join(match.unconfirmed_skills))

        with st.expander("Listing details"):
            st.write(job.description or "The source did not provide a description snippet.")
            st.write("**Category:** " + (job.category or "Not provided"))
            if job.required_skills:
                st.write("**Required skills identified in snippet:** " + ", ".join(job.required_skills))
            if job.preferred_skills:
                st.write("**Preferred skills identified in snippet:** " + ", ".join(job.preferred_skills))
            if job.unclassified_skills:
                st.write("**Other recognized skills in snippet:** " + ", ".join(job.unclassified_skills))
            if job.source == "Remotive":
                st.caption("Role restrictions and the complete posting are on Remotive. Follow the source link to verify details.")
            st.markdown(f"**Source:** [{job.source}]({job.source_url})")

        _render_source_attribution(job)
        st.link_button("Apply on listing site", job.application_url, type="primary")


def _go_to_matcher() -> None:
    st.session_state["active_page"] = "Resume Matcher"


def _render_source_attribution(job: JobListing) -> None:
    st.markdown(
        f'<a href="{job.source_url}" target="_blank" rel="noopener noreferrer" '
        f'style="display:inline-block;min-width:116px;height:23px;line-height:23px;font-weight:600;">{job.source}</a>',
        unsafe_allow_html=True,
    )


def render_job_opportunities() -> None:
    st.title("Job opportunities")
    st.write("Search live public feeds and explore established job boards. Resume matching runs locally in this app.")

    profile = st.session_state.get("resume_profile")
    if profile is None:
        st.info("Browse remote jobs without a resume, or analyze one to see local resume-based recommendations.")
        st.button("Analyze a resume", on_click=_go_to_matcher)
    else:
        skills = profile.get("skills", ())
        st.caption(
            f"Using this session's analyzed resume ({len(skills)} recognized skills). "
            "Resume text is not sent to job providers."
        )
    st.caption("Resume content stays in this session and is never sent to an opportunity provider. Confirm details and eligibility on every source site.")

    if "remote_job_query" not in st.session_state:
        st.session_state["remote_job_query"] = ""
    if "job_search_location" not in st.session_state:
        st.session_state["job_search_location"] = "India"

    try:
        with st.spinner("Loading public remote listings..."):
            catalog = _cached_remotive_catalog(100)
    except RemoteJobSearchError as error:
        catalog = None
        st.error(str(error))

    with st.form("job_search_form"):
        keyword_column, location_column, company_column = st.columns([2, 1, 1])
        with keyword_column:
            role_query = st.text_input("Role or keywords", key="remote_job_query", max_chars=100)
        with location_column:
            location = st.text_input(
                "India location",
                placeholder="Hyderabad, Bengaluru, Pune…",
                max_chars=80,
                key="job_search_location",
            )
        with company_column:
            company = st.text_input("Company", max_chars=80)

        freshness_column, salary_column, employment_column, sort_column = st.columns(4)
        with freshness_column:
            freshness_label = st.selectbox("Posted", list(FRESHNESS_OPTIONS))
        with salary_column:
            salary_filter_label = st.selectbox("Salary", list(SALARY_FILTERS))
        with employment_column:
            employment_label = st.selectbox("Employment", list(EMPLOYMENT_OPTIONS))
        with sort_column:
            sort_label = st.selectbox("Sort", list(SORT_OPTIONS))
        page_size = st.selectbox("Results per page", (10, 20, 50), index=1)
        submitted = st.form_submit_button("Search remote jobs", type="primary")
        google_submitted = st.form_submit_button("Search Google", type="secondary")

    if google_submitted:
        profile_skills = profile.get("skills", ()) if isinstance(profile, dict) else ()
        st.session_state["google_job_search_url"] = build_google_job_search_url(
            role_query,
            location,
            profile_skills if isinstance(profile_skills, tuple) else (),
        )
    google_url = st.session_state.get("google_job_search_url")
    if isinstance(google_url, str):
        st.link_button("Open Google results", google_url)
        st.caption(
            "Opens Google Search using only this role, location, and up to five detected skill names. "
            "CareerPilot does not import or verify Google results; review each employer's posting directly."
        )

    with st.container(border=True):
        st.subheader("Technology internships")
        st.caption(f"Live public listings from OpenIntern. This source focuses on technology internships and includes opportunities in several regions; it is not a comprehensive India jobs feed. [View OpenIntern]({OPENINTERN_SOURCE_URL}).")
        with st.form("openintern_search_form"):
            oi_query = st.text_input("Internship role keywords", value=role_query, placeholder="software engineer, data science, product")
            oi_submitted = st.form_submit_button("Search internship listings", type="primary")
        if oi_submitted:
            st.session_state["openintern_query"] = oi_query.strip()
            st.session_state["openintern_search_started"] = True
        if st.session_state.get("openintern_search_started"):
            try:
                query = str(st.session_state.get("openintern_query", ""))
                with st.spinner("Searching public technology internships..."):
                    internships = _cached_openintern(query)
                st.caption(f"{len(internships.jobs)} postings in this result page · {internships.total_count:,} role families reported by source · fetched {internships.fetched_at[:19]} UTC. Results refresh from the cached feed every six hours.")
                if not internships.jobs:
                    st.info("No internship listings matched these role keywords. Try broader terms or explore other boards below.")
                for internship in internships.jobs[:20]:
                    with st.container(border=True):
                        title_col, location_col = st.columns([3, 1])
                        title_col.markdown(f"**{internship.title}**")
                        title_col.write(internship.company)
                        location_col.caption(internship.location)
                        meta = " · ".join((*internship.regions, *internship.roles))
                        if internship.is_remote:
                            meta = "Remote" + (f" · {meta}" if meta else "")
                        if meta:
                            st.caption(meta)
                        if internship.posted_at:
                            st.caption(f"Listed {internship.posted_at}")
                        if internship.excerpt:
                            st.write(internship.excerpt)
                        st.link_button("Apply on employer site", internship.application_url, type="primary")
            except OpenInternSearchError as error:
                st.warning(f"OpenIntern listings are unavailable right now. {error}")

    with st.expander("Explore LinkedIn, Unstop, Internshala, and more"):
        st.write("These open Google results filtered to each platform's public pages. Follow the listing link to verify details and apply. CareerPilot does not import, verify, or store those listings.")
        for platform in PLATFORM_PATHS:
            url = build_platform_search_url(platform, role_query, location)
            st.link_button(f"Search {platform}", url, use_container_width=True)

    if submitted:
        st.session_state["remote_job_filters"] = {
            "query": role_query,
            "location": location,
            "company": company,
            "max_days_old": FRESHNESS_OPTIONS[freshness_label],
            "salary_filter": SALARY_FILTERS[salary_filter_label],
            "employment_filter": EMPLOYMENT_OPTIONS[employment_label],
            "results_per_page": page_size,
            "sort_by": SORT_OPTIONS[sort_label],
        }
        st.session_state["visible_remote_jobs"] = page_size

    if catalog is None:
        st.info("Remote listings could not be loaded. Try Google Search or retry later.")
        return

    filters = st.session_state.get("remote_job_filters")
    if not isinstance(filters, dict):
        filters = {
            "query": str(st.session_state["remote_job_query"]),
            "location": str(st.session_state["job_search_location"]),
            "company": "",
            "max_days_old": None,
            "salary_filter": "any",
            "employment_filter": "",
            "results_per_page": 20,
            "sort_by": "hybrid",
        }

    try:
        filtered_jobs = filter_remotive_jobs(
            catalog.jobs,
            query=str(filters["query"]),
            location=str(filters["location"]),
            company=str(filters["company"]),
            employment_type=str(filters["employment_filter"]),
            posted_within_days=filters["max_days_old"],
            salary_filter=str(filters["salary_filter"]),
        )
    except ValueError as error:
        st.error(str(error))
        return

    broadened_search = False
    if not filtered_jobs and str(filters["query"]).strip():
        filtered_jobs = filter_remotive_jobs(
            catalog.jobs,
            location=str(filters["location"]),
            company=str(filters["company"]),
            employment_type=str(filters["employment_filter"]),
            posted_within_days=filters["max_days_old"],
            salary_filter=str(filters["salary_filter"]),
        )
        broadened_search = bool(filtered_jobs)

    jobs_with_matches = [
        (job, _profile_match(job, profile if isinstance(profile, dict) else None))
        for job in filtered_jobs
    ]
    sort_by = str(filters["sort_by"])
    if sort_by == "company":
        jobs_with_matches.sort(key=lambda pair: pair[0].company.casefold())
    elif sort_by == "date" or profile is None:
        jobs_with_matches.sort(key=lambda pair: pair[0].posted_at or "", reverse=True)
    elif profile is not None:
        jobs_with_matches.sort(
            key=lambda pair: pair[1].score if pair[1] is not None and pair[1].score is not None else -1,
            reverse=True,
        )

    fetched_label = catalog.fetched_at
    st.caption(
        f"{len(filtered_jobs):,} matching public remote jobs from {len(catalog.jobs):,} feed listings · fetched {fetched_label} UTC. "
        "Remotive states public listings may be delayed by 24 hours."
    )
    if broadened_search:
        st.info("No exact role/keyword matches were found. Showing other remote jobs that match the remaining filters.")
    if not jobs_with_matches:
        if filters["employment_filter"] == "internship":
            st.info(
                "Remotive's current public feed has no internships matching these filters. "
                "Check Google or employer career pages for other openings."
            )
            internship_url = build_google_job_search_url(
                str(filters["query"]),
                str(filters["location"]),
                employment_keyword="internship",
            )
            st.link_button("Search Google for internships", internship_url)
            st.caption("Google results open externally and are not imported or verified by CareerPilot.")
        else:
            st.info("No remote jobs match these filters. Try broader role terms, another location, or a longer date range.")
            st.markdown(f"Try [Google Search]({build_google_job_search_url(str(filters['query']), str(filters['location']))}) for other job sources.")
        return

    visible_count = int(st.session_state.get("visible_remote_jobs", filters["results_per_page"]))
    visible_jobs = jobs_with_matches[:visible_count]
    if profile is not None:
        st.subheader("Recommended for you")
        st.caption("Sorted by local resume-match score; this is not an ATS score or a hiring prediction.")
        st.caption(
            "Weights: required skills 60%, preferred 10%, unclassified skills 10%, and description similarity 20%. "
            "This remote feed does not provide structured education or experience requirements, so those are not scored."
        )
        for job, match in visible_jobs[:3]:
            _render_job(job, match, job.fetched_at)

    st.subheader("All matching remote jobs")
    for job, match in visible_jobs:
        _render_job(job, match, job.fetched_at)

    if len(jobs_with_matches) > visible_count:
        if st.button("Load more remote jobs"):
            st.session_state["visible_remote_jobs"] = visible_count + int(filters["results_per_page"])
            st.rerun()

    st.divider()
    st.markdown(f"Remote jobs and application links supplied by [Remotive]({REMOTIVE_SOURCE_URL}).")
    st.caption("This feed is remote-only and delayed by up to 24 hours. Verify eligibility and current status on each linked Remotive posting.")
