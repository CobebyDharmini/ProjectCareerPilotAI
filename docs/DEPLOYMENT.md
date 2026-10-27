# Deployment

CareerPilot AI uses Streamlit Community Cloud. The public GitHub repository is `CobebyDharmini/ProjectCareerPilotAI`; the app entry point is `app.py` on branch `main`.

## Public demo privacy setting

This app has no authentication or per-user database isolation. Before deploying publicly, add this value in the Community Cloud **Secrets** field:

```toml
CAREERPILOT_DEMO_MODE = "true"
```

This disables writes to the application tracker, learning progress, and interview notes. The reset control is also disabled. Resume text and draft interview answers remain in the visitor's Streamlit session. Do not enter sensitive information. Hosted SQLite files are temporary and are not suitable for durable or private user data.

No API credentials are required. Do not paste credentials into GitHub or application code.

## Deploy

1. Open [Streamlit Community Cloud](https://share.streamlit.io/) and sign in with the GitHub account that owns the repository.
2. Click **Create app**, then select **Yup, I have an app**.
3. Choose repository `CobebyDharmini/ProjectCareerPilotAI`, branch `main`, and main file path `app.py`.
4. In **Advanced settings**, choose Python **3.12** (the documented Community Cloud default).
5. In **Secrets**, paste the public-demo setting above.
6. Click **Deploy** and inspect build logs if startup fails.
7. Open the generated `*.streamlit.app` address. Check the navigation, resume analysis, opportunity search, and confirm that database save controls are disabled.

Community Cloud requires GitHub access to the repository. It runs the application from GitHub; GitHub Pages only serves static files and cannot run Python/Streamlit.

## Hosting limitations

Hosted SQLite is temporary and may disappear after restarts or redeployments. For private multi-user persistence, add proper authentication, per-user authorization, and durable data storage before enabling writes.
