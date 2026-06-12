"""Source connectors. Each knows how to discover and extract products for one
kind of site (Shopify feed, JSON-LD retailer, marketplace API, ...)."""

from __future__ import annotations

from typing import Any

from ..extract.llm import LlmExtractor
from ..http import Fetcher
from .base import Connector
from .jsonld import JsonLdConnector
from .shopify import ShopifyConnector

_REGISTRY: dict[str, type[Connector]] = {
    ShopifyConnector.source_type: ShopifyConnector,
    JsonLdConnector.source_type: JsonLdConnector,
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


__all__ = ["Connector", "JsonLdConnector", "ShopifyConnector", "get_connector"]
