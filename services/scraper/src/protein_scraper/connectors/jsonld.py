"""JSON-LD connector for retailers that embed schema.org Product data.

Discovery is config-driven: an explicit ``product_urls`` list and/or a
``sitemap`` URL (optionally filtered by ``url_pattern``). Each product page is
fetched once, its schema.org Product/Offer parsed for price + brand, and
nutrition pulled from the description text (HTML parse, then LLM fallback).
"""

from __future__ import annotations

import re
from typing import Any

from ..categorize import classify_category
from ..extract.jsonld import brand_name, extract_jsonld_products, offer_price, pick_offer
from ..extract.nutrition import html_to_text, merge_nutrition, parse_nutrition_text
from ..models import NutritionRecord, ProductRecord, VariantRecord
from ..units import parse_servings, parse_weight_to_grams, to_cents
from .base import Connector


class JsonLdConnector(Connector):
    source_type = "jsonld"

    @property
    def _max_urls(self) -> int:
        return int(self.config.get("max_urls", 200))

    async def discover(self) -> list[str]:
        urls: list[str] = list(self.config.get("product_urls", []))
        sitemap = self.config.get("sitemap")
        if sitemap:
            urls += await self._sitemap_urls(sitemap, self.config.get("url_pattern"))
        # De-dupe, preserve order, cap.
        return list(dict.fromkeys(urls))[: self._max_urls]

    async def _sitemap_urls(self, sitemap_url: str, pattern: str | None) -> list[str]:
        xml = await self.fetcher.get_text(sitemap_url)
        locs = re.findall(r"<loc>\s*(.*?)\s*</loc>", xml, re.IGNORECASE | re.DOTALL)
        if pattern:
            rx = re.compile(pattern)
            locs = [u for u in locs if rx.search(u)]
        return locs

    async def extract(self, ref: str) -> ProductRecord | None:
        html = await self.fetcher.get_text(ref)
        return self.build_record(ref, html)

    def build_record(self, url: str, html: str) -> ProductRecord | None:
        """Pure (no I/O) assembly of a record from a product page's HTML."""
        node = self._pick_product(extract_jsonld_products(html))
        if node is None:
            return None
        offer = pick_offer(node)
        if offer is None:
            return None
        price_cents = to_cents(offer_price(offer))
        if not price_cents:
            return None

        name = str(node.get("name") or url)
        availability = str(offer.get("availability", "")).lower()
        in_stock = "instock" in availability or availability == ""
        sku = str(node.get("sku") or node.get("productID") or url)
        size_g = parse_weight_to_grams(name)

        nutrition = self._nutrition(node, html, name, size_g)
        variant = VariantRecord(
            source_variant_id=sku,
            flavor=None,
            size_g=size_g,
            size_label=None,
            price_cents=price_cents,
            currency=str(offer.get("priceCurrency", "USD")),
            in_stock=in_stock,
            nutrition=nutrition,
        )
        return ProductRecord(
            source_sku=sku,
            url=url,
            title=name,
            brand_name=brand_name(node) or self.source.get("name", "Unknown"),
            product_name=name,
            category=classify_category(f"{name} {node.get('category', '')}"),
            raw_payload={"jsonld": node},
            variants=[variant],
        )

    @staticmethod
    def _pick_product(products: list[dict[str, Any]]) -> dict[str, Any] | None:
        # Prefer a product that actually carries an offer.
        for node in products:
            if node.get("offers"):
                return node
        return products[0] if products else None

    def _nutrition(
        self, node: dict[str, Any], html: str, title: str, size_g: float | None
    ) -> NutritionRecord | None:
        # Prefer the product description (less noisy than the whole page).
        description = node.get("description")
        text = html_to_text(description) if description else html_to_text(html)
        record = parse_nutrition_text(text)
        if record.servings_per_container is None:
            record.servings_per_container = parse_servings(title) or (
                round(size_g / record.serving_size_g, 1)
                if size_g and record.serving_size_g
                else None
            )
        if not record.is_complete() and self.llm is not None:
            llm_record = self.llm.extract_nutrition(text, title=title)
            if llm_record is not None:
                record = merge_nutrition(record, llm_record)
        # Nothing useful found.
        if record.protein_g is None and record.serving_size_g is None:
            return None
        return record
