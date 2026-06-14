import json
from pathlib import Path

import pytest

from protein_scraper.connectors.kroger import KrogerConnector

PRODUCT = json.loads((Path(__file__).parent / "fixtures" / "kroger_product.json").read_text())

SOURCE = {
    "id": "00000000-0000-0000-0000-000000000000",
    "slug": "kroger",
    "name": "Kroger",
    "type": "kroger",
    "baseUrl": "https://www.kroger.com",
    "config": {},
}


def _connector() -> KrogerConnector:
    return KrogerConnector(SOURCE, fetcher=None, llm=None)


def test_build_record_from_product():
    record = _connector().build_record(PRODUCT)
    assert record is not None
    assert record.brand_name == "Optimum Nutrition"
    assert record.category == "whey"
    assert record.source_sku == "0074893702401"
    assert record.url == "https://www.kroger.com/p/x/0074893702401"
    assert len(record.variants) == 1

    v = record.variants[0]
    # promo (64.99) is the current sale price; regular (74.99) becomes compare_at.
    assert v.price_cents == 6499
    assert v.compare_at_price_cents == 7499
    assert v.upc == "0074893702401"
    assert v.in_stock is True
    assert v.size_g == pytest.approx(2267.96, abs=1.0)
    assert v.nutrition is None  # enriched later via Open Food Facts


def test_no_promo_uses_regular_no_sale():
    item = json.loads(json.dumps(PRODUCT))
    item["items"][0]["price"] = {"regular": 49.99}
    v = _connector().build_record(item).variants[0]
    assert v.price_cents == 4999
    assert v.compare_at_price_cents is None


def test_promo_above_regular_is_not_a_sale():
    # Defensive: a promo >= regular is not a markdown.
    item = json.loads(json.dumps(PRODUCT))
    item["items"][0]["price"] = {"regular": 49.99, "promo": 49.99}
    v = _connector().build_record(item).variants[0]
    assert v.price_cents == 4999
    assert v.compare_at_price_cents is None


def test_out_of_stock():
    item = json.loads(json.dumps(PRODUCT))
    item["items"][0]["inventory"] = {"stockLevel": "TEMPORARILY_OUT_OF_STOCK"}
    assert _connector().build_record(item).variants[0].in_stock is False


def test_protein_filter():
    c = _connector()
    assert c._is_protein_powder(PRODUCT) is True
    assert (
        c._is_protein_powder(
            {"description": "Quest Protein Bar Chocolate", "brand": "Quest", "categories": []}
        )
        is False
    )
    assert (
        c._is_protein_powder({"description": "Whole Milk", "brand": "Kroger", "categories": []})
        is False
    )
