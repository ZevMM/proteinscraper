"""Unit normalization helpers (weights, currency, text cleanup)."""

from __future__ import annotations

import re

LB_TO_G = 453.59237
OZ_TO_G = 28.349523125
KG_TO_G = 1000.0
G_TO_G = 1.0

# Order matters: match the more specific / longer units first.
_WEIGHT_UNITS: list[tuple[str, float]] = [
    ("kilograms", KG_TO_G),
    ("kilogram", KG_TO_G),
    ("kgs", KG_TO_G),
    ("kg", KG_TO_G),
    ("pounds", LB_TO_G),
    ("pound", LB_TO_G),
    ("lbs", LB_TO_G),
    ("lb", LB_TO_G),
    ("ounces", OZ_TO_G),
    ("ounce", OZ_TO_G),
    ("oz", OZ_TO_G),
    ("grams", G_TO_G),
    ("gram", G_TO_G),
    ("gr", G_TO_G),
    ("g", G_TO_G),
]

_WEIGHT_RE = re.compile(
    r"(?P<value>\d+(?:[.,]\d+)?)\s*(?P<unit>"
    + "|".join(re.escape(u) for u, _ in _WEIGHT_UNITS)
    + r")\b",
    re.IGNORECASE,
)


def parse_weight_to_grams(text: str | None) -> float | None:
    """Extract the first weight quantity from free text and return grams.

    Handles e.g. "5 lb", "2.27kg", "907 g", "32oz". Returns None if no weight
    token is found.
    """
    if not text:
        return None
    match = _WEIGHT_RE.search(text)
    if not match:
        return None
    raw_value = match.group("value").replace(",", ".")
    unit = match.group("unit").lower()
    factor = next((f for u, f in _WEIGHT_UNITS if u == unit), None)
    if factor is None:
        return None
    return round(float(raw_value) * factor, 3)


_SERVINGS_RE = re.compile(r"(\d+(?:\.\d+)?)\s*servings?\b", re.IGNORECASE)


def parse_servings(text: str | None) -> float | None:
    """Extract a 'N servings' count from free text."""
    if not text:
        return None
    match = _SERVINGS_RE.search(text)
    return float(match.group(1)) if match else None


def to_cents(amount: float | str | None) -> int | None:
    """Convert a dollar amount (float or string like '39.99') to integer cents."""
    if amount is None:
        return None
    if isinstance(amount, str):
        cleaned = re.sub(r"[^\d.]", "", amount)
        if not cleaned:
            return None
        amount = float(cleaned)
    return int(round(amount * 100))


def clean_flavor(text: str | None) -> str | None:
    """Normalize a flavor/option label."""
    if not text:
        return None
    cleaned = re.sub(r"\s+", " ", text).strip()
    # Treat Shopify's catch-all option as "no flavor".
    if cleaned.lower() in {"default title", "default", "n/a", ""}:
        return None
    return cleaned
