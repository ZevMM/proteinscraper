"""Pipeline orchestration: discover -> extract -> normalize -> validate -> upsert."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .config import Settings, get_settings
from .connectors import get_connector
from .db import Repository, create_engine
from .enrich.openfoodfacts import fetch_off_product, parse_off_product
from .extract.llm import LlmExtractor
from .http import Fetcher
from .models import ProductRecord
from .validation import validate_nutrition

logger = logging.getLogger(__name__)


@dataclass
class PipelineStats:
    sources: int = 0
    products: int = 0
    variants: int = 0
    prices: int = 0
    nutrition_ok: int = 0
    issues: int = 0
    errors: list[str] = field(default_factory=list)

    def merge(self, other: PipelineStats) -> None:
        self.sources += other.sources
        self.products += other.products
        self.variants += other.variants
        self.prices += other.prices
        self.nutrition_ok += other.nutrition_ok
        self.issues += other.issues
        self.errors.extend(other.errors)


def persist_product(repo: Repository, source_id: str, record: ProductRecord) -> PipelineStats:
    """Write one extracted product (and its variants/prices/nutrition) to the DB."""
    stats = PipelineStats()
    brand_id = repo.get_or_create_brand(record.brand_name)

    # Cross-source dedup: prefer merging onto an existing product that shares a
    # UPC; otherwise fall back to the canonical brand+name key.
    product_id: str | None = None
    for variant in record.variants:
        if variant.upc:
            product_id = repo.find_product_by_upc(variant.upc)
            if product_id:
                break
    if product_id is None:
        product_id = repo.get_or_create_product(
            brand_id=brand_id, brand_name=record.brand_name, name=record.product_name,
            category=record.category,
        )
    listing_id = repo.upsert_listing(
        source_id=source_id, product_id=product_id, url=record.url,
        source_sku=record.source_sku, title=record.title, raw_payload=record.raw_payload,
    )
    stats.products += 1

    for variant in record.variants:
        variant_id = repo.upsert_variant(listing_id=listing_id, variant=variant)
        repo.add_price_observation(
            variant_id=variant_id, price_cents=variant.price_cents,
            currency=variant.currency, in_stock=variant.in_stock,
        )
        stats.variants += 1
        stats.prices += 1

        if variant.nutrition is None:
            continue
        result = validate_nutrition(variant.nutrition, size_g=variant.size_g)
        if result.ok:
            repo.upsert_nutrition(
                variant_id=variant_id, n=variant.nutrition, confidence=result.confidence
            )
            stats.nutrition_ok += 1
            if result.warnings:
                repo.record_issue(
                    stage="validate", severity="warning", source_id=source_id,
                    listing_id=listing_id, url=record.url,
                    message="; ".join(result.warnings),
                    payload=variant.nutrition.model_dump(mode="json"),
                )
                stats.issues += 1
        else:
            repo.record_issue(
                stage="validate", severity="error", source_id=source_id,
                listing_id=listing_id, url=record.url,
                message="; ".join(result.errors),
                payload=variant.nutrition.model_dump(mode="json"),
            )
            stats.issues += 1

    return stats


async def run_source(
    repo: Repository, source: dict[str, Any], fetcher: Fetcher, llm: LlmExtractor | None
) -> PipelineStats:
    stats = PipelineStats(sources=1)
    source_id = str(source["id"])
    connector = get_connector(source, fetcher, llm)

    try:
        refs = await connector.discover()
    except Exception as exc:
        logger.exception("discover failed for %s", source["slug"])
        repo.record_issue(stage="fetch", source_id=source_id, message=f"discover failed: {exc}")
        stats.issues += 1
        stats.errors.append(f"{source['slug']}: discover failed: {exc}")
        return stats

    logger.info("source %s: %d candidate products", source["slug"], len(refs))
    for ref in refs:
        try:
            record = await connector.extract(ref)
        except Exception as exc:
            logger.warning("extract failed for a product in %s: %s", source["slug"], exc)
            repo.record_issue(stage="extract", source_id=source_id, message=str(exc))
            stats.issues += 1
            continue
        if record is None:
            continue
        try:
            stats.merge(persist_product(repo, source_id, record))
        except Exception as exc:
            logger.exception("persist failed for %s", record.url)
            repo.record_issue(
                stage="upsert", source_id=source_id, url=record.url, message=str(exc)
            )
            stats.issues += 1
    return stats


async def run(slugs: list[str] | None = None, settings: Settings | None = None) -> PipelineStats:
    """Run the pipeline for the given source slugs (or all enabled sources)."""
    settings = settings or get_settings()
    engine = create_engine(settings.database_url)
    repo = Repository(engine)
    llm = LlmExtractor(settings.anthropic_api_key) if settings.llm_enabled else None

    if slugs:
        sources = [s for slug in slugs if (s := repo.get_source(slug)) is not None]
    else:
        sources = repo.list_enabled_sources()

    overall = PipelineStats()
    async with Fetcher(settings) as fetcher:
        for source in sources:
            overall.merge(await run_source(repo, source, fetcher, llm))
    return overall


@dataclass
class EnrichStats:
    checked: int = 0
    enriched: int = 0
    issues: int = 0


async def enrich(settings: Settings | None = None) -> EnrichStats:
    """Fill missing nutrition for variants that have a UPC, via Open Food Facts."""
    settings = settings or get_settings()
    repo = Repository(create_engine(settings.database_url))
    stats = EnrichStats()
    rows = repo.variants_missing_nutrition_with_upc()
    logger.info("enrichment: %d variants with a UPC and no nutrition", len(rows))

    async with Fetcher(settings) as fetcher:
        for row in rows:
            stats.checked += 1
            variant_id, upc, size_g = str(row["id"]), row["upc"], row["sizeG"]
            try:
                product = await fetch_off_product(fetcher, upc)
            except Exception as exc:
                logger.warning("OFF fetch failed for %s: %s", upc, exc)
                continue
            if product is None:
                continue
            record = parse_off_product(product, size_g)
            if record is None:
                continue
            result = validate_nutrition(record, size_g=size_g)
            if result.ok:
                repo.upsert_nutrition(
                    variant_id=variant_id, n=record, confidence=result.confidence
                )
                stats.enriched += 1
            else:
                repo.record_issue(
                    stage="validate", severity="warning",
                    message="OFF enrichment: " + "; ".join(result.errors),
                    payload=record.model_dump(mode="json"),
                )
                stats.issues += 1
    return stats
