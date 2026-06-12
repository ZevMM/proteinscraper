"""Classify a protein product into a coarse category from its text."""

from __future__ import annotations

# Most specific first.
_CATEGORY_KEYWORDS: list[tuple[str, str]] = [
    ("collagen", "collagen"),
    ("casein", "casein"),
    ("vegan", "plant"),
    ("plant", "plant"),
    ("pea protein", "plant"),
    ("soy", "plant"),
    ("isolate", "isolate"),
    ("concentrate", "concentrate"),
    ("whey", "whey"),
    ("blend", "blend"),
]


def classify_category(text: str) -> str | None:
    haystack = text.lower()
    for keyword, category in _CATEGORY_KEYWORDS:
        if keyword in haystack:
            return category
    return None
