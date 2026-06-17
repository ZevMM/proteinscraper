import json
from pathlib import Path

import pytest

from protein_scraper.connectors.shopify import ShopifyConnector

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "shopify_product.json").read_text())

SOURCE = {
    "id": "00000000-0000-0000-0000-000000000000",
    "slug": "legion",
    "name": "Legion Athletics",
    "type": "shopify",
    "baseUrl": "https://legionathletics.com",
    "config": {},
}


def _connector() -> ShopifyConnector:
    # extract() needs no network, so a None fetcher is fine here.
    return ShopifyConnector(SOURCE, fetcher=None, llm=None)


@pytest.mark.asyncio
async def test_india_market_prices_in_inr():
    source = {**SOURCE, "slug": "nakpro", "market": "IN", "baseUrl": "https://nakpro.com"}
    record = await ShopifyConnector(source, fetcher=None, llm=None).extract(FIXTURE)
    assert record is not None
    assert all(v.currency == "INR" for v in record.variants)


@pytest.mark.asyncio
async def test_extract_builds_product_record():
    record = await _connector().extract(FIXTURE)
    assert record is not None
    assert record.brand_name == "Legion"
    assert record.product_name == "Whey Protein Powder"
    assert record.category == "whey"
    assert record.url == "https://legionathletics.com/products/whey-protein-powder"
    assert len(record.variants) == 2


@pytest.mark.asyncio
async def test_variant_fields_normalized():
    record = await _connector().extract(FIXTURE)
    by_flavor = {v.flavor: v for v in record.variants}
    assert set(by_flavor) == {"Chocolate", "Vanilla"}

    choc = by_flavor["Chocolate"]
    assert choc.price_cents == 4999
    assert choc.size_label == "2.2 lb"
    assert choc.size_g == pytest.approx(997.9, abs=1.0)
    assert choc.in_stock is True
    assert by_flavor["Vanilla"].in_stock is False


@pytest.mark.asyncio
async def test_nutrition_attached_and_complete():
    record = await _connector().extract(FIXTURE)
    nutrition = record.variants[0].nutrition
    assert nutrition is not None
    assert nutrition.protein_g == 22
    assert nutrition.servings_per_container == 30
    assert nutrition.is_complete()


def test_protein_filter():
    c = _connector()
    assert c._is_protein_powder(FIXTURE) is True
    assert c._is_protein_powder(
        {"title": "Stainless Shaker Bottle", "product_type": "Accessories", "tags": []}
    ) is False
