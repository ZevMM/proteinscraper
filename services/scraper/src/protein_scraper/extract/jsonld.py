"""schema.org JSON-LD extraction (extraction tier 1 for non-Shopify retailers)."""

from __future__ import annotations

from typing import Any

import extruct


def extract_jsonld_products(html: str) -> list[dict[str, Any]]:
    """Return all schema.org Product nodes found in a page's JSON-LD."""
    data = extruct.extract(html, syntaxes=["json-ld"], uniform=True)
    products: list[dict[str, Any]] = []
    for node in data.get("json-ld", []):
        products.extend(_collect_products(node))
    return products


def _collect_products(node: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if isinstance(node, list):
        for child in node:
            out.extend(_collect_products(child))
    elif isinstance(node, dict):
        if "@graph" in node:
            for child in node["@graph"]:
                out.extend(_collect_products(child))
        if _is_type(node, "Product"):
            out.append(node)
    return out


def _is_type(node: dict[str, Any], wanted: str) -> bool:
    types = node.get("@type")
    if isinstance(types, list):
        return wanted in types
    return types == wanted


def pick_offer(node: dict[str, Any]) -> dict[str, Any] | None:
    """Return a single offer dict (handles Offer / AggregateOffer / lists)."""
    offers = node.get("offers")
    if offers is None:
        return None
    if isinstance(offers, list):
        offers = offers[0] if offers else None
    if not isinstance(offers, dict):
        return None
    return offers


def offer_price(offer: dict[str, Any]) -> Any:
    """Price from an Offer (price) or AggregateOffer (lowPrice)."""
    return offer.get("price") or offer.get("lowPrice")


def brand_name(node: dict[str, Any]) -> str | None:
    brand = node.get("brand")
    if isinstance(brand, dict):
        return brand.get("name")
    if isinstance(brand, str):
        return brand
    return None
