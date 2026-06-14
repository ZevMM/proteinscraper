"""Derive normalized ingredient facets (dietary labels, allergens, sweeteners)
from raw ingredient text + any structured labels a retailer provides.

Coverage is best-effort and additive: explicit retailer data (e.g. Kroger
allergens / dietary declarations, Amazon "Diet Type"/"Allergen Information") is
authoritative; otherwise facets are inferred by scanning the ingredient list.
"""

from __future__ import annotations

import re

from .models import IngredientFactsRecord

# canonical label -> phrases that imply it (matched in lowercased text)
DIETARY_LABELS: dict[str, list[str]] = {
    "vegan": ["vegan"],
    "vegetarian": ["vegetarian"],
    "gluten_free": ["gluten free", "gluten-free", "certified gluten", "no gluten"],
    "kosher": ["kosher"],
    "halal": ["halal"],
    "organic": ["organic"],
    "non_gmo": ["non-gmo", "non gmo", "no gmo", "gmo free", "gmo-free"],
    "keto": ["keto", "ketogenic"],
    "dairy_free": ["dairy free", "dairy-free", "no dairy"],
    "sugar_free": ["sugar free", "sugar-free", "no sugar added", "zero sugar"],
    "soy_free": ["soy free", "soy-free", "no soy"],
    "grass_fed": ["grass fed", "grass-fed"],
}

# canonical allergen -> ingredient keywords
ALLERGENS: dict[str, list[str]] = {
    "milk": ["milk", "whey", "casein", "caseinate", "lactose", "dairy"],
    "soy": ["soy", "soya", "soybean"],
    "gluten": ["gluten", "wheat", "barley", "rye", "malt"],
    "egg": ["egg", "albumen"],
    "tree_nuts": ["almond", "cashew", "walnut", "pecan", "hazelnut", "pistachio", "tree nut"],
    "peanut": ["peanut"],
    "fish": ["fish", "cod", "tuna"],
    "shellfish": ["shellfish", "shrimp", "crab", "lobster", "crustacean"],
    "sesame": ["sesame"],
}

# canonical sweetener -> keywords
SWEETENERS: dict[str, list[str]] = {
    "stevia": ["stevia", "rebaudioside", "reb a", "steviol", "reb-a"],
    "monk_fruit": ["monk fruit", "monkfruit", "luo han guo"],
    "erythritol": ["erythritol"],
    "xylitol": ["xylitol"],
    "allulose": ["allulose"],
    "sucralose": ["sucralose"],
    "aspartame": ["aspartame"],
    "acesulfame_k": ["acesulfame", "ace-k", "ace k", "acesulfame potassium"],
    "saccharin": ["saccharin"],
    "sugar": ["cane sugar", "organic sugar", "sucrose", "dextrose", "fructose"],
}

ARTIFICIAL_SWEETENERS = {"sucralose", "aspartame", "acesulfame_k", "saccharin"}


def _scan(text: str, vocab: dict[str, list[str]]) -> list[str]:
    return [canonical for canonical, kws in vocab.items() if any(kw in text for kw in kws)]


_INGREDIENTS_RE = re.compile(
    r"ingredients?\s*[:\-]?\s*(.+?)(?:\.\s|\n\n|allergen|contains:|directions|suggested use|$)",
    re.IGNORECASE | re.DOTALL,
)


def extract_ingredients_text(text: str | None) -> str | None:
    """Pull the ingredient list out of a description blob (best-effort)."""
    if not text:
        return None
    match = _INGREDIENTS_RE.search(text)
    if not match:
        return None
    candidate = re.sub(r"\s+", " ", match.group(1)).strip(" .,;")
    # Require it to look like a real list (commas) and not be runaway marketing copy.
    if "," not in candidate or len(candidate) > 1200:
        return None
    return candidate or None


def derive_facts(
    ingredients_text: str | None = None,
    *,
    labels: list[str] | None = None,
    allergens: list[str] | None = None,
    label_text: str | None = None,
) -> IngredientFactsRecord | None:
    """Build an IngredientFactsRecord.

    ingredients_text: raw ingredient list (display + sweetener/allergen scan).
    labels: explicit dietary/cert labels from the retailer (free strings).
    allergens: explicit allergens from the retailer (free strings).
    label_text: extra text (claims/description) scanned for dietary labels.
    """
    ingredient_blob = (ingredients_text or "").lower()
    label_blob = " ".join(
        [label_text or "", " ".join(labels or [])]
    ).lower()

    dietary = set(_scan(f"{label_blob} {ingredient_blob}", DIETARY_LABELS))

    sweeteners = set(_scan(ingredient_blob, SWEETENERS))

    if allergens:
        allergen_set = set(_scan(" ".join(allergens).lower(), ALLERGENS))
    else:
        allergen_set = set(_scan(ingredient_blob, ALLERGENS))

    record = IngredientFactsRecord(
        ingredients_text=ingredients_text or None,
        dietary_labels=sorted(dietary),
        allergens=sorted(allergen_set),
        sweeteners=sorted(sweeteners),
    )
    return None if record.is_empty() else record
