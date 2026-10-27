# CareerPilot AI

CareerPilot AI is a local-first career preparation and internship application manager for students and entry-level job seekers. The dashboard, resume matcher, local PDF/TXT text extraction, SQLite application tracker, skill learning plans, interview practice, CSV exports, and settings/privacy controls are implemented; other features are being built incrementally.

## Current status

- Streamlit entry point and workspace navigation
- Resume text matching with TF-IDF cosine similarity and rule-based skill detection
- PDF and TXT resume upload (up to 5 MB) or pasted text
- Detailed results with text-similarity explanation, detected skill coverage, resume-writing guidance, and skill-specific practice, project, and learning suggestions
- Credential-free Remotive remote-job search with source attribution, local filters, and resume-based match explanations
- Google Search fallback for other roles and locations; results open externally and are not scraped into the app
- No sample records or hardcoded dashboard metrics
- Application tracker with SQLite persistence, status updates, search, deadline indicators, and per-record deletion
- Filtered tracker CSV export and confirmed local tracker reset
- Settings page with local storage information, privacy explanation, and session text clearing
- Skill-gap review from the current resume analysis with editable, locally saved learning progress
- Rule-based interview practice prompts with private session answers and saved practice notes
- Reports for filtered applications, learning plans, and current-session resume analysis

## Technology

- Python 3.12 (recommended for Streamlit Community Cloud); local development was tested with Python 3.14.6
- Streamlit
- pandas
- scikit-learn
- SQLite (application records stored locally in `data/careerpilot.db`)
- pytest

The core analysis runs locally without an external AI API. The similarity score describes text similarity, not hiring probability. Detected or missing skills are based only on supplied text and do not verify proficiency.

Scikit-learn provides TF-IDF cosine similarity when its compiled extensions can load. If the platform blocks those extensions, the matcher uses a local pure-Python TF-IDF fallback instead. PyMuPDF extracts selectable text from PDFs locally; scanned image-only PDFs need OCR or pasted text. Recognized skills come from a small maintainable dictionary and do not represent a complete skills inventory.

The Opportunities page uses Remotive's public remote-jobs API; no API key or account is required. CareerPilot caches the public catalog for eight hours, within Remotive's guidance of no more than four API requests per day. Remotive says listings may be delayed by 24 hours, requires visible source attribution and a link back, and prohibits resubmitting its listings to other job boards. This source is remote-only and is not a comprehensive search of local or onsite India jobs. Location eligibility, posting status, and application details should be confirmed on each linked Remotive listing.

The page also queries OpenIntern's public technology-internship API when a user searches. Results are cached locally in Streamlit for six hours and direct applications to the employer's listing page. OpenIntern's feed has multiple regions but is not a comprehensive India job feed. LinkedIn Jobs, Unstop internships/jobs/competitions, Internshala, and National Career Service are available as external Google searches filtered to each source's public pages; results are not imported or verified by CareerPilot. LinkedIn's job posting API is for approved partners, so this project does not use it. No resume text is sent to any provider or search link.

Google Search is available as a fallback for other roles and locations. It uses only the selected role/location and up to five detected skill names, opens results externally, and does not import or verify them. Google's Custom Search JSON API is closed to new customers and existing access is scheduled to end on January 1, 2027, so the project does not depend on that API. An Adzuna client and blank credential templates remain optional, but the current Opportunities UI does not call Adzuna.

## Run on Windows

From the project folder in PowerShell, install the dependencies into the existing virtual environment and start the app:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Streamlit normally opens the app at `http://localhost:8501`.

## Tests

Install development dependencies once with `pip install -r requirements-dev.txt`, then run tests from the project folder with:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The suite covers resume analysis, PDF/TXT extraction, opportunity searches, application storage, learning progress, interview notes, and public-demo storage safeguards.

## Privacy and storage

Application tracker records persist in local SQLite at `data/careerpilot.db`. Resume analysis stays in the current Streamlit session and is not sent to an external analysis service. SQLite is unencrypted and should not be treated as secure storage for sensitive information. Local database files and generated user data are excluded from Git by `.gitignore`.

## Deployment

For public hosting, set `CAREERPILOT_DEMO_MODE = "true"` in Streamlit Community Cloud secrets. This disables database writes because the project has no login or per-user database isolation. Resume text and practice answers remain session-only. Hosted SQLite storage is temporary and is not suitable for private or durable user records.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for Community Cloud setup and verification. GitHub Pages cannot run the Python Streamlit app.
