"""Open Food Facts nutrition enrichment by UPC.

OFF is a free, ToS-clean database with nutrition + barcodes but no prices, so it
is an enrichment source (not a listing source): for variants that already have a
UPC but no nutrition, look the barcode up and fill in the facts.
"""

from __future__ import annotations

import json
from typing import Any

from ..http import Fetcher
from ..ingredients import derive_facts
from ..models import ExtractionMethod, IngredientFactsRecord, NutritionRecord
from ..units import parse_weight_to_grams

# Map Open Food Facts tag leaves to our canonical facet vocabulary.
_OFF_ALLERGEN = {
    "milk": "milk", "soybeans": "soy", "soy": "soy", "gluten": "gluten",
    "eggs": "egg", "egg": "egg", "nuts": "tree_nuts", "tree-nuts": "tree_nuts",
    "peanuts": "peanut", "fish": "fish", "crustaceans": "shellfish",
    "molluscs": "shellfish", "sesame-seeds": "sesame", "sesame": "sesame",
}
_OFF_LABEL = {
    "vegan": "vegan", "vegetarian": "vegetarian", "gluten-free": "gluten_free",
    "no-gluten": "gluten_free", "organic": "organic", "eu-organic": "organic",
    "usda-organic": "organic", "kosher": "kosher", "halal": "halal",
    "non-gmo": "non_gmo", "no-gmos": "non_gmo", "keto": "keto", "dairy-free": "dairy_free",
}


def parse_off_facts(product: dict[str, Any]) -> IngredientFactsRecord | None:
    """Map an OFF product to ingredient facts (ingredients + allergens + labels)."""
    ingredients = product.get("ingredients_text") or product.get("ingredients_text_en")
    allergens = {
        _OFF_ALLERGEN[leaf]
        for t in product.get("allergens_tags", [])
        if (leaf := str(t).split(":")[-1]) in _OFF_ALLERGEN
    }
    labels = {
        _OFF_LABEL[leaf]
        for t in product.get("labels_tags", [])
        if (leaf := str(t).split(":")[-1]) in _OFF_LABEL
    }
    # derive sweeteners (and anything else) from the ingredient text, then merge
    # in OFF's structured allergens/labels.
    record = derive_facts(ingredients_text=ingredients) or IngredientFactsRecord()
    record.allergens = sorted(set(record.allergens) | allergens)
    record.dietary_labels = sorted(set(record.dietary_labels) | labels)
    return None if record.is_empty() else record

PRODUCT_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_off_product(product: dict[str, Any], size_g: float | None) -> NutritionRecord | None:
    """Map an OFF product payload to a per-serving NutritionRecord.

    Prefers per-serving nutriment values; otherwise scales per-100g values by the
    serving size. ``size_g`` (our known container weight) is used to derive
    servings-per-container when OFF doesn't state it.
    """
    nutriments: dict[str, Any] = product.get("nutriments", {})

    serving_g = _to_float(product.get("serving_quantity")) or parse_weight_to_grams(
        product.get("serving_size")
    )

    def per_serving(serving_key: str, per100_key: str) -> float | None:
        direct = _to_float(nutriments.get(serving_key))
        if direct is not None:
            return round(direct, 2)
        base = _to_float(nutriments.get(per100_key))
        if base is not None and serving_g:
            return round(base * serving_g / 100.0, 2)
        return None

    protein = per_serving("proteins_serving", "proteins_100g")
    fat = per_serving("fat_serving", "fat_100g")
    carb = per_serving("carbohydrates_serving", "carbohydrates_100g")
    sugar = per_serving("sugars_serving", "sugars_100g")
    calories = per_serving("energy-kcal_serving", "energy-kcal_100g")

    servings = None
    product_qty = _to_float(product.get("product_quantity"))
    if product_qty and serving_g:
        servings = round(product_qty / serving_g, 1)
    elif size_g and size_g >= 300 and serving_g:
        # Only trust our known container size if it's plausibly a container
        # (avoids deriving servings from a mis-parsed tiny size).
        servings = round(size_g / serving_g, 1)

    record = NutritionRecord(
        serving_size_g=serving_g,
        servings_per_container=servings,
        protein_g=protein,
        fat_g=fat,
        carb_g=carb,
        sugar_g=sugar,
        calories_kcal=calories,
        extraction_method=ExtractionMethod.open_food_facts,
    )
    if record.protein_g is None and record.serving_size_g is None:
        return None
    return record


async def fetch_off_product(fetcher: Fetcher, upc: str) -> dict[str, Any] | None:
    """Fetch one product from OFF by barcode; None if not found."""
    raw = await fetcher.get_text(PRODUCT_URL.format(barcode=upc))
    payload = json.loads(raw)
    if payload.get("status") == 1:
        product: dict[str, Any] = payload.get("product", {})
        return product
    return None
