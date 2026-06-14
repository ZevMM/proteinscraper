from protein_scraper.identity import (
    canonical_core_name,
    normalize_brand,
    product_dedup_key,
)


def test_normalize_brand_aliases_and_full_names_converge():
    assert normalize_brand("ON") == "optimum nutrition"
    assert normalize_brand("Optimum Nutrition") == "optimum nutrition"
    assert normalize_brand("BPN") == "bare performance nutrition"
    assert normalize_brand("Bare Performance Nutrition") == "bare performance nutrition"
    assert normalize_brand("Ghost") == "ghost lifestyle"


def test_canonical_core_strips_brand_flavor_size_noise():
    core = canonical_core_name(
        "Optimum Nutrition",
        "Optimum Nutrition Gold Standard 100% Whey - Double Rich Chocolate, 5 lb",
    )
    assert core == "gold standard whey"


def test_same_product_across_sources_gets_same_key():
    # Same product, different retailer wording + abbreviation + size/flavor.
    a = product_dedup_key(
        "Optimum Nutrition",
        "Optimum Nutrition Gold Standard 100% Whey, Vanilla Ice Cream, 5 lb",
    )
    b = product_dedup_key("ON", "ON Gold Standard Whey 2 lb Double Rich Chocolate")
    assert a == b == "optimum-nutrition:gold-standard-whey"


def test_different_types_do_not_merge():
    isolate = product_dedup_key("Dymatize", "Dymatize ISO100 Whey Isolate 1.6 lb")
    casein = product_dedup_key("Dymatize", "Dymatize Elite Casein 4 lb")
    assert isolate != casein
