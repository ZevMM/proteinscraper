"""Kroger connector via the official Kroger Products API.

Sanctioned, ToS-clean, free access to Kroger's grocery + supplement catalog with
authentic per-store prices. Auth is OAuth2 client-credentials (scope
``product.compact``). Price is only returned when a ``filter.locationId`` is
supplied, so the connector first resolves a store via the Locations API (from a
configured zip code) and then queries products for that store.

The Products API returns ``items[].price.regular`` / ``items[].price.promo`` and a
13-digit ``productId`` (a base UPC), which both enables cross-source dedup by
barcode and lets the Open Food Facts pass fill in nutrition. No nutrition is
returned by the API itself.
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any
from urllib.parse import quote

from ..categorize import classify_category
from ..config import get_settings
from ..models import ProductRecord, VariantRecord
from ..units import is_multipack, parse_container_size_grams, to_cents
from .base import Connector

logger = logging.getLogger(__name__)

BASE_URL = "https://api.kroger.com/v1"
TOKEN_URL = f"{BASE_URL}/connect/oauth2/token"
_PAGE_SIZE = 50  # Products API caps filter.limit at 50.
_DEFAULT_QUERIES = [
    "whey protein powder",
    "plant protein powder",
    "casein protein powder",
    "protein isolate powder",
    "collagen protein powder",
]
_DEFAULT_ZIP = "45202"  # Cincinnati (Kroger HQ) — a reliably-stocked store.
_EXCLUDE = [
    "bar", "ready to drink", "rtd", "shake", "drink", "snack", "cookie",
    "capsule", "tablet", "clif", "water", "creamer",
]


class KrogerConnector(Connector):
    source_type = "kroger"

    @property
    def _max_pages(self) -> int:
        return int(self.config.get("max_pages", 2))

    @property
    def _queries(self) -> list[str]:
        return list(self.config.get("queries", _DEFAULT_QUERIES))

    @property
    def _zip(self) -> str:
        return str(self.config.get("zip_code", _DEFAULT_ZIP))

    async def _token(self) -> str:
        """Mint an OAuth client-credentials access token (scope product.compact)."""
        settings = get_settings()
        creds = f"{settings.kroger_client_id}:{settings.kroger_client_secret}"
        basic = base64.b64encode(creds.encode()).decode()
        headers = {
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        raw = await self.fetcher.post_text(
            TOKEN_URL,
            data="grant_type=client_credentials&scope=product.compact",
            headers=headers,
        )
        return str(json.loads(raw)["access_token"])

    async def _location_id(self, token: str) -> str | None:
        """Resolve a store locationId from the configured zip (price requires it)."""
        url = f"{BASE_URL}/locations?filter.zipCode.near={quote(self._zip)}&filter.limit=1"
        raw = await self.fetcher.get_text(url, headers={"Authorization": f"Bearer {token}"})
        data = json.loads(raw).get("data", [])
        return str(data[0]["locationId"]) if data else None

    async def discover(self) -> list[dict[str, Any]]:
        settings = get_settings()
        if not settings.kroger_enabled:
            logger.warning("Kroger credentials not set; skipping kroger source")
            return []

        token = await self._token()
        location_id = await self._location_id(token)
        if not location_id:
            logger.warning("Kroger: no store found near zip %s; skipping", self._zip)
            return []
        self._auth = {"Authorization": f"Bearer {token}"}

        items: list[dict[str, Any]] = []
        seen: set[str] = set()
        for query in self._queries:
            for page in range(self._max_pages):
                start = 1 + page * _PAGE_SIZE
                url = (
                    f"{BASE_URL}/products?filter.term={quote(query)}"
                    f"&filter.locationId={location_id}"
                    f"&filter.limit={_PAGE_SIZE}&filter.start={start}"
                )
                raw = await self.fetcher.get_text(url, headers=self._auth)
                batch = json.loads(raw).get("data", [])
                if not batch:
                    break
                for item in batch:
                    product_id = str(item.get("productId", ""))
                    if product_id and product_id not in seen and self._is_protein_powder(item):
                        seen.add(product_id)
                        items.append(item)
        return items

    @staticmethod
    def _is_protein_powder(item: dict[str, Any]) -> bool:
        text = " ".join(
            str(item.get(k, ""))
            for k in ("description", "brand")
        )
        categories = item.get("categories")
        if isinstance(categories, list):
            text += " " + " ".join(str(c) for c in categories)
        text = text.lower()
        if is_multipack(text):
            return False
        if "protein" not in text:
            return False
        return not any(word in text for word in _EXCLUDE)

    async def extract(self, ref: dict[str, Any]) -> ProductRecord | None:
        return self.build_record(ref)

    def build_record(self, item: dict[str, Any]) -> ProductRecord | None:
        """Pure (no I/O) assembly of a record from a Kroger product payload."""
        product_id = str(item.get("productId", ""))
        name = str(item.get("description") or product_id)
        if not product_id or not name:
            return None

        # A Kroger product carries one or more "items" (sizes); take the first
        # priced one. price.regular / price.promo come from the store location.
        size_items = item.get("items") or []
        priced = next(
            (
                i for i in size_items
                if isinstance(i, dict) and (i.get("price") or {}).get("regular")
            ),
            size_items[0] if size_items else None,
        )
        if not isinstance(priced, dict):
            return None
        price = priced.get("price") or {}
        regular = to_cents(price.get("regular"))
        promo = to_cents(price.get("promo"))
        if not regular and not promo:
            return None
        # promo is the current sale price when present and below regular.
        price_cents: int | None
        if promo and (not regular or promo < regular):
            price_cents = promo
            compare_at = regular if regular and regular > promo else None
        else:
            price_cents = regular
            compare_at = None
        if not price_cents:
            return None

        brand = str(item.get("brand") or "Unknown").strip() or "Unknown"
        # Kroger's productId is a 13-digit base UPC; normalize to the 12-digit UPC-A
        # when it is a leading-zero-padded GTIN-13 so it matches other retailers.
        upc = product_id if product_id.isdigit() and len(product_id) >= 12 else None

        size_label = str(priced.get("size") or "")
        size_g = parse_container_size_grams(f"{name} {size_label}")
        inventory = str(priced.get("inventory", {}).get("stockLevel", "")).upper()
        in_stock = inventory not in ("TEMPORARILY_OUT_OF_STOCK", "OUT_OF_STOCK")

        variant = VariantRecord(
            source_variant_id=product_id,
            flavor=None,
            size_g=size_g,
            size_label=size_label or None,
            price_cents=price_cents,
            currency="USD",
            in_stock=in_stock,
            upc=upc,
            compare_at_price_cents=compare_at,
            nutrition=None,  # filled by Open Food Facts enrichment via UPC
        )
        url = f"https://www.kroger.com/p/x/{product_id}"
        categories = item.get("categories")
        cat_text = " ".join(categories) if isinstance(categories, list) else ""
        return ProductRecord(
            source_sku=product_id,
            url=url,
            title=name,
            brand_name=brand,
            product_name=name,
            category=classify_category(f"{name} {cat_text}"),
            raw_payload=item,
            variants=[variant],
        )
