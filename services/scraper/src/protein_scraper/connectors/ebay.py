"""eBay connector via the official Browse API (Buy APIs).

Sanctioned, ToS-clean access via an OAuth client-credentials *application* token
(no user consent). The Browse ``item_summary/search`` endpoint returns price +
title + condition + seller for the US marketplace.

eBay is a marketplace, so to keep prices comparable to what a shopper actually
pays the connector restricts results to brand-new, fixed-price (Buy It Now)
listings and skips low-feedback sellers, auctions, and multipacks. ``GTIN``/UPC is
not present in the search summary; when ``fetch_details`` is enabled a per-item
``getItem`` call recovers it (enabling cross-source dedup + OFF nutrition), at the
cost of one extra request per item.
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any
from urllib.parse import quote

from ..categorize import classify_category
from ..config import get_settings
from ..markets import EBAY_MARKETPLACE, currency_for
from ..models import ProductRecord, VariantRecord
from ..units import is_multipack, parse_container_size_grams, to_cents
from .base import Connector

logger = logging.getLogger(__name__)

BASE_URL = "https://api.ebay.com"
TOKEN_URL = f"{BASE_URL}/identity/v1/oauth2/token"
SEARCH_URL = f"{BASE_URL}/buy/browse/v1/item_summary/search"
ITEM_URL = f"{BASE_URL}/buy/browse/v1/item"
SCOPE = "https://api.ebay.com/oauth/api_scope"
_PAGE_SIZE = 50
# Only brand-new, fixed-price listings — keeps the price comparable to retail and
# avoids auctions / used / refurbished noise.
_FILTER = "conditions:{NEW},buyingOptions:{FIXED_PRICE}"
_DEFAULT_QUERIES = [
    "whey protein powder",
    "plant protein powder",
    "casein protein powder",
    "protein isolate powder",
]
_EXCLUDE = [
    "bar", "ready to drink", "rtd", "shake", "drink", "snack", "cookie",
    "capsule", "tablet", "clif", "water", "creamer", "sample", "empty",
    "lot", "expired", "tub only", "container only",
]
# Skip sellers below this positive-feedback %% (junk / risky listings).
_MIN_FEEDBACK_PCT = 95.0


class EbayConnector(Connector):
    source_type = "ebay"

    @property
    def _max_pages(self) -> int:
        return int(self.config.get("max_pages", 2))

    @property
    def _queries(self) -> list[str]:
        return list(self.config.get("queries", _DEFAULT_QUERIES))

    @property
    def _fetch_details(self) -> bool:
        # getItem recovers the GTIN/UPC but doubles the request count.
        return bool(self.config.get("fetch_details", True))

    @property
    def _marketplace(self) -> str:
        return str(self.config.get("marketplace") or EBAY_MARKETPLACE.get(self.market, "EBAY_US"))

    async def _token(self) -> str:
        """Mint an OAuth client-credentials application access token."""
        settings = get_settings()
        creds = f"{settings.ebay_client_id}:{settings.ebay_client_secret}"
        basic = base64.b64encode(creds.encode()).decode()
        headers = {
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        raw = await self.fetcher.post_text(
            TOKEN_URL,
            data=f"grant_type=client_credentials&scope={quote(SCOPE)}",
            headers=headers,
        )
        return str(json.loads(raw)["access_token"])

    def _headers(self, token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": self._marketplace,
        }

    async def discover(self) -> list[dict[str, Any]]:
        if not get_settings().ebay_enabled:
            logger.warning("eBay credentials not set; skipping ebay source")
            return []

        token = await self._token()
        self._auth = self._headers(token)
        items: list[dict[str, Any]] = []
        seen: set[str] = set()
        for query in self._queries:
            for page in range(self._max_pages):
                offset = page * _PAGE_SIZE
                url = (
                    f"{SEARCH_URL}?q={quote(query)}&limit={_PAGE_SIZE}&offset={offset}"
                    f"&filter={quote(_FILTER)}"
                )
                raw = await self.fetcher.get_text(url, headers=self._auth)
                summaries = json.loads(raw).get("itemSummaries", []) or []
                if not summaries:
                    break
                for summary in summaries:
                    item_id = str(summary.get("itemId", ""))
                    if item_id and item_id not in seen and self._is_protein_powder(summary):
                        seen.add(item_id)
                        items.append(summary)
        return items

    @staticmethod
    def _is_protein_powder(summary: dict[str, Any]) -> bool:
        title = str(summary.get("title", ""))
        if is_multipack(title):
            return False
        lower = title.lower()
        if "protein" not in lower:
            return False
        if any(word in lower for word in _EXCLUDE):
            return False
        seller = summary.get("seller") or {}
        try:
            feedback = float(seller.get("feedbackPercentage", "0") or 0)
        except (TypeError, ValueError):
            feedback = 0.0
        return feedback >= _MIN_FEEDBACK_PCT

    async def extract(self, ref: dict[str, Any]) -> ProductRecord | None:
        upc: str | None = None
        if self._fetch_details:
            item_id = str(ref.get("itemId", ""))
            if item_id:
                try:
                    raw = await self.fetcher.get_text(
                        f"{ITEM_URL}/{quote(item_id, safe='')}",
                        headers=getattr(self, "_auth", {}),
                    )
                    upc = self._find_gtin(json.loads(raw))
                except Exception as exc:  # details are best-effort
                    logger.warning("ebay getItem failed for %s: %s", item_id, exc)
        return self.build_record(ref, upc=upc)

    @staticmethod
    def _find_gtin(item: dict[str, Any]) -> str | None:
        """Pull a UPC/EAN/GTIN from a getItem response."""
        gtin = item.get("gtin")
        if gtin and str(gtin).isdigit():
            return str(gtin)
        for aspect in item.get("localizedAspects", []) or []:
            name = str(aspect.get("name", "")).lower()
            if name in ("upc", "ean", "gtin"):
                value = str(aspect.get("value", "")).strip()
                if value.isdigit() and len(value) >= 12:
                    return value
        return None

    def build_record(
        self, summary: dict[str, Any], *, upc: str | None = None
    ) -> ProductRecord | None:
        """Pure (no I/O) assembly of a record from a Browse item summary."""
        item_id = str(summary.get("itemId", ""))
        title = str(summary.get("title", ""))
        if not item_id or not title:
            return None

        expected_currency = currency_for(self.market)
        price = summary.get("price") or {}
        price_cents = to_cents(price.get("value"))
        currency = str(price.get("currency", expected_currency))
        if not price_cents or currency != expected_currency:
            return None

        # marketingPrice.originalPrice is eBay's strikethrough (a genuine markdown).
        marketing = summary.get("marketingPrice") or {}
        original = to_cents((marketing.get("originalPrice") or {}).get("value"))
        compare_at = original if original and original > price_cents else None

        url = str(summary.get("itemWebUrl") or f"https://www.ebay.com/itm/{item_id}")
        size_g = parse_container_size_grams(title)
        # eBay summaries have no real brand field; the first title token is too
        # noisy, so leave brand resolution to the title/dedup key.
        brand = str(summary.get("brand") or "").strip() or "Unknown"

        variant = VariantRecord(
            source_variant_id=item_id,
            flavor=None,
            size_g=size_g,
            size_label=None,
            price_cents=price_cents,
            currency=expected_currency,
            in_stock=True,  # search returns active listings only
            upc=upc,
            compare_at_price_cents=compare_at,
            nutrition=None,  # filled by Open Food Facts enrichment via UPC
        )
        return ProductRecord(
            source_sku=item_id,
            url=url,
            title=title,
            brand_name=brand,
            product_name=title,
            category=classify_category(title),
            raw_payload=summary,
            variants=[variant],
        )
