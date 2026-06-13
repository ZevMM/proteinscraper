"""Amazon connector via the RapidAPI "Real-Time Amazon Data" provider.

A third-party service (not Amazon PA-API) that returns structured Amazon product
data, so no Associates approval is needed. Discovery uses the search endpoint;
product-details is fetched per ASIN to recover brand + UPC (the UPC is what lets
Amazon listings merge with Walmart's by barcode). Amazon returns no nutrition, so
that is filled afterward by the Open Food Facts enrichment pass via UPC.

Note: data here is scraped by the provider, i.e. outside Amazon's sanctioned API.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any
from urllib.parse import quote

from ..categorize import classify_category
from ..config import get_settings
from ..models import ProductRecord, VariantRecord
from ..units import parse_weight_to_grams, to_cents
from .base import Connector

logger = logging.getLogger(__name__)

HOST = "real-time-amazon-data.p.rapidapi.com"
BASE_URL = f"https://{HOST}"
_DEFAULT_QUERIES = [
    "whey protein powder",
    "plant protein powder",
    "casein protein powder",
    "protein isolate powder",
]
_EXCLUDE = [
    "bar", "ready to drink", "rtd", "shake", "drink", "snack", "cookie",
    "capsule", "tablet", "clif", "water", "creamer", "sample",
]
# Keys (case-insensitive) under product_information/product_details that hold a barcode.
_UPC_KEYS = ("upc", "ean", "gtin")
_BARCODE_RE = re.compile(r"\b(\d{12,14})\b")


class AmazonConnector(Connector):
    source_type = "amazon"

    @property
    def _max_pages(self) -> int:
        return int(self.config.get("max_pages", 3))

    @property
    def _queries(self) -> list[str]:
        return list(self.config.get("queries", _DEFAULT_QUERIES))

    @property
    def _country(self) -> str:
        return str(self.config.get("country", "US"))

    @property
    def _fetch_details(self) -> bool:
        # Product-details calls recover brand + UPC but double the request count.
        return bool(self.config.get("fetch_details", True))

    def _headers(self) -> dict[str, str]:
        return {
            "X-RapidAPI-Key": get_settings().rapidapi_key,
            "X-RapidAPI-Host": HOST,
        }

    async def discover(self) -> list[dict[str, Any]]:
        if not get_settings().amazon_enabled:
            logger.warning("RAPIDAPI_KEY not set; skipping amazon source")
            return []

        items: list[dict[str, Any]] = []
        seen: set[str] = set()
        for query in self._queries:
            for page in range(1, self._max_pages + 1):
                url = (
                    f"{BASE_URL}/search?query={quote(query)}"
                    f"&page={page}&country={self._country}"
                )
                raw = await self.fetcher.get_text(url, headers=self._headers())
                products = json.loads(raw).get("data", {}).get("products", [])
                if not products:
                    break
                for product in products:
                    asin = str(product.get("asin", ""))
                    if asin and asin not in seen and self._is_protein_powder(product):
                        seen.add(asin)
                        items.append(product)
        return items

    @staticmethod
    def _is_protein_powder(product: dict[str, Any]) -> bool:
        title = str(product.get("product_title", "")).lower()
        if "protein" not in title:
            return False
        return not any(word in title for word in _EXCLUDE)

    async def extract(self, ref: dict[str, Any]) -> ProductRecord | None:
        asin = str(ref.get("asin", ""))
        if not asin:
            return None

        details: dict[str, Any] = {}
        if self._fetch_details:
            url = f"{BASE_URL}/product-details?asin={asin}&country={self._country}"
            try:
                details = json.loads(
                    await self.fetcher.get_text(url, headers=self._headers())
                ).get("data", {})
            except Exception as exc:  # details are best-effort
                logger.warning("amazon product-details failed for %s: %s", asin, exc)

        title = str(details.get("product_title") or ref.get("product_title") or asin)
        price_cents = to_cents(ref.get("product_price") or details.get("product_price"))
        if not price_cents:
            return None

        info = details.get("product_information") or {}
        brand = self._brand(details, info) or "Unknown"
        upc = self._find_upc(details)
        original = to_cents(
            ref.get("product_original_price") or details.get("product_original_price")
        )
        size_g = parse_weight_to_grams(str(info.get("Item Weight", ""))) or parse_weight_to_grams(
            title
        )
        url = (
            details.get("product_url")
            or ref.get("product_url")
            or f"https://www.amazon.com/dp/{asin}"
        )
        availability = str(details.get("product_availability", "")).lower()
        in_stock = "unavailable" not in availability and "out of stock" not in availability

        variant = VariantRecord(
            source_variant_id=asin,
            flavor=None,
            size_g=size_g,
            size_label=None,
            price_cents=price_cents,
            currency="USD",
            in_stock=in_stock,
            upc=upc,
            compare_at_price_cents=original if original and original > price_cents else None,
            nutrition=None,  # filled by Open Food Facts enrichment via UPC
        )
        return ProductRecord(
            source_sku=asin,
            url=str(url),
            title=title,
            brand_name=brand,
            product_name=title,
            category=classify_category(title),
            raw_payload={"search": ref, "details": details or None},
            variants=[variant],
        )

    @staticmethod
    def _brand(details: dict[str, Any], info: dict[str, Any]) -> str | None:
        for key in ("Brand", "Manufacturer"):
            if info.get(key):
                return str(info[key]).strip()
        byline = str(details.get("product_byline", ""))
        match = re.search(r"(?:brand:|visit the)\s*(.+?)(?:\s+store)?$", byline, re.IGNORECASE)
        return match.group(1).strip() if match else None

    @staticmethod
    def _find_upc(details: dict[str, Any]) -> str | None:
        for container in (details.get("product_information"), details.get("product_details")):
            if not isinstance(container, dict):
                continue
            for key, value in container.items():
                if any(token in key.lower() for token in _UPC_KEYS):
                    match = _BARCODE_RE.search(str(value))
                    if match:
                        return match.group(1)
        return None
