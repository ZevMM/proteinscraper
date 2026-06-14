"""Walmart connector via the official Walmart IO Affiliate API.

Sanctioned, ToS-clean access to Walmart's huge multi-brand catalog. Each request
is signed with the registered RSA key (see ``walmart_auth``). The API returns
price + brand + UPC but no nutrition facts, so nutrition is filled afterward by
the Open Food Facts enrichment pass keyed on the UPC.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import quote

from ..categorize import classify_category
from ..config import get_settings
from ..models import ProductRecord, VariantRecord
from ..units import is_multipack, parse_container_size_grams, to_cents
from ..walmart_auth import build_auth_headers
from .base import Connector

logger = logging.getLogger(__name__)

BASE_URL = "https://developer.api.walmart.com/api-proxy/service/affil/product/v2"
_PAGE_SIZE = 25
_DEFAULT_QUERIES = [
    "whey protein powder",
    "whey protein isolate",
    "plant protein powder",
    "vegan protein powder",
    "casein protein powder",
    "mass gainer protein powder",
    "grass fed whey protein",
    "egg white protein powder",
    "collagen protein powder",
    "protein powder unflavored",
]
_EXCLUDE = [
    "bar", "ready to drink", "rtd", "shake", "drink", "snack", "cookie",
    "capsule", "tablet", "clif", "water", "coffee creamer",
]


class WalmartConnector(Connector):
    source_type = "walmart"

    @property
    def _max_pages(self) -> int:
        return int(self.config.get("max_pages", 4))

    @property
    def _queries(self) -> list[str]:
        return list(self.config.get("queries", _DEFAULT_QUERIES))

    def _auth_headers(self) -> dict[str, str]:
        settings = get_settings()
        return build_auth_headers(
            settings.walmart_consumer_id,
            settings.walmart_private_key_pem,
            settings.walmart_key_version,
        )

    async def discover(self) -> list[dict[str, Any]]:
        settings = get_settings()
        if not settings.walmart_enabled:
            logger.warning("Walmart credentials not set; skipping walmart source")
            return []

        publisher_id = settings.walmart_publisher_id
        items: list[dict[str, Any]] = []
        seen: set[str] = set()

        for query in self._queries:
            for page in range(self._max_pages):
                start = 1 + page * _PAGE_SIZE
                url = f"{BASE_URL}/search?query={quote(query)}&numItems={_PAGE_SIZE}&start={start}"
                if publisher_id:
                    url += f"&publisherId={quote(publisher_id)}"
                raw = await self.fetcher.get_text(url, headers=self._auth_headers())
                batch = json.loads(raw).get("items", [])
                if not batch:
                    break
                for item in batch:
                    item_id = str(item.get("itemId"))
                    if item_id not in seen and self._is_protein_powder(item):
                        seen.add(item_id)
                        items.append(item)
        return items

    @staticmethod
    def _is_protein_powder(item: dict[str, Any]) -> bool:
        name = str(item.get("name", ""))
        if is_multipack(name):
            return False
        text = f"{name} {item.get('categoryPath', '')}".lower()
        if "protein" not in text:
            return False
        return not any(word in text for word in _EXCLUDE)

    async def _lookup(self, item_id: str) -> dict[str, Any] | None:
        """Fetch fresh item data via Product Lookup. The Search API's price is
        often stale (and may be a marketplace offer), but the item lookup returns
        the current buy-box price."""
        publisher_id = get_settings().walmart_publisher_id
        url = f"{BASE_URL}/items/{item_id}"
        if publisher_id:
            url += f"?publisherId={quote(publisher_id)}"
        try:
            raw = await self.fetcher.get_text(url, headers=self._auth_headers())
        except Exception as exc:
            logger.warning("walmart item lookup failed for %s: %s", item_id, exc)
            return None
        data = json.loads(raw)
        items = data.get("items")
        if isinstance(items, list):
            return items[0] if items else None
        return data if data.get("itemId") else None

    async def extract(self, ref: dict[str, Any]) -> ProductRecord | None:
        item_id = str(ref.get("itemId"))
        if not item_id:
            return None
        # Re-fetch the item for an accurate, current price (Search prices lag).
        item = await self._lookup(item_id)
        if item is None:
            return None
        return self.build_record(item)

    def build_record(self, item: dict[str, Any]) -> ProductRecord | None:
        """Pure (no I/O) assembly of a record from a Walmart item payload."""
        item_id = str(item.get("itemId"))
        price_cents = to_cents(item.get("salePrice"))
        if not item_id or not price_cents:
            return None

        name = str(item.get("name") or item_id)
        brand = str(item.get("brandName") or "Unknown")
        upc = item.get("upc")
        msrp = to_cents(item.get("msrp"))
        # productTrackingUrl is an affiliate link with a literal "|PUBID|"
        # placeholder that only works once an Impact publisher id is set. Use the
        # direct product URL for working links; use tracking only if configured.
        publisher_id = get_settings().walmart_publisher_id
        tracking = item.get("productTrackingUrl")
        if publisher_id and tracking:
            url = tracking.replace("|PUBID|", publisher_id)
        else:
            url = f"https://www.walmart.com/ip/{item_id}"
        in_stock = bool(item.get("availableOnline", True)) and (
            str(item.get("stock", "Available")).lower() != "not available"
        )
        size_g = parse_container_size_grams(name)

        variant = VariantRecord(
            source_variant_id=item_id,
            flavor=None,
            size_g=size_g,
            size_label=None,
            price_cents=price_cents,
            currency="USD",
            in_stock=in_stock,
            upc=str(upc) if upc else None,
            compare_at_price_cents=msrp if msrp and msrp > price_cents else None,
            nutrition=None,  # filled by Open Food Facts enrichment via UPC
        )
        return ProductRecord(
            source_sku=item_id,
            url=str(url),
            title=name,
            brand_name=brand,
            product_name=name,
            category=classify_category(f"{name} {item.get('categoryPath', '')}"),
            raw_payload=item,
            variants=[variant],
        )
