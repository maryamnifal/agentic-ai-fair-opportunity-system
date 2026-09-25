"""
A small, hand-authored, explainable skill relatedness taxonomy.

This is intentionally simple (a lookup table, not ML) so the scoring logic
can be explained line-by-line in a viva. Every entry answers: "if the
evidence mentions skill X, what claims does that reasonably support, and
how strongly?"

Keys are normalized (lowercase) skill names.
"""

from typing import Dict, List

# skill (lowercase) -> other skills it STRONGLY implies (e.g. a framework implies its language)
STRONG_IMPLIES: Dict[str, List[str]] = {
    "django": ["python", "rest api", "web development", "backend development"],
    "flask": ["python", "rest api", "web development", "backend development"],
    "fastapi": ["python", "rest api", "web development", "backend development"],
    "spring boot": ["java", "rest api", "backend development"],
    "spring": ["java", "backend development"],
    "react": ["javascript", "frontend development", "web development"],
    "react native": ["javascript", "mobile development"],
    "vue": ["javascript", "frontend development"],
    "angular": ["typescript", "javascript", "frontend development"],
    "node.js": ["javascript", "backend development"],
    "express": ["javascript", "node.js", "backend development"],
    "tensorflow": ["python", "machine learning", "deep learning"],
    "pytorch": ["python", "machine learning", "deep learning"],
    "scikit-learn": ["python", "machine learning"],
    "pandas": ["python", "data analysis"],
    "numpy": ["python", "data analysis"],
    "django rest framework": ["django", "python", "rest api", "backend development"],
    "laravel": ["php", "backend development"],
    "ruby on rails": ["ruby", "backend development"],
    ".net": ["c#", "backend development"],
    "asp.net": ["c#", "backend development", "web development"],
    "android studio": ["java", "kotlin", "mobile development"],
    "swiftui": ["swift", "mobile development"],
}

# skill (lowercase) -> other skills it WEAKLY / loosely relates to (partial, not implication)
WEAK_RELATED: Dict[str, List[str]] = {
    "data analysis": ["machine learning", "statistics"],
    "pandas": ["machine learning"],
    "numpy": ["machine learning"],
    "sql": ["data analysis", "database design"],
    "excel": ["data analysis"],
    "rest api": ["api design", "backend development"],
    "docker": ["devops", "deployment"],
    "git": ["version control", "collaboration"],
    "html": ["web development"],
    "css": ["web development"],
    "javascript": ["web development"],
}

# "language families" used purely for contradiction detection: if evidence text
# explicitly and exclusively claims one family, a claim from a *different*
# family is treated as a potential contradiction rather than just "unsupported".
LANGUAGE_FAMILIES: Dict[str, List[str]] = {
    "python": ["python", "django", "flask", "fastapi", "pandas", "numpy",
               "tensorflow", "pytorch", "scikit-learn", "django rest framework"],
    "java": ["java", "spring", "spring boot", "android studio"],
    "javascript": ["javascript", "typescript", "react", "vue", "angular",
                   "node.js", "express", "react native"],
    "php": ["php", "laravel"],
    "ruby": ["ruby", "ruby on rails"],
    "c#": ["c#", ".net", "asp.net"],
    "swift": ["swift", "swiftui"],
}

# Phrases in evidence descriptions that signal an EXCLUSIVE technology choice,
# used to detect contradictions (e.g. "entirely in Java" contradicts a Python claim).
EXCLUSIVITY_MARKERS = [
    "entirely using", "entirely in", "solely using", "solely in",
    "exclusively using", "exclusively in", "written entirely in",
    "built entirely with", "no use of", "without using",
]


# Common aliases/abbreviations -> canonical taxonomy key. Kept as a flat lookup
# (no fuzzy matching) so it stays explainable in a viva. Where possible, these
# are aligned with Member A's skill_taxonomy.json aliases so a claim like
# "psql" resolves to the same canonical name on both sides of the system.
ALIASES: Dict[str, str] = {
    "js": "javascript",
    "ts": "typescript",
    "postgres": "postgresql",
    "psql": "postgresql",
    "postgres db": "postgresql",
    "ml": "machine learning",
    "dl": "deep learning",
    "py": "python",
    "python3": "python",
    "reactjs": "react",
    "react.js": "react",
    "angularjs": "angular",
    "vuejs": "vue",
    "vue.js": "vue",
    "nodejs": "node.js",
    "node": "node.js",
    "expressjs": "express",
    "sklearn": "scikit-learn",
    "tf": "tensorflow",
    "k8s": "kubernetes",
    "mongo": "mongodb",
    "mysql database": "mysql",
    "drf": "django",
    "django rest framework": "django",
    "fast api": "fastapi",
    "data analytics": "data analysis",
    "rest apis": "rest api",
    "restful api": "rest api",
    "web api": "rest api",
    "version control": "git",
}


def normalize(skill: str) -> str:
    cleaned = skill.strip().lower()
    return ALIASES.get(cleaned, cleaned)


def family_of(skill_lower: str) -> str | None:
    for family, members in LANGUAGE_FAMILIES.items():
        if skill_lower in members:
            return family
    return None
