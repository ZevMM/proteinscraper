"""Accuracy guardrails: sanity-check extracted nutrition before it is stored.

Failures are surfaced (and routed to ExtractionIssue by the pipeline) rather than
silently writing implausible numbers into the catalog. Each record also gets a
0..1 confidence score that the frontend can use to down-rank shaky data.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import ExtractionMethod, NutritionRecord

# Base confidence by how the data was obtained (structured > parsed > guessed).
_BASE_CONFIDENCE: dict[ExtractionMethod, float] = {
    ExtractionMethod.manual: 1.0,
    ExtractionMethod.shopify_json: 0.9,
    ExtractionMethod.json_ld: 0.9,
    ExtractionMethod.html_parse: 0.7,
    ExtractionMethod.llm: 0.6,
}

# Plausible ranges for a single serving of protein powder.
SERVING_SIZE_MIN_G = 5.0
SERVING_SIZE_MAX_G = 250.0
SERVINGS_MIN = 1.0
SERVINGS_MAX = 400.0

# Atwater calorie tolerance. Protein powders carry fiber / sugar alcohols /
# rounding, so allow a generous band before flagging.
CALORIE_TOLERANCE = 0.30
# Container weight reconstructed from serving math may differ from the label.
CONTAINER_WEIGHT_TOLERANCE = 0.25


@dataclass
class ValidationResult:
    ok: bool
    confidence: float
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _predicted_calories(n: NutritionRecord) -> float | None:
    if n.protein_g is None or n.carb_g is None or n.fat_g is None:
        return None
    return 4.0 * n.protein_g + 4.0 * n.carb_g + 9.0 * n.fat_g


def validate_nutrition(n: NutritionRecord, *, size_g: float | None = None) -> ValidationResult:
    """Validate one nutrition record. ``ok=False`` means do not store it."""
    errors: list[str] = []
    warnings: list[str] = []

    # --- Hard requirements -------------------------------------------------
    if not n.is_complete():
        errors.append("missing required fields (protein_g, servings_per_container)")

    for label, value in (
        ("protein_g", n.protein_g),
        ("fat_g", n.fat_g),
        ("carb_g", n.carb_g),
        ("calories_kcal", n.calories_kcal),
        ("serving_size_g", n.serving_size_g),
        ("servings_per_container", n.servings_per_container),
    ):
        if value is not None and value < 0:
            errors.append(f"{label} is negative ({value})")

    if n.protein_g is not None and n.serving_size_g is not None and n.protein_g > n.serving_size_g:
        errors.append(
            f"protein_g ({n.protein_g}) exceeds serving_size_g ({n.serving_size_g})"
        )

    # A real container has at least one serving; < 1 means the serving math is
    # broken (usually a bad container size), so reject rather than store garbage.
    if n.servings_per_container is not None and n.servings_per_container < 1:
        errors.append(f"servings_per_container ({n.servings_per_container}) is below 1")

    # --- Soft sanity checks (reduce confidence, don't reject) --------------
    if n.serving_size_g is not None and not (
        SERVING_SIZE_MIN_G <= n.serving_size_g <= SERVING_SIZE_MAX_G
    ):
        warnings.append(f"serving_size_g {n.serving_size_g} outside plausible range")

    if n.servings_per_container is not None and not (
        SERVINGS_MIN <= n.servings_per_container <= SERVINGS_MAX
    ):
        warnings.append(
            f"servings_per_container {n.servings_per_container} outside plausible range"
        )

    predicted = _predicted_calories(n)
    if predicted is not None and n.calories_kcal is not None and n.calories_kcal > 0:
        rel = abs(n.calories_kcal - predicted) / n.calories_kcal
        if rel > CALORIE_TOLERANCE:
            warnings.append(
                f"calories {n.calories_kcal} disagree with macros (~{predicted:.0f} kcal, "
                f"{rel * 100:.0f}% off)"
            )

    if (
        size_g is not None
        and n.serving_size_g is not None
        and n.servings_per_container is not None
    ):
        reconstructed = n.serving_size_g * n.servings_per_container
        if size_g > 0 and abs(reconstructed - size_g) / size_g > CONTAINER_WEIGHT_TOLERANCE:
            warnings.append(
                f"serving math ({reconstructed:.0f} g) disagrees with "
                f"container size ({size_g:.0f} g)"
            )

    # --- Confidence --------------------------------------------------------
    base = _BASE_CONFIDENCE.get(n.extraction_method, 0.5)
    confidence = max(0.0, base - 0.15 * len(warnings))
    if errors:
        confidence = 0.0

    return ValidationResult(
        ok=not errors,
        confidence=round(confidence, 3),
        errors=errors,
        warnings=warnings,
    )
