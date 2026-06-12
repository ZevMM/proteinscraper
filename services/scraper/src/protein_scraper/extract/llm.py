"""Extraction tier 3: Claude Haiku fallback for nutrition fields still missing
after structured-data and HTML parsing.

Kept deliberately small and cheap: Haiku, a tight token budget, a forced-tool
structured output, and a cacheable system prompt. The pipeline only calls this
when cheaper tiers leave required fields empty, and results are cached upstream
by page content hash.
"""

from __future__ import annotations

import logging

from ..models import ExtractionMethod, NutritionRecord

logger = logging.getLogger(__name__)

# Cheapest capable Claude model — ideal for short structured extraction.
DEFAULT_MODEL = "claude-haiku-4-5-20251001"

_SYSTEM = (
    "You extract per-serving nutrition facts for a single protein powder product "
    "from messy product-page text. Report values for ONE serving as stated on the "
    "Supplement/Nutrition Facts panel. Convert all weights to grams. If a field is "
    "not clearly stated, return null for it rather than guessing. Never fabricate."
)

_NUTRITION_TOOL = {
    "name": "record_nutrition",
    "description": "Record the per-serving nutrition facts for the protein powder.",
    "input_schema": {
        "type": "object",
        "properties": {
            "serving_size_g": {"type": ["number", "null"], "description": "Serving size in grams"},
            "servings_per_container": {"type": ["number", "null"]},
            "protein_g": {"type": ["number", "null"]},
            "fat_g": {"type": ["number", "null"]},
            "carb_g": {"type": ["number", "null"]},
            "sugar_g": {"type": ["number", "null"]},
            "calories_kcal": {"type": ["number", "null"]},
        },
        "required": [
            "serving_size_g",
            "servings_per_container",
            "protein_g",
            "fat_g",
            "carb_g",
            "sugar_g",
            "calories_kcal",
        ],
    },
}


class LlmExtractor:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL, max_chars: int = 6000) -> None:
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)
        self._model = model
        self._max_chars = max_chars

    def extract_nutrition(self, text: str, *, title: str | None = None) -> NutritionRecord | None:
        snippet = text[: self._max_chars]
        try:
            message = self._client.messages.create(  # type: ignore[call-overload]
                model=self._model,
                max_tokens=512,
                system=[{"type": "text", "text": _SYSTEM, "cache_control": {"type": "ephemeral"}}],
                tools=[_NUTRITION_TOOL],
                tool_choice={"type": "tool", "name": "record_nutrition"},
                messages=[
                    {"role": "user", "content": f"Product: {title or 'unknown'}\n\n{snippet}"}
                ],
            )
        except Exception as exc:  # network / API errors must not crash the run
            logger.warning("LLM extraction failed: %s", exc)
            return None

        for block in message.content:
            if block.type == "tool_use":
                data = block.input
                return NutritionRecord(
                    serving_size_g=data.get("serving_size_g"),
                    servings_per_container=data.get("servings_per_container"),
                    protein_g=data.get("protein_g"),
                    fat_g=data.get("fat_g"),
                    carb_g=data.get("carb_g"),
                    sugar_g=data.get("sugar_g"),
                    calories_kcal=data.get("calories_kcal"),
                    extraction_method=ExtractionMethod.llm,
                )
        return None
