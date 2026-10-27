"""Runtime switches controlled through environment variables or Streamlit secrets."""
import os


def public_demo_mode() -> bool:
    """True when the public hosted instance must not save shared user records."""
    return os.environ.get("CAREERPILOT_DEMO_MODE", "").strip().casefold() in {"1", "true", "yes", "on"}
