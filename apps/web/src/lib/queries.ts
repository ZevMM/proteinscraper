import { prisma, type ListingMetrics, type Prisma } from "@proteinscraper/db";

import { ARTIFICIAL_SWEETENERS } from "./facets";
import { DEFAULT_METRIC, METRICS, isMetricKey, type MetricKey } from "./metrics";

export interface Filters {
  q?: string;
  brands: string[];
  sources: string[];
  inStockOnly: boolean;
  maxPriceCents?: number;
  metric: MetricKey;
  /** "best" = sort so the most desirable values come first. */
  order: "best" | "worst";
  /** "grouped" = one row per product (best offer); "all" = every offer. */
  view: "grouped" | "all";
  /** Require all of these dietary/certification labels. */
  dietary: string[];
  /** Exclude products containing any of these allergens. */
  allergenFree: string[];
  /** Exclude products with artificial sweeteners. */
  noArtificial: boolean;
}

type RawParams = Record<string, string | string[] | undefined>;

function first(value: string | string[] | undefined): string | undefined {
  const v = Array.isArray(value) ? value[0] : value;
  return v && v.length > 0 ? v : undefined;
}

function all(value: string | string[] | undefined): string[] {
  if (value == null) return [];
  return (Array.isArray(value) ? value : [value]).filter((v) => v.length > 0);
}

export function parseFilters(params: RawParams): Filters {
  const metricParam = first(params.metric);
  const maxPrice = first(params.maxPrice);
  return {
    q: first(params.q),
    brands: all(params.brand),
    sources: all(params.source),
    inStockOnly: first(params.inStock) === "1",
    maxPriceCents: maxPrice ? Math.round(Number(maxPrice) * 100) : undefined,
    metric: isMetricKey(metricParam) ? metricParam : DEFAULT_METRIC,
    order: first(params.order) === "worst" ? "worst" : "best",
    // Always one row per product; the "all offers" view was removed from the UI.
    view: "grouped",
    dietary: all(params.dietary),
    allergenFree: all(params.allergenFree),
    noArtificial: first(params.noArtificial) === "1",
  };
}

export function buildQuery(filters: Filters): {
  where: Prisma.ListingMetricsWhereInput;
  orderBy: Prisma.ListingMetricsOrderByWithRelationInput[];
} {
  const metric = METRICS[filters.metric];
  const where: Prisma.ListingMetricsWhereInput = {};

  if (filters.inStockOnly) where.inStock = true;
  if (filters.brands.length) where.brandName = { in: filters.brands };
  if (filters.sources.length) where.sourceSlug = { in: filters.sources };
  if (filters.maxPriceCents != null) where.priceCents = { lte: filters.maxPriceCents };
  if (filters.q) {
    where.OR = [
      { productName: { contains: filters.q, mode: "insensitive" } },
      { brandName: { contains: filters.q, mode: "insensitive" } },
    ];
  }
  // Only rank rows that actually have the metric value.
  if (metric.requiresNutrition) {
    where[metric.field as "proteinPerDollar"] = { not: null };
  }

  if (filters.dietary.length) where.dietaryLabels = { hasEvery: filters.dietary };
  const exclude: Prisma.ListingMetricsWhereInput[] = [];
  if (filters.allergenFree.length) exclude.push({ allergens: { hasSome: filters.allergenFree } });
  if (filters.noArtificial) exclude.push({ sweeteners: { hasSome: ARTIFICIAL_SWEETENERS } });
  if (exclude.length) where.NOT = exclude;

  // "best" first => descending when higher is better, ascending otherwise.
  const descending = filters.order === "best" ? metric.higherIsBetter : !metric.higherIsBetter;
  const sort: Prisma.SortOrder = descending ? "desc" : "asc";

  const primary = (
    metric.requiresNutrition
      ? { [metric.field]: { sort, nulls: "last" } }
      : { [metric.field]: sort }
  ) as Prisma.ListingMetricsOrderByWithRelationInput;

  return { where, orderBy: [primary, { priceCents: "asc" }, { variantId: "asc" }] };
}

export async function getListings(filters: Filters, take = 200): Promise<ListingMetrics[]> {
  const { where, orderBy } = buildQuery(filters);
  return prisma.listingMetrics.findMany({ where, orderBy, take });
}

export type GroupedListing = ListingMetrics & {
  retailerCount: number;
  offerCount: number;
};

export interface PagedListings {
  rows: GroupedListing[];
  /** Total number of distinct products matching the filters (across all pages). */
  total: number;
}

/**
 * One row per product: its best offer for the selected metric, plus how many
 * retailers/offers carry it. Rows come back already sorted best-first, so the
 * first time a product is seen is its best offer (and products stay best-first).
 *
 * Grouping happens in-app over the full matching set, so `total` is the true
 * product count and the returned `rows` are the requested page of that set.
 */
export async function getGroupedListings(
  filters: Filters,
  page = 1,
  pageSize = 50,
): Promise<PagedListings> {
  const { where, orderBy } = buildQuery(filters);
  const rows = await prisma.listingMetrics.findMany({ where, orderBy });

  const byProduct = new Map<string, { best: ListingMetrics; retailers: Set<string>; offers: number }>();
  for (const row of rows) {
    const existing = byProduct.get(row.productId);
    if (!existing) {
      byProduct.set(row.productId, {
        best: row,
        retailers: new Set([row.sourceSlug]),
        offers: 1,
      });
    } else {
      existing.retailers.add(row.sourceSlug);
      existing.offers += 1;
    }
  }

  const grouped = [...byProduct.values()].map((g) => ({
    ...g.best,
    retailerCount: g.retailers.size,
    offerCount: g.offers,
  }));
  const start = (page - 1) * pageSize;
  return { rows: grouped.slice(start, start + pageSize), total: grouped.length };
}

export interface Facets {
  brands: string[];
  sources: string[];
}

export async function getFacets(): Promise<Facets> {
  const [brands, sources] = await Promise.all([
    prisma.listingMetrics.findMany({
      distinct: ["brandName"],
      select: { brandName: true },
      orderBy: { brandName: "asc" },
    }),
    prisma.listingMetrics.findMany({
      distinct: ["sourceSlug"],
      select: { sourceSlug: true },
      orderBy: { sourceSlug: "asc" },
    }),
  ]);
  return {
    brands: brands.map((b) => b.brandName),
    sources: sources.map((s) => s.sourceSlug),
  };
}

export async function getProductDetail(productId: string) {
  const rows = await prisma.listingMetrics.findMany({
    where: { productId },
    orderBy: { proteinPerDollar: { sort: "desc", nulls: "last" } },
  });
  if (rows.length === 0) return null;

  // Price history across this product's variants.
  const variantIds = rows.map((r) => r.variantId);
  const history = await prisma.priceObservation.findMany({
    where: { variantId: { in: variantIds } },
    orderBy: { capturedAt: "asc" },
    select: { priceCents: true, capturedAt: true },
  });

  return { rows, history };
}
