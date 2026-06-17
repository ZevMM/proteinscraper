"""Shopify connector.

Shopify storefronts expose a public ``/products.json`` feed with full product +
variant + price data and no API key — the cheapest, most reliable starting
point. Nutrition facts live in the product description, so those go through the
tiered extractor (HTML parse, then optional LLM fallback).
"""

from __future__ import annotations

import json
from typing import Any

from ..categorize import classify_category
from ..extract.nutrition import html_to_text, merge_nutrition, parse_nutrition_text
from ..ingredients import derive_facts, extract_ingredients_text
from ..markets import currency_for
from ..models import IngredientFactsRecord, NutritionRecord, ProductRecord, VariantRecord
from ..units import clean_flavor, parse_servings, parse_weight_to_grams, to_cents
from .base import Connector

_DEFAULT_INCLUDE = ["protein"]
_DEFAULT_EXCLUDE = [
    "bar", "rtd", "ready to drink", "shaker", "bottle", "t-shirt", "shirt",
    "hoodie", "gift card", "capsule", "tablet", "pill", "sample", "bundle",
]
_FLAVOR_OPTIONS = {"flavor", "flavour", "taste"}
_SIZE_OPTIONS = {"size", "weight", "servings", "container", "count", "bag size", "amount"}


class ShopifyConnector(Connector):
    source_type = "shopify"

    @property
    def _max_pages(self) -> int:
        return int(self.config.get("max_pages", 5))

    @property
    def _include(self) -> list[str]:
        return [k.lower() for k in self.config.get("include_keywords", _DEFAULT_INCLUDE)]

    @property
    def _exclude(self) -> list[str]:
        return [k.lower() for k in self.config.get("exclude_keywords", _DEFAULT_EXCLUDE)]

    async def discover(self) -> list[dict[str, Any]]:
        products: list[dict[str, Any]] = []
        for page in range(1, self._max_pages + 1):
            url = f"{self.base_url}/products.json?limit=250&page={page}"
            raw = await self.fetcher.get_text(url)
            batch = json.loads(raw).get("products", [])
            if not batch:
                break
            products.extend(batch)
        return [p for p in products if self._is_protein_powder(p)]

    def _is_protein_powder(self, product: dict[str, Any]) -> bool:
        # Match on title + product_type only: tags are noisy (collections,
        # cross-sells) and cause false positives like creatine/hydration.
        haystack = self._text(product, include_tags=False)
        if not any(kw in haystack for kw in self._include):
            return False
        return not any(kw in haystack for kw in self._exclude)

    @staticmethod
    def _text(product: dict[str, Any], *, include_tags: bool) -> str:
        parts = [product.get("title", ""), product.get("product_type", "")]
        if include_tags:
            tags = product.get("tags", [])
            parts.append(" ".join(tags) if isinstance(tags, list) else str(tags))
        return " ".join(parts).lower()

    def _classify(self, product: dict[str, Any]) -> str | None:
        # Classification can use tags for extra signal.
        return classify_category(self._text(product, include_tags=True))

    def _option_indices(self, product: dict[str, Any]) -> tuple[int | None, int | None]:
        flavor_idx: int | None = None
        size_idx: int | None = None
        for option in product.get("options", []):
            name = str(option.get("name", "")).lower()
            position = int(option.get("position", 0))
            if name in _FLAVOR_OPTIONS and flavor_idx is None:
                flavor_idx = position
            elif name in _SIZE_OPTIONS and size_idx is None:
                size_idx = position
        return flavor_idx, size_idx

    def _extract_nutrition(self, product: dict[str, Any]) -> NutritionRecord | None:
        text = html_to_text(product.get("body_html", ""))
        if not text:
            return None
        record = parse_nutrition_text(text)
        if not record.is_complete() and self.llm is not None:
            llm_record = self.llm.extract_nutrition(text, title=product.get("title"))
            if llm_record is not None:
                record = merge_nutrition(record, llm_record)
        return record

    @staticmethod
    def _variant_nutrition(
        base: NutritionRecord | None, product: dict[str, Any], variant: dict[str, Any],
        size_g: float | None,
    ) -> NutritionRecord | None:
        """Per-variant nutrition: copy the product's facts and fill in this
        variant's servings-per-container (which depends on its size)."""
        if base is None:
            return None
        n = base.model_copy()
        if n.servings_per_container is None:
            n.servings_per_container = (
                parse_servings(variant.get("title"))
                or parse_servings(variant.get("option1"))
                or parse_servings(variant.get("option2"))
                or parse_servings(product.get("title"))
                or (
                    round(size_g / n.serving_size_g, 1)
                    if size_g and n.serving_size_g
                    else None
                )
            )
        return n

    @staticmethod
    def _facts(product: dict[str, Any]) -> IngredientFactsRecord | None:
        """Ingredients from the description; dietary labels from tags/product_type."""
        ingredients = extract_ingredients_text(html_to_text(product.get("body_html", "")))
        tags = product.get("tags", [])
        tags_str = " ".join(tags) if isinstance(tags, list) else str(tags)
        label_text = f"{tags_str} {product.get('product_type', '')}"
        return derive_facts(ingredients_text=ingredients, label_text=label_text)

    async def extract(self, ref: dict[str, Any]) -> ProductRecord | None:
        product = ref
        handle = product.get("handle")
        if not handle:
            return None

        flavor_idx, size_idx = self._option_indices(product)
        nutrition = self._extract_nutrition(product)
        facts = self._facts(product)

        variants: list[VariantRecord] = []
        for variant in product.get("variants", []):
            price_cents = to_cents(variant.get("price"))
            if not price_cents:
                continue
            flavor = clean_flavor(variant.get(f"option{flavor_idx}")) if flavor_idx else None
            size_label = variant.get(f"option{size_idx}") if size_idx else None
            size_g = (
                parse_weight_to_grams(size_label)
                or parse_weight_to_grams(variant.get("title"))
                or (float(variant["grams"]) if variant.get("grams") else None)
            )
            compare_at = to_cents(variant.get("compare_at_price"))
            # Only a genuine markdown (compare_at above the live price).
            on_sale = compare_at if compare_at and compare_at > price_cents else None
            variants.append(
                VariantRecord(
                    source_variant_id=str(variant["id"]),
                    flavor=flavor,
                    size_g=size_g,
                    size_label=size_label,
                    price_cents=price_cents,
                    currency=currency_for(self.market),
                    in_stock=bool(variant.get("available", True)),
                    compare_at_price_cents=on_sale,
                    nutrition=self._variant_nutrition(nutrition, product, variant, size_g),
                    facts=facts.model_copy() if facts else None,
                )
            )

        if not variants:
            return None

        return ProductRecord(
            source_sku=str(handle),
            url=f"{self.base_url}/products/{handle}",
            title=product.get("title", str(handle)),
            brand_name=product.get("vendor") or self.source.get("name", "Unknown"),
            product_name=product.get("title", str(handle)),
            category=self._classify(product),
            raw_payload=product,
            variants=variants,
        )
