import Link from "next/link";

import { FilterBar } from "@/components/Filters";
import { formatPrice, formatSize, salePercent } from "@/lib/format";
import { METRICS, type MetricKey } from "@/lib/metrics";
import {
  getFacets,
  getGroupedListings,
  getListings,
  parseFilters,
  type GroupedListing,
} from "@/lib/queries";

// Always reflect the latest scraped prices.
export const dynamic = "force-dynamic";

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const filters = parseFilters(await searchParams);
  const grouped = filters.view === "grouped";
  const [rows, facets] = await Promise.all([
    grouped ? getGroupedListings(filters) : getListings(filters),
    getFacets(),
  ]);
  const activeMetric = METRICS[filters.metric];
  // Metrics that already have a dedicated column in the table. Sorting by one of
  // these just highlights that column instead of adding a duplicate; any other
  // metric gets an extra column inserted right after "Best price".
  const FIXED_COLUMN_METRICS = new Set<MetricKey>([
    "priceCents",
    "proteinPerDollar",
    "costPer30gProtein",
  ]);
  const showExtraColumn = !FIXED_COLUMN_METRICS.has(filters.metric);
  const isSort = (key: MetricKey) => filters.metric === key;
  const thSort = (key: MetricKey) =>
    isSort(key)
      ? "border-b-2 border-brand-500 bg-neutral-100 px-3 py-2 text-right font-semibold text-neutral-800"
      : "px-3 py-2 text-right";
  const tdSort = (key: MetricKey) =>
    isSort(key)
      ? "bg-neutral-50 px-3 py-2 text-right font-semibold text-neutral-900"
      : "px-3 py-2 text-right text-neutral-600";

  return (
    <div className="flex flex-col gap-5">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Compare protein powders</h1>
        <p className="text-sm text-neutral-500">
          {grouped ? "One row per product, " : "Every offer, "}ranked by{" "}
          <span className="font-medium text-neutral-700">{activeMetric.label}</span>,{" "}
          {filters.order === "best" ? "best" : "worst"} first.
        </p>
      </div>

      <FilterBar filters={filters} facets={facets} />

      <p className="text-sm text-neutral-500">{rows.length} results</p>

      {rows.length === 0 ? (
        <div className="rounded-lg border border-dashed border-neutral-300 p-10 text-center text-neutral-500">
          No matching products. Try widening your filters.
        </div>
      ) : (
        <>
          {/* Desktop Table View */}
          <div className="hidden overflow-x-auto rounded-lg border border-neutral-200 bg-white md:block">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-neutral-200 bg-neutral-50 text-left text-xs uppercase tracking-wide text-neutral-500">
                  <th className="px-3 py-2">#</th>
                  <th className="px-3 py-2">Product</th>
                  <th className="px-3 py-2">Retailers</th>
                  <th className="px-3 py-2 text-right">Size</th>
                  <th className={thSort("priceCents")}>Best price</th>
                  {showExtraColumn ? (
                    <th className="border-b-2 border-brand-500 bg-neutral-100 px-3 py-2 text-right font-semibold text-neutral-800">
                      {activeMetric.label}
                    </th>
                  ) : null}
                  <th className="px-3 py-2 text-right">Protein/serv</th>
                  <th className={thSort("proteinPerDollar")}>Protein/$</th>
                  <th className={thSort("costPer30gProtein")}>$/30g protein</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => {
                  const off = salePercent(r.priceCents, r.compareAtPriceCents);
                  const retailerCount = (r as GroupedListing).retailerCount;
                  return (
                    <tr
                      key={r.variantId}
                      className="border-b border-neutral-100 last:border-0 hover:bg-neutral-50"
                    >
                      <td className="px-3 py-2 text-neutral-400">{i + 1}</td>
                      <td className="px-3 py-2">
                        <Link
                          href={`/product/${r.productId}`}
                          className="font-medium text-neutral-900 hover:text-brand-700 hover:underline"
                        >
                          {r.productName}
                        </Link>
                        <div className="text-xs text-neutral-500">
                          {r.brandName}
                          {r.flavor ? ` · ${r.flavor}` : ""}
                          {!r.inStock ? " · out of stock" : ""}
                        </div>
                      </td>
                      <td className="px-3 py-2 text-neutral-600">
                        {grouped ? (
                          <span title={`${(r as GroupedListing).offerCount} offers`}>
                            {r.sourceSlug}
                            {retailerCount > 1 ? (
                              <span className="ml-1 rounded bg-neutral-100 px-1.5 py-0.5 text-xs text-neutral-600">
                                +{retailerCount - 1} more
                              </span>
                            ) : null}
                          </span>
                        ) : (
                          r.sourceSlug
                        )}
                      </td>
                      <td className="px-3 py-2 text-right text-neutral-600">
                        {formatSize(r.sizeG)}
                      </td>
                      <td
                        className={
                          isSort("priceCents")
                            ? "bg-neutral-50 px-3 py-2 text-right"
                            : "px-3 py-2 text-right"
                        }
                      >
                        <span className="font-medium">{formatPrice(r.priceCents)}</span>
                        {off != null ? (
                          <div className="text-xs">
                            <span className="text-neutral-400 line-through">
                              {formatPrice(r.compareAtPriceCents)}
                            </span>{" "}
                            <span className="font-medium text-rose-600">-{off}%</span>
                          </div>
                        ) : null}
                      </td>
                      {showExtraColumn ? (
                        <td className="bg-neutral-50 px-3 py-2 text-right font-semibold text-neutral-900">
                          {activeMetric.format(numeric(r[activeMetric.field as keyof typeof r]))}
                        </td>
                      ) : null}
                      <td className="px-3 py-2 text-right text-neutral-600">
                        {r.proteinG != null ? `${r.proteinG} g` : "—"}
                      </td>
                      <td className={tdSort("proteinPerDollar")}>
                        {METRICS.proteinPerDollar.format(r.proteinPerDollar)}
                      </td>
                      <td className={tdSort("costPer30gProtein")}>
                        {METRICS.costPer30gProtein.format(r.costPer30gProtein)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Mobile Card View */}
          <div className="flex flex-col gap-4 md:hidden">
            {rows.map((r, i) => {
              const off = salePercent(r.priceCents, r.compareAtPriceCents);
              const retailerCount = (r as GroupedListing).retailerCount;
              return (
                <div
                  key={r.variantId}
                  className="flex flex-col gap-3 rounded-lg border border-neutral-200 bg-white p-4"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="text-xs font-medium text-neutral-400">#{i + 1}</div>
                      <Link
                        href={`/product/${r.productId}`}
                        className="font-bold text-neutral-900 hover:text-brand-700 hover:underline"
                      >
                        {r.productName}
                      </Link>
                      <div className="text-sm text-neutral-500">
                        {r.brandName}
                        {r.flavor ? ` · ${r.flavor}` : ""}
                        {!r.inStock ? (
                          <span className="ml-1 text-rose-600 font-medium">(out of stock)</span>
                        ) : null}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-bold text-neutral-900">{formatPrice(r.priceCents)}</div>
                      {off != null ? (
                        <div className="text-xs">
                          <span className="text-neutral-400 line-through">
                            {formatPrice(r.compareAtPriceCents)}
                          </span>{" "}
                          <span className="font-bold text-rose-600">-{off}%</span>
                        </div>
                      ) : null}
                      <div className="text-xs text-neutral-500">{formatSize(r.sizeG)}</div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2 border-t border-neutral-100 pt-3">
                    {showExtraColumn ? (
                      <div className="flex flex-col rounded bg-neutral-50 p-2 ring-2 ring-brand-400">
                        <span className="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">
                          {activeMetric.label}
                        </span>
                        <span className="text-sm font-bold text-neutral-900">
                          {activeMetric.format(numeric(r[activeMetric.field as keyof typeof r]))}
                        </span>
                      </div>
                    ) : null}
                    <div
                      className={`flex flex-col rounded bg-brand-50 p-2${
                        isSort("proteinPerDollar") ? " ring-2 ring-brand-400" : ""
                      }`}
                    >
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-brand-700">
                        Protein / $
                      </span>
                      <span className="text-sm font-bold text-brand-900">
                        {METRICS.proteinPerDollar.format(r.proteinPerDollar)}
                      </span>
                    </div>
                    <div
                      className={`flex flex-col rounded bg-neutral-50 p-2${
                        isSort("costPer30gProtein") ? " ring-2 ring-brand-400" : ""
                      }`}
                    >
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">
                        $/30g Protein
                      </span>
                      <span className="text-sm font-semibold text-neutral-700">
                        {METRICS.costPer30gProtein.format(r.costPer30gProtein)}
                      </span>
                    </div>
                    <div className="flex flex-col rounded bg-neutral-50 p-2">
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">
                        Retailer
                      </span>
                      <span className="truncate text-sm font-semibold text-neutral-700">
                        {r.sourceSlug}
                        {retailerCount > 1 ? ` (+${retailerCount - 1})` : ""}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

function numeric(value: unknown): number | null {
  return typeof value === "number" ? value : null;
}
