import json
from pathlib import Path

import pytest

from protein_scraper.enrich.openfoodfacts import parse_off_product
from protein_scraper.models import ExtractionMethod

PRODUCT = json.loads((Path(__file__).parent / "fixtures" / "off_product.json").read_text())


def test_parse_per_serving_values():
    n = parse_off_product(PRODUCT, size_g=None)
    assert n is not None
    assert n.serving_size_g == 31
    assert n.protein_g == 24
    assert n.fat_g == 1.5
    assert n.carb_g == 3
    assert n.calories_kcal == 120
    # product_quantity (907g) / serving (31g)
    assert n.servings_per_container == pytest.approx(29.3, abs=0.1)
    assert n.extraction_method == ExtractionMethod.open_food_facts
    assert n.is_complete()


def test_scales_from_per_100g_when_no_per_serving():
    product = {
        "serving_quantity": 31,
        "nutriments": {"proteins_100g": 77.4},
    }
    n = parse_off_product(product, size_g=None)
    assert n is not None
    assert n.protein_g == pytest.approx(24.0, abs=0.1)


def test_returns_none_when_no_usable_data():
    assert parse_off_product({"nutriments": {}}, size_g=None) is None
