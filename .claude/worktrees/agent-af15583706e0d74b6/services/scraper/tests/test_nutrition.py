from protein_scraper.extract.nutrition import parse_nutrition_html, parse_nutrition_text


def test_parse_supplement_facts_text():
    text = (
        "Serving Size 1 Scoop (33 g) Servings Per Container 30 Calories 120 "
        "Total Fat 1.5g Total Carbohydrate 5g Total Sugars 1g Protein 22g"
    )
    n = parse_nutrition_text(text)
    assert n.serving_size_g == 33
    assert n.servings_per_container == 30
    assert n.calories_kcal == 120
    assert n.fat_g == 1.5
    assert n.carb_g == 5
    assert n.sugar_g == 1
    assert n.protein_g == 22
    assert n.is_complete()


def test_parse_from_html_strips_tags():
    html = "<div><p>Protein 25g</p><p>Serving Size 40 g</p></div>"
    n = parse_nutrition_html(html)
    assert n.protein_g == 25
    assert n.serving_size_g == 40


def test_prose_protein_pattern():
    # Real DTC stores often state macros in prose rather than a facts table.
    n = parse_nutrition_text("delivering 30g of pure protein and 6.5g of BCAAs per serving")
    assert n.protein_g == 30


def test_incomplete_when_fields_absent():
    n = parse_nutrition_text("Great taste, mixes easily.")
    assert not n.is_complete()
    assert n.protein_g is None
