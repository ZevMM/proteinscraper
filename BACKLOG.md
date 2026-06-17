# Backlog / eventual to-dos

Deferred work and "revisit when…" notes. Not blocking; captured so they aren't lost.

## Performance / scale

- **Push grouped-by-product dedup into SQL.** `getGroupedListings`
  ([apps/web/src/lib/queries.ts](apps/web/src/lib/queries.ts)) currently fetches the
  *full* matching set of offers and dedups to one best offer per product in app code,
  so pagination + the total count are accurate. Cheap at the current scale (hundreds of
  products / low-thousands of offers). **Revisit when the catalog reaches tens of
  thousands of offers** — at that point move the dedup (DISTINCT ON product, best offer
  per the active metric) into the `listing_metrics` query / a SQL window function and
  paginate with LIMIT/OFFSET instead of loading every row.

## Data quality / enrichment

- **OFF rate-limiting.** Open Food Facts enrichment hits HTTP 429s during the enrich
  pass (it still completes via retries). If facts/nutrition coverage looks thin, add a
  small delay / backoff between OFF requests in the enrich loop
  ([services/scraper/src/protein_scraper/pipeline.py](services/scraper/src/protein_scraper/pipeline.py)).
- **Nutrition for marketplace items (eBay/Walmart marketplace).** eBay carries no
  nutrition; it relies on OFF-by-UPC, and OFF coverage for supplement barcodes is sparse.
  Better lever: match marketplace UPCs against nutrition already sourced from retailer
  connectors (cross-source dedup) rather than depending on OFF.
- **Cross-source product dedup / entity resolution (M4).** Collapse the same physical
  product sold by multiple retailers into one `Product` with multiple `Listing`s. Would
  also feed the nutrition-reuse idea above.

## Connectors / sources

- **Amazon RapidAPI quota blocks Amazon UK/IN.** The "Real-Time Amazon Data" plan is
  capped at 100 requests/month and is currently exhausted (HTTP 429, ~monthly reset), so
  `amazon` (US) can't refresh and `amazon-uk` can't populate. To enable Amazon for any
  market, upgrade the RapidAPI plan (raises the request cap). Until then Amazon markets
  stay empty/stale; eBay (free Browse API) is the working multi-market source.
- **eBay account-deletion endpoint.** Production Browse access is granted (the portal
  requirement is satisfied via exemption or otherwise). *If* eBay ever flags the
  marketplace-account-deletion notification as pending, build the webhook as a Next.js
  route handler on Vercel (GET challenge-code validation + POST deletion handler).
- **eBay brand/dedup hardening.** eBay summaries have no real brand field (brand defaults
  to "Unknown"); titles are noisy. Improve brand extraction + dedup before relying on
  eBay rows for grouping.
- **Kroger product URLs.** Built from `slugify(name) + product_id`; couldn't be
  auto-verified (bot-blocked). The Kroger payload has a `productPageURI` field that could
  be used directly instead.
- **Rotate the Walmart API key** (shared in chat during setup).

## Infra

- **GitHub Actions Node 20 deprecation.** `actions/checkout@v4`, `actions/setup-node@v4`,
  `astral-sh/setup-uv@v5`, `pnpm/action-setup@v4` run on Node 20, which is being forced to
  Node 24 (June 16 2026) and removed (Sept 16 2026). Bump action versions before then, or
  set `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true`.
