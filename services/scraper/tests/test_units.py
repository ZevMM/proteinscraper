import math

from protein_scraper.units import (
    clean_flavor,
    parse_servings,
    parse_weight_to_grams,
    to_cents,
)


def _close(a, b, tol=0.5):
    return a is not None and math.isclose(a, b, abs_tol=tol)


def test_parse_weight_pounds():
    assert _close(parse_weight_to_grams("5 lb"), 2267.96)
    assert _close(parse_weight_to_grams("2.2 lb"), 997.9)
    assert _close(parse_weight_to_grams("2.2lbs"), 997.9)


def test_parse_weight_kg_oz_g():
    assert _close(parse_weight_to_grams("2.27 kg"), 2270.0, tol=1)
    assert _close(parse_weight_to_grams("32 oz"), 907.18)
    assert _close(parse_weight_to_grams("907 g"), 907.0)


def test_parse_weight_from_messy_label():
    # First weight token in "1 Scoop (33 g)" is the grams value.
    assert _close(parse_weight_to_grams("1 Scoop (33 g)"), 33.0)


def test_parse_weight_none():
    assert parse_weight_to_grams("no weight here") is None
    assert parse_weight_to_grams(None) is None


def test_parse_servings():
    assert parse_servings("About 30 servings") == 30.0
    assert parse_servings("no count") is None


def test_to_cents():
    assert to_cents("49.99") == 4999
    assert to_cents(49.99) == 4999
    assert to_cents("$59.00") == 5900
    assert to_cents(None) is None


def test_clean_flavor():
    assert clean_flavor("Default Title") is None
    assert clean_flavor("  Chocolate  ") == "Chocolate"
    assert clean_flavor(None) is None
