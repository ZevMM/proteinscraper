# protein-scraper

Discovery + extraction pipeline for protein powder listings. Writes directly to
the shared Postgres database (schema owned by `packages/db`).

## Pipeline

```
discover  -> connector finds candidate products (Shopify /products.json, ...)
extract   -> tiered: structured feed -> HTML parse -> LLM fallback (Claude Haiku)
normalize -> units to grams, prices to cents, flavor cleanup
validate  -> sanity checks + confidence; failures -> extraction_issues (not stored)
upsert    -> idempotent writes; append a price observation per run
```

## Usage

```bash
uv sync                       # install deps + the package (editable)

uv run scraper seed           # load seed sources into the DB
uv run scraper list-sources
uv run scraper run --source legion -v
uv run scraper run --all
```

Requires `DATABASE_URL` (see repo-root `.env`). Set `ANTHROPIC_API_KEY` to enable
the LLM nutrition fallback; without it, extraction uses structured + HTML parsing
only.

## Tests

```bash
uv run pytest            # unit + golden-fixture tests (no network, no DB)
uv run ruff check .
uv run mypy src
```

## Adding a source type

1. Implement a `Connector` subclass in `src/protein_scraper/connectors/`.
2. Register it in `connectors/__init__.py`.
3. Add entries to `seed_sources.yaml` with the matching `type`.
