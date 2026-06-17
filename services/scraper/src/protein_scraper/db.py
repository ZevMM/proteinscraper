"""Database access for the scraper (writes directly to the Prisma-managed schema).

Uses SQLAlchemy Core with Postgres ``INSERT ... ON CONFLICT`` for idempotent
upserts, so a daily run updates existing rows and appends new price observations
without creating duplicates.

Note: Prisma's ``@updatedAt`` is applied client-side, so those columns have no DB
default — every write here sets ``updatedAt`` explicitly.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, JSONB, UUID
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine

from .identity import normalize_brand, product_dedup_key, slugify
from .models import IngredientFactsRecord, NutritionRecord, VariantRecord

__all__ = ["Repository", "create_engine", "slugify", "to_sqlalchemy_url"]

metadata = sa.MetaData()

_source_type = ENUM(
    "shopify", "jsonld", "walmart", "amazon", "kroger", "ebay",
    name="SourceType", create_type=False,
)
_market = ENUM("US", "UK", "IN", name="Market", create_type=False)
_extraction_method = ENUM(
    "shopify_json", "json_ld", "html_parse", "llm", "manual",
    name="ExtractionMethod", create_type=False,
)
_issue_stage = ENUM(
    "fetch", "extract", "normalize", "validate", "upsert", name="IssueStage", create_type=False
)
_issue_severity = ENUM("warning", "error", name="IssueSeverity", create_type=False)

sources = sa.Table(
    "sources", metadata,
    sa.Column("id", UUID(as_uuid=False), primary_key=True,
              server_default=sa.text("gen_random_uuid()")),
    sa.Column("slug", sa.Text, nullable=False),
    sa.Column("name", sa.Text, nullable=False),
    sa.Column("type", _source_type, nullable=False),
    sa.Column("market", _market, nullable=False),
    sa.Column("baseUrl", sa.Text, nullable=False),
    sa.Column("enabled", sa.Boolean, nullable=False),
    sa.Column("config", JSONB),
    sa.Column("updatedAt", sa.DateTime, nullable=False),
)

brands = sa.Table(
    "brands", metadata,
    sa.Column("id", UUID(as_uuid=False), primary_key=True,
              server_default=sa.text("gen_random_uuid()")),
    sa.Column("slug", sa.Text, nullable=False),
    sa.Column("name", sa.Text, nullable=False),
    sa.Column("website", sa.Text),
    sa.Column("updatedAt", sa.DateTime, nullable=False),
)

products = sa.Table(
    "products", metadata,
    sa.Column("id", UUID(as_uuid=False), primary_key=True,
              server_default=sa.text("gen_random_uuid()")),
    sa.Column("brandId", UUID(as_uuid=False), nullable=False),
    sa.Column("name", sa.Text, nullable=False),
    sa.Column("category", sa.Text),
    sa.Column("dedupKey", sa.Text),
    sa.Column("updatedAt", sa.DateTime, nullable=False),
)

listings = sa.Table(
    "listings", metadata,
    sa.Column("id", UUID(as_uuid=False), primary_key=True,
              server_default=sa.text("gen_random_uuid()")),
    sa.Column("sourceId", UUID(as_uuid=False), nullable=False),
    sa.Column("productId", UUID(as_uuid=False), nullable=False),
    sa.Column("url", sa.Text, nullable=False),
    sa.Column("sourceSku", sa.Text, nullable=False),
    sa.Column("title", sa.Text, nullable=False),
    sa.Column("rawPayload", JSONB),
    sa.Column("lastSeenAt", sa.DateTime, nullable=False),
)

variants = sa.Table(
    "variants", metadata,
    sa.Column("id", UUID(as_uuid=False), primary_key=True,
              server_default=sa.text("gen_random_uuid()")),
    sa.Column("listingId", UUID(as_uuid=False), nullable=False),
    sa.Column("flavor", sa.Text),
    sa.Column("sizeG", sa.Float),
    sa.Column("sizeLabel", sa.Text),
    sa.Column("sourceVariantId", sa.Text, nullable=False),
    sa.Column("upc", sa.Text),
    sa.Column("compareAtPriceCents", sa.Integer),
)

nutrition = sa.Table(
    "nutrition", metadata,
    sa.Column("id", UUID(as_uuid=False), primary_key=True,
              server_default=sa.text("gen_random_uuid()")),
    sa.Column("variantId", UUID(as_uuid=False), nullable=False),
    sa.Column("servingSizeG", sa.Float),
    sa.Column("servingsPerContainer", sa.Float),
    sa.Column("proteinG", sa.Float),
    sa.Column("fatG", sa.Float),
    sa.Column("carbG", sa.Float),
    sa.Column("sugarG", sa.Float),
    sa.Column("caloriesKcal", sa.Float),
    sa.Column("confidence", sa.Float, nullable=False),
    sa.Column("extractionMethod", _extraction_method, nullable=False),
    sa.Column("updatedAt", sa.DateTime, nullable=False),
)

ingredient_facts = sa.Table(
    "ingredient_facts", metadata,
    sa.Column("id", UUID(as_uuid=False), primary_key=True,
              server_default=sa.text("gen_random_uuid()")),
    sa.Column("variantId", UUID(as_uuid=False), nullable=False),
    sa.Column("ingredientsText", sa.Text),
    sa.Column("dietaryLabels", ARRAY(sa.Text), nullable=False),
    sa.Column("allergens", ARRAY(sa.Text), nullable=False),
    sa.Column("sweeteners", ARRAY(sa.Text), nullable=False),
    sa.Column("updatedAt", sa.DateTime, nullable=False),
)

price_observations = sa.Table(
    "price_observations", metadata,
    sa.Column("id", UUID(as_uuid=False), primary_key=True,
              server_default=sa.text("gen_random_uuid()")),
    sa.Column("variantId", UUID(as_uuid=False), nullable=False),
    sa.Column("priceCents", sa.Integer, nullable=False),
    sa.Column("currency", sa.Text, nullable=False),
    sa.Column("inStock", sa.Boolean, nullable=False),
)

extraction_issues = sa.Table(
    "extraction_issues", metadata,
    sa.Column("id", UUID(as_uuid=False), primary_key=True,
              server_default=sa.text("gen_random_uuid()")),
    sa.Column("sourceId", UUID(as_uuid=False)),
    sa.Column("listingId", UUID(as_uuid=False)),
    sa.Column("url", sa.Text),
    sa.Column("stage", _issue_stage, nullable=False),
    sa.Column("severity", _issue_severity, nullable=False),
    sa.Column("message", sa.Text, nullable=False),
    sa.Column("payload", JSONB),
)


def _utcnow() -> datetime:
    """Naive UTC timestamp matching Prisma's TIMESTAMP(3) columns."""
    return datetime.now(UTC).replace(tzinfo=None)


def to_sqlalchemy_url(database_url: str) -> str:
    """Convert a Prisma-style URL to a psycopg3 SQLAlchemy URL.

    Switches the driver to ``postgresql+psycopg`` and drops Prisma-only query
    params (e.g. ``schema``) that libpq does not understand.
    """
    parts = urlsplit(database_url)
    scheme = parts.scheme
    if scheme in ("postgres", "postgresql"):
        scheme = "postgresql+psycopg"
    query = [(k, v) for k, v in parse_qsl(parts.query) if k != "schema"]
    return urlunsplit((scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def create_engine(database_url: str) -> Engine:
    return sa.create_engine(to_sqlalchemy_url(database_url), future=True, pool_pre_ping=True)


class Repository:
    """Idempotent writer for the catalog tables."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    # -- Sources -----------------------------------------------------------
    def upsert_source(
        self, *, slug: str, name: str, type_: str, base_url: str, enabled: bool = True,
        market: str = "US", config: dict[str, Any] | None = None,
    ) -> str:
        stmt = (
            pg_insert(sources)
            .values(
                slug=slug, name=name, type=type_, market=market, baseUrl=base_url,
                enabled=enabled, config=config, updatedAt=_utcnow(),
            )
            .on_conflict_do_update(
                index_elements=[sources.c.slug],
                set_={"name": name, "baseUrl": base_url, "enabled": enabled,
                      "market": market, "config": config, "updatedAt": _utcnow()},
            )
            .returning(sources.c.id)
        )
        with self.engine.begin() as conn:
            return str(conn.execute(stmt).scalar_one())

    def get_source(self, slug: str) -> dict[str, Any] | None:
        stmt = sa.select(sources.c.id, sources.c.slug, sources.c.type, sources.c.baseUrl,
                         sources.c.config, sources.c.enabled).where(sources.c.slug == slug)
        with self.engine.connect() as conn:
            row = conn.execute(stmt).mappings().first()
        return dict(row) if row else None

    def list_enabled_sources(self) -> list[dict[str, Any]]:
        stmt = sa.select(sources.c.id, sources.c.slug, sources.c.type, sources.c.baseUrl,
                         sources.c.config).where(sources.c.enabled.is_(True))
        with self.engine.connect() as conn:
            return [dict(r) for r in conn.execute(stmt).mappings().all()]

    # -- Catalog upserts ---------------------------------------------------
    def get_or_create_brand(self, name: str) -> str:
        # Normalize so the same brand across sources (e.g. "ON" vs "Optimum
        # Nutrition") collapses to one row.
        slug = slugify(normalize_brand(name))
        stmt = (
            pg_insert(brands)
            .values(slug=slug, name=name, updatedAt=_utcnow())
            .on_conflict_do_update(
                index_elements=[brands.c.slug],
                set_={"name": name, "updatedAt": _utcnow()},
            )
            .returning(brands.c.id)
        )
        with self.engine.begin() as conn:
            return str(conn.execute(stmt).scalar_one())

    def get_or_create_product(
        self, *, brand_id: str, brand_name: str, name: str, category: str | None
    ) -> str:
        dedup_key = product_dedup_key(brand_name, name)
        stmt = (
            pg_insert(products)
            .values(brandId=brand_id, name=name, category=category,
                    dedupKey=dedup_key, updatedAt=_utcnow())
            .on_conflict_do_update(
                index_elements=[products.c.dedupKey],
                set_={"name": name, "category": category, "updatedAt": _utcnow()},
            )
            .returning(products.c.id)
        )
        with self.engine.begin() as conn:
            return str(conn.execute(stmt).scalar_one())

    def upsert_listing(
        self, *, source_id: str, product_id: str, url: str, source_sku: str,
        title: str, raw_payload: dict[str, Any] | None,
    ) -> str:
        stmt = (
            pg_insert(listings)
            .values(sourceId=source_id, productId=product_id, url=url, sourceSku=source_sku,
                    title=title, rawPayload=raw_payload, lastSeenAt=_utcnow())
            .on_conflict_do_update(
                index_elements=[listings.c.sourceId, listings.c.sourceSku],
                set_={"url": url, "title": title, "rawPayload": raw_payload,
                      "productId": product_id, "lastSeenAt": _utcnow()},
            )
            .returning(listings.c.id)
        )
        with self.engine.begin() as conn:
            return str(conn.execute(stmt).scalar_one())

    def upsert_variant(self, *, listing_id: str, variant: VariantRecord) -> str:
        values = {
            "listingId": listing_id,
            "flavor": variant.flavor,
            "sizeG": variant.size_g,
            "sizeLabel": variant.size_label,
            "sourceVariantId": variant.source_variant_id,
            "upc": variant.upc,
            "compareAtPriceCents": variant.compare_at_price_cents,
        }
        update = {k: v for k, v in values.items() if k not in ("listingId", "sourceVariantId")}
        stmt = (
            pg_insert(variants)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[variants.c.listingId, variants.c.sourceVariantId],
                set_=update,
            )
            .returning(variants.c.id)
        )
        with self.engine.begin() as conn:
            return str(conn.execute(stmt).scalar_one())

    def find_product_by_upc(self, upc: str) -> str | None:
        """Return the product id of an existing variant with this UPC, if any.

        Lets the pipeline merge the same product across sources by barcode.
        """
        stmt = (
            sa.select(listings.c.productId)
            .select_from(variants.join(listings, listings.c.id == variants.c.listingId))
            .where(variants.c.upc == upc)
            .limit(1)
        )
        with self.engine.connect() as conn:
            result = conn.execute(stmt).scalar_one_or_none()
        return str(result) if result else None

    def variants_missing_nutrition_with_upc(self, limit: int = 1000) -> list[dict[str, Any]]:
        """Variants that have a UPC but no nutrition row yet — candidates for
        Open Food Facts enrichment."""
        stmt = (
            sa.select(variants.c.id, variants.c.upc, variants.c.sizeG)
            .select_from(variants.outerjoin(nutrition, nutrition.c.variantId == variants.c.id))
            .where(variants.c.upc.isnot(None), nutrition.c.id.is_(None))
            .limit(limit)
        )
        with self.engine.connect() as conn:
            return [dict(r) for r in conn.execute(stmt).mappings().all()]

    def upsert_nutrition(self, *, variant_id: str, n: NutritionRecord, confidence: float) -> None:
        values = {
            "variantId": variant_id,
            "servingSizeG": n.serving_size_g,
            "servingsPerContainer": n.servings_per_container,
            "proteinG": n.protein_g,
            "fatG": n.fat_g,
            "carbG": n.carb_g,
            "sugarG": n.sugar_g,
            "caloriesKcal": n.calories_kcal,
            "confidence": confidence,
            "extractionMethod": n.extraction_method.value,
            "updatedAt": _utcnow(),
        }
        update = {k: v for k, v in values.items() if k != "variantId"}
        stmt = (
            pg_insert(nutrition)
            .values(**values)
            .on_conflict_do_update(index_elements=[nutrition.c.variantId], set_=update)
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)

    def upsert_facts(self, *, variant_id: str, facts: IngredientFactsRecord) -> None:
        values = {
            "variantId": variant_id,
            "ingredientsText": facts.ingredients_text,
            "dietaryLabels": facts.dietary_labels,
            "allergens": facts.allergens,
            "sweeteners": facts.sweeteners,
            "updatedAt": _utcnow(),
        }
        update = {k: v for k, v in values.items() if k != "variantId"}
        stmt = (
            pg_insert(ingredient_facts)
            .values(**values)
            .on_conflict_do_update(index_elements=[ingredient_facts.c.variantId], set_=update)
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)

    def variants_missing_facts_with_upc(self, limit: int = 1000) -> list[dict[str, Any]]:
        """Variants with a UPC but no ingredient facts yet — OFF enrichment candidates."""
        stmt = (
            sa.select(variants.c.id, variants.c.upc)
            .select_from(
                variants.outerjoin(
                    ingredient_facts, ingredient_facts.c.variantId == variants.c.id
                )
            )
            .where(variants.c.upc.isnot(None), ingredient_facts.c.id.is_(None))
            .limit(limit)
        )
        with self.engine.connect() as conn:
            return [dict(r) for r in conn.execute(stmt).mappings().all()]

    def add_price_observation(
        self, *, variant_id: str, price_cents: int, currency: str, in_stock: bool
    ) -> None:
        stmt = pg_insert(price_observations).values(
            variantId=variant_id, priceCents=price_cents, currency=currency, inStock=in_stock
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)

    def record_issue(
        self, *, stage: str, message: str, severity: str = "error",
        source_id: str | None = None, listing_id: str | None = None,
        url: str | None = None, payload: dict[str, Any] | None = None,
    ) -> None:
        stmt = pg_insert(extraction_issues).values(
            sourceId=source_id, listingId=listing_id, url=url, stage=stage,
            severity=severity, message=message, payload=payload,
        )
        with self.engine.begin() as conn:
            conn.execute(stmt)
