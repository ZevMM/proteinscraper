"""Deterministic nutrition extraction from product description HTML / text.

This is extraction tier 2: cheap regex parsing of supplement-facts text. Tier 1
is structured feed data (handled per-connector); tier 3 is the LLM fallback in
``llm.py``, used only for fields this parser leaves empty.
"""

from __future__ import annotations

import re

from selectolax.parser import HTMLParser

from ..models import ExtractionMethod, NutritionRecord
from ..units import parse_servings, parse_weight_to_grams

_NUM = r"(\d+(?:\.\d+)?)"


def html_to_text(html: str) -> str:
    """Strip tags and collapse whitespace, keeping label/value adjacency."""
    if not html:
        return ""
    tree = HTMLParser(html)
    text = tree.body.text(separator=" ") if tree.body else tree.text(separator=" ")
    return re.sub(r"\s+", " ", text).strip()


def _search_grams(label: str, text: str) -> float | None:
    match = re.search(rf"{label}\s*[:\-]?\s*{_NUM}\s*g\b", text, re.IGNORECASE)
    return float(match.group(1)) if match else None


def _search_number(label: str, text: str) -> float | None:
    match = re.search(rf"{label}\s*[:\-]?\s*(?:about\s*)?{_NUM}", text, re.IGNORECASE)
    return float(match.group(1)) if match else None


# Marketing prose like "30g of pure protein per serving" — number precedes the
# label, with optional qualifiers in between.
_PROSE_PROTEIN_RE = re.compile(
    rf"{_NUM}\s*g(?:rams)?\s+(?:of\s+)?(?:[a-z]+\s+){{0,2}}protein",
    re.IGNORECASE,
)


def _search_protein(text: str) -> float | None:
    forward = _search_grams(r"protein", text)
    if forward is not None:
        return forward
    match = _PROSE_PROTEIN_RE.search(text)
    return float(match.group(1)) if match else None


def parse_nutrition_text(text: str) -> NutritionRecord:
    """Parse a supplement-facts blob. Missing fields stay None."""
    record = NutritionRecord(extraction_method=ExtractionMethod.html_parse)

    serving_match = re.search(
        r"serving size\s*[:\-]?\s*([^\n.;|]+)", text, re.IGNORECASE
    )
    if serving_match:
        record.serving_size_g = parse_weight_to_grams(serving_match.group(1))

    record.servings_per_container = _search_number(
        r"servings?\s*per\s*container", text
    ) or parse_servings(text)
    record.calories_kcal = _search_number(r"calories", text)
    record.protein_g = _search_protein(text)
    record.fat_g = _search_grams(r"(?:total\s+)?fat", text)
    record.carb_g = _search_grams(
        r"(?:total\s+)?(?:carbohydrates?|carbs?)", text
    )
    record.sugar_g = _search_grams(r"(?:total\s+|added\s+)?sugars?", text)

    return record


def parse_nutrition_html(html: str) -> NutritionRecord:
    return parse_nutrition_text(html_to_text(html))
