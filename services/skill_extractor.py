import re


SKILL_ALIASES = {
    "AWS": ("aws", "amazon web services"),
    "C#": ("c#", "c sharp"),
    "C++": ("c++", "cpp"),
    "CSS": ("css",),
    "Docker": ("docker",),
    "Git": ("git",),
    "HTML": ("html",),
    "Java": ("java",),
    "JavaScript": ("javascript", "js"),
    "Linux": ("linux",),
    "Machine Learning": ("machine learning", "ml"),
    "Node.js": ("node.js", "nodejs"),
    "Python": ("python",),
    "REST APIs": ("rest api", "rest apis"),
    "React": ("react",),
    "SQL": ("sql",),
    "SQLite": ("sqlite",),
    "Streamlit": ("streamlit",),
    "TypeScript": ("typescript", "ts"),
    "pandas": ("pandas",),
    "scikit-learn": ("scikit-learn", "sklearn"),
}


def _compile_skill_pattern(aliases: tuple[str, ...]) -> re.Pattern[str]:
    alternatives = "|".join(re.escape(alias) for alias in aliases)
    return re.compile(rf"(?<![A-Za-z0-9_.])(?:{alternatives})(?![A-Za-z0-9_])", re.IGNORECASE)


SKILL_PATTERNS = {
    skill: _compile_skill_pattern(aliases)
    for skill, aliases in SKILL_ALIASES.items()
}


def extract_skills(text: str) -> list[str]:
    """Return recognized canonical skill names in dictionary order."""
    return [
        skill
        for skill, pattern in SKILL_PATTERNS.items()
        if pattern.search(text)
    ]