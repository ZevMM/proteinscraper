"""Source connectors. Each knows how to discover and extract products for one
kind of site (Shopify feed, JSON-LD retailer, marketplace API, ...)."""

from __future__ import annotations

from typing import Any

from ..extract.llm import LlmExtractor
from ..http import Fetcher
from .amazon import AmazonConnector
from .base import Connector
from .ebay import EbayConnector
from .jsonld import JsonLdConnector
from .kroger import KrogerConnector
from .shopify import ShopifyConnector
from .walmart import WalmartConnector

_REGISTRY: dict[str, type[Connector]] = {
    ShopifyConnector.source_type: ShopifyConnector,
    JsonLdConnector.source_type: JsonLdConnector,
    WalmartConnector.source_type: WalmartConnector,
    AmazonConnector.source_type: AmazonConnector,
    KrogerConnector.source_type: KrogerConnector,
    EbayConnector.source_type: EbayConnector,
}


def get_connector(
    source: dict[str, Any], fetcher: Fetcher, llm: LlmExtractor | None = None
) -> Connector:
    """Instantiate the connector matching a source's ``type``."""
    source_type = source["type"]
    try:
        cls = _REGISTRY[source_type]
    except KeyError as exc:
        raise ValueError(f"No connector registered for source type {source_type!r}") from exc
    return cls(source, fetcher, llm)


__all__ = [
    "AmazonConnector",
    "Connector",
    "EbayConnector",
    "JsonLdConnector",
    "KrogerConnector",
    "ShopifyConnector",
    "WalmartConnector",
    "get_connector",
]
