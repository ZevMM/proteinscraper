from protein_scraper.ingredients import (
    ARTIFICIAL_SWEETENERS,
    derive_facts,
    extract_ingredients_text,
)


def test_extract_ingredients_section():
    text = (
        "Great taste! Ingredients: Whey Protein Isolate, Cocoa, Natural Flavor, "
        "Stevia Leaf Extract. Directions: mix one scoop."
    )
    assert extract_ingredients_text(text) == (
        "Whey Protein Isolate, Cocoa, Natural Flavor, Stevia Leaf Extract"
    )
    assert extract_ingredients_text("no list here") is None


def test_derive_from_ingredient_text():
    facts = derive_facts(
        "Whey Protein Concentrate, Soy Lecithin, Sucralose, Stevia Leaf Extract"
    )
    assert facts is not None
    assert facts.allergens == ["milk", "soy"]
    assert set(facts.sweeteners) == {"sucralose", "stevia"}
    # sucralose is artificial
    assert any(s in ARTIFICIAL_SWEETENERS for s in facts.sweeteners)
    assert facts.ingredients_text is not None


def test_explicit_labels_and_allergens_win():
    facts = derive_facts(
        ingredients_text=None,
        labels=["Gluten Free", "Keto", "Vegan"],
        allergens=["Milk", "Soy"],
    )
    assert facts is not None
    assert set(facts.dietary_labels) == {"gluten_free", "keto", "vegan"}
    assert set(facts.allergens) == {"milk", "soy"}


def test_label_text_scanned_for_dietary():
    facts = derive_facts("Pea Protein, Rice Protein", label_text="Certified USDA Organic, Non-GMO")
    assert facts is not None
    assert "organic" in facts.dietary_labels
    assert "non_gmo" in facts.dietary_labels


def test_empty_returns_none():
    assert derive_facts(None) is None
    # Ingredient text is kept for display even when no facets are derived.
    kept = derive_facts("water")
    assert kept is not None and kept.ingredients_text == "water"
    assert kept.dietary_labels == [] and kept.allergens == [] and kept.sweeteners == []
