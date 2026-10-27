import unicodedata


def normalize_text(text: str) -> str:
    """Normalize Unicode, case, and whitespace without changing stored input."""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(normalized.split())