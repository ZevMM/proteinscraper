"""Market → currency / eBay-marketplace mappings.

A Source belongs to exactly one market (US/UK/IN). Prices are stored in the
market's local currency; metrics are only ever compared within a market.
"""

from __future__ import annotations

MARKET_CURRENCY: dict[str, str] = {"US": "USD", "UK": "GBP", "IN": "INR"}

# eBay Browse marketplace IDs (X-EBAY-C-MARKETPLACE-ID). eBay India is closed.
EBAY_MARKETPLACE: dict[str, str] = {"US": "EBAY_US", "UK": "EBAY_GB"}

# Amazon storefront domain per market, for URL fallbacks.
AMAZON_DOMAIN: dict[str, str] = {"US": "amazon.com", "UK": "amazon.co.uk", "IN": "amazon.in"}


def currency_for(market: str) -> str:
    return MARKET_CURRENCY.get(market, "USD")
