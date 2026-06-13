import pytest

from protein_scraper.connectors.amazon import AmazonConnector

SEARCH_ITEM = {
    "asin": "B000QSNYGI",
    "product_title": (
        "Optimum Nutrition Gold Standard 100% Whey Protein Powder, "
        "Double Rich Chocolate, 5 Pound"
    ),
    "product_price": "$74.99",
    "product_original_price": "$89.99",
    "product_url": "https://www.amazon.com/dp/B000QSNYGI",
}


def _connector(fetch_details: bool = False) -> AmazonConnector:
    source = {
        "id": "00000000-0000-0000-0000-000000000000",
        "slug": "amazon",
        "name": "Amazon",
        "type": "amazon",
        "baseUrl": "https://www.amazon.com",
        "config": {"fetch_details": fetch_details},
    }
    return AmazonConnector(source, fetcher=None, llm=None)


@pytest.mark.asyncio
async def test_extract_search_only():
    # fetch_details=False => no network call, parse from the search item.
    record = await _connector(fetch_details=False).extract(SEARCH_ITEM)
    assert record is not None
    assert record.category == "whey"
    assert record.source_sku == "B000QSNYGI"
    v = record.variants[0]
    assert v.price_cents == 7499
    assert v.compare_at_price_cents == 8999
    assert v.size_g == pytest.approx(2267.96, abs=1.0)
    assert v.upc is None  # only available via product-details
    assert v.nutrition is None


def test_find_upc_from_product_information():
    details = {"product_information": {"UPC": "0748927024074", "Brand": "ON"}}
    assert AmazonConnector._find_upc(details) == "0748927024074"
    assert AmazonConnector._find_upc({"product_information": {}}) is None


def test_brand_from_info_and_byline():
    assert (
        AmazonConnector._brand({}, {"Brand": "NOW Sports"}) == "NOW Sports"
    )
    assert (
        AmazonConnector._brand({"product_byline": "Visit the Dymatize Store"}, {})
        == "Dymatize"
    )


def test_protein_filter():
    assert AmazonConnector._is_protein_powder({"product_title": "Whey Protein Powder 5lb"})
    assert not AmazonConnector._is_protein_powder(
        {"product_title": "Quest Protein Bar, Chocolate, 12 Count"}
    )
