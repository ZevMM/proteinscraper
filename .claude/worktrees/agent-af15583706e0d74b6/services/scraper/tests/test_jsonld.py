from pathlib import Path

import pytest

from protein_scraper.connectors.jsonld import JsonLdConnector
from protein_scraper.extract.jsonld import brand_name, extract_jsonld_products, pick_offer

HTML = (Path(__file__).parent / "fixtures" / "jsonld_product.html").read_text()

SOURCE = {
    "id": "00000000-0000-0000-0000-000000000000",
    "slug": "peakform",
    "name": "PeakForm",
    "type": "jsonld",
    "baseUrl": "https://peakform.example",
    "config": {"product_urls": ["https://peakform.example/p/whey-isolate"]},
}


def _connector() -> JsonLdConnector:
    return JsonLdConnector(SOURCE, fetcher=None, llm=None)


def test_extract_jsonld_helpers():
    products = extract_jsonld_products(HTML)
    assert len(products) == 1
    node = products[0]
    assert brand_name(node) == "PeakForm"
    offer = pick_offer(node)
    assert offer is not None and offer["price"] == "54.99"


def test_build_record_from_jsonld():
    record = _connector().build_record("https://peakform.example/p/whey-isolate", HTML)
    assert record is not None
    assert record.brand_name == "PeakForm"
    assert record.category == "isolate"
    assert len(record.variants) == 1

    v = record.variants[0]
    assert v.price_cents == 5499
    assert v.currency == "USD"
    assert v.in_stock is True
    assert v.size_g == pytest.approx(907.2, abs=1.0)

    assert v.nutrition is not None
    assert v.nutrition.protein_g == 25
    assert v.nutrition.servings_per_container == 30
    assert v.nutrition.is_complete()


@pytest.mark.asyncio
async def test_discover_uses_configured_urls():
    # With only product_urls (no sitemap), discover needs no network.
    urls = await _connector().discover()
    assert urls == ["https://peakform.example/p/whey-isolate"]
