import { prisma, type ListingMetrics, type Prisma } from "@proteinscraper/db";

import { DEFAULT_METRIC, METRICS, isMetricKey, type MetricKey } from "./metrics";

export interface Filters {
  q?: string;
  brand?: string;
  source?: string;
  inStockOnly: boolean;
  maxPriceCents?: number;
  minProtein?: number;
  metric: MetricKey;
  /** "best" = sort so the most desirable values come first. */
  order: "best" | "worst";
}

type RawParams = Record<string, string | string[] | undefined>;

function first(value: string | string[] | undefined): string | undefined {
  const v = Array.isArray(value) ? value[0] : value;
  return v && v.length > 0 ? v : undefined;
}

export function parseFilters(params: RawParams): Filters {
  const metricParam = first(params.metric);
  const maxPrice = first(params.maxPrice);
  const minProtein = first(params.minProtein);
  return {
    q: first(params.q),
    brand: first(params.brand),
    source: first(params.source),
    inStockOnly: first(params.inStock) === "1",
    maxPriceCents: maxPrice ? Math.round(Number(maxPrice) * 100) : undefined,
    minProtein: minProtein ? Number(minProtein) : undefined,
    metric: isMetricKey(metricParam) ? metricParam : DEFAULT_METRIC,
    order: first(params.order) === "worst" ? "worst" : "best",
  };
}

export function buildQuery(filters: Filters): {
  where: Prisma.ListingMetricsWhereInput;
  orderBy: Prisma.ListingMetricsOrderByWithRelationInput[];
} {
  const metric = METRICS[filters.metric];
  const where: Prisma.ListingMetricsWhereInput = {};

  if (filters.inStockOnly) where.inStock = true;
  if (filters.brand) where.brandName = filters.brand;
  if (filters.source) where.sourceSlug = filters.source;
  if (filters.minProtein != null) where.proteinG = { gte: filters.minProtein };
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
