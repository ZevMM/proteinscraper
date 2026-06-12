/**
 * Registry of the comparison metrics users can sort by. Each maps to a column
 * on the `listing_metrics` view (Prisma model `ListingMetrics`).
 */
import type { Prisma } from "@proteinscraper/db";

export type MetricKey =
  | "proteinPerDollar"
  | "costPer30gProtein"
  | "pricePerServing"
  | "proteinPctWeight"
  | "fatPerProtein"
  | "caloriesPerProtein"
  | "totalProteinG"
  | "priceCents";

export interface MetricDef {
  key: MetricKey;
  /** Prisma orderBy field on ListingMetrics. */
  field: keyof Prisma.ListingMetricsOrderByWithRelationInput;
  label: string;
  /** Whether a higher value is "better" (drives the default sort direction). */
  higherIsBetter: boolean;
  /** Most sort metrics only make sense once nutrition is known. */
  requiresNutrition: boolean;
  format: (value: number | null) => string;
}

const money = (v: number | null) => (v == null ? "—" : `$${v.toFixed(2)}`);
const num = (digits: number) => (v: number | null) =>
  v == null ? "—" : v.toFixed(digits);

export const METRICS: Record<MetricKey, MetricDef> = {
  proteinPerDollar: {
    key: "proteinPerDollar",
    field: "proteinPerDollar",
    label: "Protein per dollar",
    higherIsBetter: true,
    requiresNutrition: true,
    format: (v) => (v == null ? "—" : `${v.toFixed(1)} g/$`),
  },
  costPer30gProtein: {
    key: "costPer30gProtein",
    field: "costPer30gProtein",
    label: "Cost per 30g protein",
    higherIsBetter: false,
    requiresNutrition: true,
    format: money,
  },
  pricePerServing: {
    key: "pricePerServing",
    field: "pricePerServing",
    label: "Price per serving",
    higherIsBetter: false,
    requiresNutrition: true,
    format: money,
  },
  proteinPctWeight: {
    key: "proteinPctWeight",
    field: "proteinPctWeight",
    label: "Protein % by weight",
    higherIsBetter: true,
    requiresNutrition: true,
    format: (v) => (v == null ? "—" : `${(v * 100).toFixed(0)}%`),
  },
  fatPerProtein: {
    key: "fatPerProtein",
    field: "fatPerProtein",
    label: "Fat per gram protein",
    higherIsBetter: false,
    requiresNutrition: true,
    format: num(2),
  },
  caloriesPerProtein: {
    key: "caloriesPerProtein",
    field: "caloriesPerProtein",
    label: "Calories per gram protein",
    higherIsBetter: false,
    requiresNutrition: true,
    format: num(1),
  },
  totalProteinG: {
    key: "totalProteinG",
    field: "totalProteinG",
    label: "Total protein per tub",
    higherIsBetter: true,
    requiresNutrition: true,
    format: (v) => (v == null ? "—" : `${v.toFixed(0)} g`),
  },
  priceCents: {
    key: "priceCents",
    field: "priceCents",
    label: "Price",
    higherIsBetter: false,
    requiresNutrition: false,
    format: (v) => (v == null ? "—" : `$${(v / 100).toFixed(2)}`),
  },
};

export const METRIC_LIST = Object.values(METRICS);
export const DEFAULT_METRIC: MetricKey = "proteinPerDollar";

export function isMetricKey(value: string | undefined): value is MetricKey {
  return value != null && value in METRICS;
}
