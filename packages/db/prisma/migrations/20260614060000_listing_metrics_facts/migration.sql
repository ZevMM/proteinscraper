-- Add ingredient facts (ingredients_text + dietary_labels/allergens/sweeteners
-- arrays) to listing_metrics for faceted filtering.
-- Keep in sync with prisma/sql/listing_metrics.sql.

DROP VIEW IF EXISTS listing_metrics;
CREATE VIEW listing_metrics AS
WITH latest_price AS (
  SELECT DISTINCT ON (po."variantId")
    po."variantId"  AS variant_id,
    po."priceCents" AS price_cents,
    po."currency"   AS currency,
    po."inStock"    AS in_stock,
    po."capturedAt" AS captured_at
  FROM price_observations po
  ORDER BY po."variantId", po."capturedAt" DESC
)
SELECT
  v.id::text                AS variant_id,
  l.id::text                AS listing_id,
  p.id::text                AS product_id,
  s.id::text                AS source_id,
  s.slug                    AS source_slug,
  s.type::text              AS source_type,
  b.name                    AS brand_name,
  p.name                    AS product_name,
  p.category                AS category,
  v.flavor                  AS flavor,
  v."sizeG"                 AS size_g,
  l.url                     AS url,

  lp.price_cents            AS price_cents,
  lp.currency               AS currency,
  lp.in_stock               AS in_stock,
  lp.captured_at            AS captured_at,
  v."compareAtPriceCents"   AS compare_at_price_cents,

  n."servingSizeG"          AS serving_size_g,
  n."servingsPerContainer"  AS servings_per_container,
  n."proteinG"              AS protein_g,
  n."fatG"                  AS fat_g,
  n."carbG"                 AS carb_g,
  n."caloriesKcal"          AS calories_kcal,
  COALESCE(n.confidence, 0) AS confidence,

  f."ingredientsText"               AS ingredients_text,
  COALESCE(f."dietaryLabels", '{}') AS dietary_labels,
  COALESCE(f."allergens", '{}')     AS allergens,
  COALESCE(f."sweeteners", '{}')    AS sweeteners,

  (n."servingsPerContainer" * n."proteinG")                       AS total_protein_g,

  CASE WHEN lp.price_cents > 0
       THEN (n."servingsPerContainer" * n."proteinG") / (lp.price_cents / 100.0)
  END                                                             AS protein_per_dollar,

  CASE WHEN (n."servingsPerContainer" * n."proteinG") > 0
       THEN (lp.price_cents / 100.0) / ((n."servingsPerContainer" * n."proteinG") / 30.0)
  END                                                             AS cost_per_30g_protein,

  CASE WHEN n."servingSizeG" > 0
       THEN n."proteinG" / n."servingSizeG"
  END                                                             AS protein_pct_weight,

  CASE WHEN n."proteinG" > 0
       THEN n."fatG" / n."proteinG"
  END                                                             AS fat_per_protein,

  CASE WHEN n."proteinG" > 0
       THEN n."caloriesKcal" / n."proteinG"
  END                                                             AS calories_per_protein,

  CASE WHEN n."servingsPerContainer" > 0
       THEN (lp.price_cents / 100.0) / n."servingsPerContainer"
  END                                                             AS price_per_serving

FROM variants v
JOIN listings l        ON l.id = v."listingId"
JOIN products p        ON p.id = l."productId"
JOIN brands b          ON b.id = p."brandId"
JOIN sources s         ON s.id = l."sourceId"
JOIN latest_price lp        ON lp.variant_id = v.id
LEFT JOIN nutrition n       ON n."variantId" = v.id
LEFT JOIN ingredient_facts f ON f."variantId" = v.id;
