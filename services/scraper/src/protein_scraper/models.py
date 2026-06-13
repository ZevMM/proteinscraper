"""Domain models for extracted records (pre-database)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ExtractionMethod(StrEnum):
    """Mirrors the Prisma ExtractionMethod enum."""

    shopify_json = "shopify_json"
    json_ld = "json_ld"
    html_parse = "html_parse"
    llm = "llm"
    manual = "manual"
    open_food_facts = "open_food_facts"


class NutritionRecord(BaseModel):
    """Per-serving nutrition facts for a single variant."""

    serving_size_g: float | None = None
    servings_per_container: float | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    carb_g: float | None = None
    sugar_g: float | None = None
    calories_kcal: float | None = None
    confidence: float = 0.0
    extraction_method: ExtractionMethod = ExtractionMethod.shopify_json

    def is_complete(self) -> bool:
        """True when the fields needed for the headline metrics exist.

        The core metric (protein per dollar / per container) needs protein per
        serving and servings per container; serving_size_g is only required for
        secondary metrics like protein-by-weight, so it's optional here.
        """
        return self.protein_g is not None and self.servings_per_container is not None


class VariantRecord(BaseModel):
    """A purchasable (flavor, size) variant with its current price."""

    source_variant_id: str
    flavor: str | None = None
    size_g: float | None = None
    size_label: str | None = None
    price_cents: int
    currency: str = "USD"
    in_stock: bool = True
    upc: str | None = None
    compare_at_price_cents: int | None = None
    nutrition: NutritionRecord | None = None


class ProductRecord(BaseModel):
    """A normalized product extracted from a single source listing."""

    source_sku: str
    url: str
    title: str
    brand_name: str
    product_name: str
    category: str | None = None
    raw_payload: dict[str, Any] | None = None
    variants: list[VariantRecord] = Field(default_factory=list)
