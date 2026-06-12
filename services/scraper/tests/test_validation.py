from protein_scraper.models import ExtractionMethod, NutritionRecord
from protein_scraper.validation import validate_nutrition


def _good() -> NutritionRecord:
    return NutritionRecord(
        serving_size_g=33,
        servings_per_container=30,
        protein_g=22,
        fat_g=1.5,
        carb_g=5,
        sugar_g=1,
        calories_kcal=120,
        extraction_method=ExtractionMethod.html_parse,
    )


def test_valid_record_passes():
    result = validate_nutrition(_good(), size_g=998)
    assert result.ok
    assert not result.errors
    assert not result.warnings
    assert result.confidence == 0.7  # html_parse base, no penalties


def test_missing_required_fields_rejected():
    record = NutritionRecord(protein_g=22, extraction_method=ExtractionMethod.html_parse)
    result = validate_nutrition(record)
    assert not result.ok
    assert result.confidence == 0.0


def test_protein_exceeds_serving_rejected():
    record = _good()
    record.protein_g = 50  # > serving_size_g
    result = validate_nutrition(record)
    assert not result.ok
    assert any("exceeds serving" in e for e in result.errors)


def test_calorie_mismatch_warns_not_rejects():
    record = _good()
    record.calories_kcal = 400  # macros imply ~121 kcal
    result = validate_nutrition(record, size_g=998)
    assert result.ok
    assert result.warnings
    assert result.confidence < 0.7


def test_container_weight_mismatch_warns():
    record = _good()
    # 33g * 30 servings = 990g, but claim a 5 lb (2268g) container.
    result = validate_nutrition(record, size_g=2268)
    assert result.ok
    assert any("container" in w for w in result.warnings)


def test_negative_value_rejected():
    record = _good()
    record.fat_g = -1
    result = validate_nutrition(record)
    assert not result.ok
