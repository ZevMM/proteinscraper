"""Product identity / canonicalization for cross-source dedup.

Shopify public feeds expose no universal UPC, so the same product sold by
multiple sources is matched on a canonical key: normalized brand + a core
product name with flavor/size/marketing words stripped out. UPC, when present
(Walmart, Open Food Facts), is used as a stronger secondary merge signal by the
pipeline.
"""

from __future__ import annotations

import re

# Map common brand spellings/abbreviations to a single canonical brand. Values
# are the canonical full form so abbreviations and full names converge.
_BRAND_ALIASES: dict[str, str] = {
    "on": "optimum nutrition",
    "bpn": "bare performance nutrition",
    "ghost": "ghost lifestyle",
    "raw": "raw nutrition",
    "mts": "mts nutrition",
}

# Flavor + marketing words stripped from the core product name. Flavors are a
# variant attribute, so removing them groups all flavors under one product.
_FLAVOR_WORDS = {
    "chocolate", "vanilla", "strawberry", "banana", "cookies", "cream", "cookie",
    "dough", "peanut", "butter", "caramel", "mocha", "coffee", "latte", "mint",
    "birthday", "cake", "unflavored", "unflavoured", "natural", "fruity", "fruit",
    "cinnamon", "salted", "coconut", "mango", "berry", "blueberry", "raspberry",
    "lemon", "lemonade", "orange", "smores", "marshmallow", "hazelnut", "pumpkin",
    "spice", "chip", "chips", "fudge", "brownie", "milk", "dark", "white", "rich",
    "double", "gourmet", "vanilla bean", "punch", "icy", "blue", "green", "apple",
    "watermelon", "grape", "cherry", "tropical", "honey", "maple", "horchata",
    "snickerdoodle", "frosted", "glazed", "donut", "toffee", "pina", "colada",
    "flavor", "flavored", "flavour", "flavoured", "naturally", "ice", "iced",
    "sea", "salt", "roasted", "creamy", "smooth",
}

# Generic noise in product names (kept type words like whey/isolate/casein).
_NAME_NOISE = {
    "protein", "powder", "the", "with", "and", "premium", "grass", "fed",
    "grassfed", "pure", "100", "new", "improved", "value", "size", "pack",
    "tub", "bag", "bottle", "jug", "supplement",
}

# Tokens that denote size / count to strip from the core name.
_SIZE_RE = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:lbs?|pounds?|kgs?|kilograms?|oz|ounces?|g|grams?|"
    r"servings?|serving|count|ct|packets?|sticks?)\b",
    re.IGNORECASE,
)


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def normalize_brand(brand: str) -> str:
    raw = " ".join(re.sub(r"[^a-z0-9 ]+", " ", brand.lower()).split())
    return _BRAND_ALIASES.get(raw, raw)


def canonical_core_name(brand: str, name: str) -> str:
    text = name.lower()
    # Drop brand tokens (both the raw spelling and the canonical form) that
    # often prefix retailer product names, e.g. "ON ..." and "Optimum ...".
    raw_brand = re.sub(r"[^a-z0-9 ]+", " ", brand.lower())
    brand_tokens = set(normalize_brand(brand).split()) | set(raw_brand.split())
    for token in brand_tokens:
        text = re.sub(rf"\b{re.escape(token)}\b", " ", text)
    text = _SIZE_RE.sub(" ", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    tokens = [
        t for t in text.split()
        if t and t not in _FLAVOR_WORDS and t not in _NAME_NOISE
    ]
    return " ".join(tokens).strip()


def product_dedup_key(brand: str, name: str) -> str:
    """Stable key grouping the same product across sources (excludes size/flavor,
    which are variant attributes)."""
    core = canonical_core_name(brand, name) or slugify(name)
    return f"{slugify(normalize_brand(brand))}:{slugify(core)}"
