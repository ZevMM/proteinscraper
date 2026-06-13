import json
from pathlib import Path

import pytest

from protein_scraper.connectors.walmart import WalmartConnector

ITEM = json.loads((Path(__file__).parent / "fixtures" / "walmart_item.json").read_text())

SOURCE = {
    "id": "00000000-0000-0000-0000-000000000000",
    "slug": "walmart",
    "name": "Walmart",
    "type": "walmart",
    "baseUrl": "https://www.walmart.com",
    "config": {},
}


def _connector() -> WalmartConnector:
    return WalmartConnector(SOURCE, fetcher=None, llm=None)


@pytest.mark.asyncio
async def test_extract_walmart_item():
    record = await _connector().extract(ITEM)
    assert record is not None
    assert record.brand_name == "Optimum Nutrition"
    assert record.category == "whey"
    assert len(record.variants) == 1

    v = record.variants[0]
    assert v.price_cents == 7499
    assert v.compare_at_price_cents == 8999  # msrp > sale price
    assert v.upc == "748927024074"
    assert v.in_stock is True
    assert v.size_g == pytest.approx(2267.96, abs=1.0)
    assert v.nutrition is None  # enriched later via Open Food Facts


def test_protein_filter_excludes_non_powder():
    c = _connector()
    assert c._is_protein_powder(ITEM) is True
    assert (
        c._is_protein_powder(
            {"name": "Protein Bar Chocolate 12 ct", "categoryPath": "Food/Snacks"}
        )
        is False
    )
