import Link from "next/link";
import { notFound } from "next/navigation";

import { PriceSparkline } from "@/components/PriceSparkline";
import { formatPrice, formatSize, salePercent } from "@/lib/format";
import { METRICS } from "@/lib/metrics";
import { getProductDetail } from "@/lib/queries";

export const dynamic = "force-dynamic";

export default async function ProductPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const detail = await getProductDetail(id);
  if (!detail) notFound();

  const { rows, history } = detail;
  const best = rows[0];
  if (!best) notFound();

  return (
    <div className="flex flex-col gap-6">
      <Link href="/" className="text-sm text-brand-700 hover:underline">
        ← Back to comparison
      </Link>

      <div>
        <h1 className="text-2xl font-bold tracking-tight">{best.productName}</h1>
        <p className="text-sm text-neutral-500">
          {best.brandName}
          {best.category ? ` · ${best.category}` : ""}
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <section className="rounded-lg border border-neutral-200 bg-white p-4 md:col-span-1">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">
            Nutrition (per serving)
          </h2>
          <dl className="grid grid-cols-2 gap-y-2 text-sm">
            <Fact label="Serving size" value={best.servingSizeG != null ? `${best.servingSizeG} g` : "—"} />
            <Fact label="Protein" value={best.proteinG != null ? `${best.proteinG} g` : "—"} />
            <Fact label="Calories" value={best.caloriesKcal != null ? `${best.caloriesKcal}` : "—"} />
            <Fact label="Fat" value={best.fatG != null ? `${best.fatG} g` : "—"} />
            <Fact label="Carbs" value={best.carbG != null ? `${best.carbG} g` : "—"} />
          </dl>
          <div className="mt-3 flex items-center justify-between border-t border-neutral-100 pt-3 text-xs text-neutral-500">
            <span>
              {best.servingsPerContainer != null
                ? `≈ ${best.servingsPerContainer} servings per container`
                : "Servings per container unknown"}
            </span>
            <span className="text-neutral-400">
              {(best.confidence * 100).toFixed(0)}% confidence
            </span>
          </div>
        </section>

        <section className="rounded-lg border border-neutral-200 bg-white p-4 md:col-span-2">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">
            Price history
          </h2>
          <PriceSparkline points={history.map((h) => ({ t: +new Date(h.capturedAt), v: h.priceCents }))} />
          <p className="mt-2 text-xs text-neutral-400">
            {history.length} observation{history.length === 1 ? "" : "s"} across all variants.
          </p>
        </section>
      </div>

      <section className="overflow-x-auto rounded-lg border border-neutral-200 bg-white">
        <h2 className="px-4 pt-4 text-sm font-semibold uppercase tracking-wide text-neutral-500">
          Listings &amp; variants
        </h2>
        <table className="mt-2 w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-neutral-200 bg-neutral-50 text-left text-xs uppercase tracking-wide text-neutral-500">
              <th className="px-4 py-2">Retailer</th>
              <th className="px-4 py-2">Flavor</th>
              <th className="px-4 py-2 text-right">Size</th>
              <th className="px-4 py-2 text-right">Price</th>
              <th className="px-4 py-2 text-right">Protein/$</th>
              <th className="px-4 py-2 text-right">$/30g</th>
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.variantId} className="border-b border-neutral-100 last:border-0">
                <td className="px-4 py-2 text-neutral-600">{r.sourceSlug}</td>
                <td className="px-4 py-2">{r.flavor ?? "—"}</td>
                <td className="px-4 py-2 text-right text-neutral-600">{formatSize(r.sizeG)}</td>
                <td className="px-4 py-2 text-right">
                  <span className="font-medium">{formatPrice(r.priceCents)}</span>
                  {salePercent(r.priceCents, r.compareAtPriceCents) != null ? (
                    <span className="ml-1 text-xs font-medium text-rose-600">
                      -{salePercent(r.priceCents, r.compareAtPriceCents)}%
                    </span>
                  ) : null}
                </td>
                <td className="px-4 py-2 text-right">{METRICS.proteinPerDollar.format(r.proteinPerDollar)}</td>
                <td className="px-4 py-2 text-right">{METRICS.costPer30gProtein.format(r.costPer30gProtein)}</td>
                <td className="px-4 py-2 text-right">
                  <a
                    href={r.url}
                    target="_blank"
                    rel="noopener noreferrer nofollow"
                    className="text-brand-700 hover:underline"
                  >
                    View ↗
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <>
      <dt className="text-neutral-500">{label}</dt>
      <dd className="text-right font-medium text-neutral-900">{value}</dd>
    </>
  );
}
