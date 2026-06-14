import Link from "next/link";
import { notFound } from "next/navigation";

import { PriceSparkline } from "@/components/PriceSparkline";
import { ARTIFICIAL_SWEETENERS, facetLabel } from "@/lib/facets";
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

  // Aggregate ingredient facts across all variants of this product.
  const uniq = (xs: string[]) => [...new Set(xs)];
  const dietary = uniq(rows.flatMap((r) => r.dietaryLabels));
  const allergens = uniq(rows.flatMap((r) => r.allergens));
  const sweeteners = uniq(rows.flatMap((r) => r.sweeteners));
  const ingredientsText = rows.find((r) => r.ingredientsText)?.ingredientsText ?? null;
  const hasFacts =
    dietary.length > 0 || allergens.length > 0 || sweeteners.length > 0 || ingredientsText;

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

      {hasFacts ? (
        <section className="rounded-lg border border-neutral-200 bg-white p-4">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">
            Ingredients &amp; dietary
          </h2>
          <div className="flex flex-col gap-3">
            {dietary.length > 0 ? (
              <TagRow label="Dietary">
                {dietary.map((t) => (
                  <Pill key={t} className="bg-emerald-50 text-emerald-700">
                    {facetLabel(t)}
                  </Pill>
                ))}
              </TagRow>
            ) : null}
            {sweeteners.length > 0 ? (
              <TagRow label="Sweeteners">
                {sweeteners.map((t) => (
                  <Pill
                    key={t}
                    className={
                      ARTIFICIAL_SWEETENERS.includes(t)
                        ? "bg-amber-50 text-amber-700"
                        : "bg-neutral-100 text-neutral-700"
                    }
                  >
                    {facetLabel(t)}
                  </Pill>
                ))}
              </TagRow>
            ) : null}
            {allergens.length > 0 ? (
              <TagRow label="Contains">
                {allergens.map((t) => (
                  <Pill key={t} className="bg-rose-50 text-rose-700">
                    {facetLabel(t)}
                  </Pill>
                ))}
              </TagRow>
            ) : null}
            {ingredientsText ? (
              <div className="border-t border-neutral-100 pt-3">
                <div className="mb-1 text-xs font-semibold text-neutral-500">Ingredients</div>
                <p className="text-sm leading-relaxed text-neutral-700">{ingredientsText}</p>
              </div>
            ) : null}
          </div>
        </section>
      ) : null}

      <section className="rounded-lg border border-neutral-200 bg-white">
        <h2 className="px-4 pt-4 text-sm font-semibold uppercase tracking-wide text-neutral-500">
          Listings &amp; variants
        </h2>

        {/* Desktop Table */}
        <div className="hidden md:block">
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
                <tr key={r.variantId} className="border-b border-neutral-100 last:border-0 hover:bg-neutral-50">
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
        </div>

        {/* Mobile Cards */}
        <div className="flex flex-col divide-y divide-neutral-100 md:hidden">
          {rows.map((r) => (
            <div key={r.variantId} className="flex flex-col gap-3 p-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="font-bold text-neutral-900">{r.flavor ?? "Unflavored / Original"}</div>
                  <div className="text-sm text-neutral-500">
                    {r.sourceSlug} · {formatSize(r.sizeG)}
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-bold text-neutral-900">{formatPrice(r.priceCents)}</div>
                  {salePercent(r.priceCents, r.compareAtPriceCents) != null ? (
                    <div className="text-xs font-bold text-rose-600">
                      -{salePercent(r.priceCents, r.compareAtPriceCents)}%
                    </div>
                  ) : null}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="flex flex-col rounded bg-neutral-50 p-2">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">
                    Protein / $
                  </span>
                  <span className="text-sm font-bold text-neutral-900">
                    {METRICS.proteinPerDollar.format(r.proteinPerDollar)}
                  </span>
                </div>
                <div className="flex flex-col rounded bg-neutral-50 p-2">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">
                    $/30g Protein
                  </span>
                  <span className="text-sm font-semibold text-neutral-700">
                    {METRICS.costPer30gProtein.format(r.costPer30gProtein)}
                  </span>
                </div>
              </div>

              <a
                href={r.url}
                target="_blank"
                rel="noopener noreferrer nofollow"
                className="mt-1 block w-full rounded border border-brand-200 bg-brand-50 py-2 text-center text-sm font-bold text-brand-700 hover:bg-brand-100"
              >
                View on {r.sourceSlug} ↗
              </a>
            </div>
          ))}
        </div>
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

function TagRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs font-semibold text-neutral-500">{label}:</span>
      {children}
    </div>
  );
}

function Pill({ className, children }: { className: string; children: React.ReactNode }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${className}`}>{children}</span>
  );
}
