import Link from "next/link";

import { FilterBar } from "@/components/Filters";
import { formatPrice, formatSize, salePercent } from "@/lib/format";
import { METRICS } from "@/lib/metrics";
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
        <div className="overflow-x-auto rounded-lg border border-neutral-200 bg-white">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-neutral-200 bg-neutral-50 text-left text-xs uppercase tracking-wide text-neutral-500">
                <th className="px-3 py-2">#</th>
                <th className="px-3 py-2">Product</th>
                <th className="px-3 py-2">{grouped ? "Retailers" : "Retailer"}</th>
                <th className="px-3 py-2 text-right">Size</th>
                <th className="px-3 py-2 text-right">{grouped ? "Best price" : "Price"}</th>
                <th className="px-3 py-2 text-right">Protein/serv</th>
                <th className="border-b-2 border-brand-500 bg-neutral-100 px-3 py-2 text-right font-semibold text-neutral-800">
                  {activeMetric.label}
                </th>
                <th className="px-3 py-2 text-right">Protein/$</th>
                <th className="px-3 py-2 text-right">$/30g protein</th>
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
                    <td className="px-3 py-2 text-right text-neutral-600">{formatSize(r.sizeG)}</td>
                    <td className="px-3 py-2 text-right">
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
                    <td className="px-3 py-2 text-right text-neutral-600">
                      {r.proteinG != null ? `${r.proteinG} g` : "—"}
                    </td>
                    <td className="bg-neutral-50 px-3 py-2 text-right font-semibold text-neutral-900">
                      {activeMetric.format(numeric(r[activeMetric.field as keyof typeof r]))}
                    </td>
                    <td className="px-3 py-2 text-right text-neutral-600">
                      {METRICS.proteinPerDollar.format(r.proteinPerDollar)}
                    </td>
                    <td className="px-3 py-2 text-right text-neutral-600">
                      {METRICS.costPer30gProtein.format(r.costPer30gProtein)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function numeric(value: unknown): number | null {
  return typeof value === "number" ? value : null;
}
