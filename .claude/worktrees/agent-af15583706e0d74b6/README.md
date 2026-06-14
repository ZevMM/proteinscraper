# ProteinScraper

A protein-powder price & nutrition **comparison site** backed by a recurring **scraping
pipeline** that discovers products across the web and extracts their attributes
(price, serving size, protein/fat/carbs/calories, servings per container), then keeps them
fresh daily.

Shoppers can filter and sort by **derived** metrics — e.g. *most protein per dollar*,
*least fat per gram of protein*, *cheapest per 30 g protein*.

## Monorepo layout

```
apps/web/          Next.js (App Router) frontend + read API
services/scraper/  Python pipeline: discover -> fetch -> extract -> normalize -> validate -> upsert
packages/db/       Prisma schema + migrations (single source of truth for the DB)
.github/workflows/ CI (lint/test) + scheduled daily scrape
```

One Postgres database is shared: the scraper **writes**, the web app **reads**.

## Architecture at a glance

- **Hybrid sourcing** — prefer official/structured data (Shopify `/products.json`,
  schema.org JSON-LD), fall back to polite HTML scraping, with an LLM (Claude Haiku 4.5)
  fallback only for fields still missing. Aggressive content-hash caching keeps cost ~0.
- **Accuracy guardrails** — every extracted record is validated (e.g.
  `calories ≈ 4·protein + 4·carb + 9·fat`) and scored; failures go to a review queue
  instead of polluting the catalog.
- **Derived metrics** are computed in a SQL view (`listing_metrics`), so new ratios are
  just new expressions — no re-scraping.
- **Near-zero hosting cost** — web on Vercel free tier, DB on Neon/Supabase free tier,
  scraper on GitHub Actions cron.

See `docs/` and the plan for the full design.

## Prerequisites

- Node ≥ 20 + [pnpm](https://pnpm.io) 11
- Python 3.12 + [uv](https://docs.astral.sh/uv/)
- Docker (for local Postgres)

## Quickstart (local dev)

```bash
cp .env.example .env

# 1. Start local Postgres
docker compose up -d db

# 2. Install JS deps and apply the DB schema
pnpm install
pnpm db:migrate          # creates tables + the listing_metrics view

# 3. Set up the scraper
cd services/scraper
uv sync
uv run scraper --help

# 4. Run the web app (in another terminal, from repo root)
pnpm dev                 # http://localhost:3000
```

## Running the pipeline

```bash
cd services/scraper
uv run scraper run --source <brand-slug>   # scrape one source
uv run scraper run --all                   # scrape every enabled source
```

## Tests

```bash
pnpm test            # JS/TS (web + db)
cd services/scraper && uv run pytest
```
