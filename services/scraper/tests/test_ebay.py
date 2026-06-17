import json
from pathlib import Path

import pytest

from protein_scraper.connectors.ebay import EbayConnector

SUMMARY = json.loads(
    (Path(__file__).parent / "fixtures" / "ebay_item_summary.json").read_text()
)

SOURCE = {
    "id": "00000000-0000-0000-0000-000000000000",
    "slug": "ebay",
    "name": "eBay",
    "type": "ebay",
    "baseUrl": "https://www.ebay.com",
    "config": {},
}


SOURCE_UK = {
    **SOURCE,
    "slug": "ebay-uk",
    "market": "UK",
    "baseUrl": "https://www.ebay.co.uk",
    "config": {"marketplace": "EBAY_GB"},
}


def _connector() -> EbayConnector:
    return EbayConnector(SOURCE, fetcher=None, llm=None)


def _connector_uk() -> EbayConnector:
    return EbayConnector(SOURCE_UK, fetcher=None, llm=None)


def test_build_record_from_summary():
    record = _connector().build_record(SUMMARY, upc="074893702401")
    assert record is not None
    assert record.source_sku == "v1|123456789012|0"
    assert record.url == "https://www.ebay.com/itm/123456789012"
    assert record.category == "whey"
    v = record.variants[0]
    assert v.price_cents == 6995
    # marketingPrice.originalPrice (79.99) is a genuine strikethrough markdown.
    assert v.compare_at_price_cents == 7999
    assert v.upc == "074893702401"
    assert v.in_stock is True
    assert v.size_g == pytest.approx(2267.96, abs=1.0)
    assert v.nutrition is None


def test_non_usd_skipped():
    summary = json.loads(json.dumps(SUMMARY))
    summary["price"] = {"value": "59.99", "currency": "GBP"}
    assert _connector().build_record(summary) is None


def test_uk_market_accepts_gbp_and_uses_gb_marketplace():
    c = _connector_uk()
    assert c.market == "UK"
    assert c._marketplace == "EBAY_GB"
    summary = json.loads(json.dumps(SUMMARY))
    summary["price"] = {"value": "59.99", "currency": "GBP"}
    record = c.build_record(summary)
    assert record is not None
    v = record.variants[0]
    assert v.price_cents == 5999
    assert v.currency == "GBP"


def test_uk_market_skips_usd():
    summary = json.loads(json.dumps(SUMMARY))  # fixture price is USD
    assert _connector_uk().build_record(summary) is None


def test_no_marketing_price_no_sale():
    summary = json.loads(json.dumps(SUMMARY))
    summary.pop("marketingPrice")
    v = _connector().build_record(summary).variants[0]
    assert v.compare_at_price_cents is None


def test_protein_filter_condition_and_feedback():
    c = _connector()
    assert c._is_protein_powder(SUMMARY) is True
    # Multipack excluded.
    assert not c._is_protein_powder(
        {**SUMMARY, "title": "Whey Protein Powder 5lb (Pack of 3)"}
    )
    # Non-powder excluded.
    assert not c._is_protein_powder({**SUMMARY, "title": "Protein Bar 12 Count"})
    # Low-feedback seller excluded (price-accuracy guard).
    assert not c._is_protein_powder(
        {**SUMMARY, "seller": {"feedbackPercentage": "80.0"}}
    )
    # Missing feedback treated as 0 => excluded.
    assert not c._is_protein_powder({**SUMMARY, "seller": {}})


def test_find_gtin():
    assert EbayConnector._find_gtin({"gtin": "0074893702401"}) == "0074893702401"
    assert (
        EbayConnector._find_gtin(
            {"localizedAspects": [{"name": "UPC", "value": "074893702401"}]}
        )
        == "074893702401"
    )
    assert EbayConnector._find_gtin({"gtin": "Does Not Apply"}) is None
    assert EbayConnector._find_gtin({}) is None
