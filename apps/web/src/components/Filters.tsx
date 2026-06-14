import { ALLERGEN_OPTIONS, DIETARY_OPTIONS } from "@/lib/facets";
import { METRIC_LIST } from "@/lib/metrics";
import type { Facets } from "@/lib/queries";
import type { Filters } from "@/lib/queries";

/**
 * A plain GET form: submitting encodes all state in the URL, so every filtered
 * view is shareable and bookmarkable with no client-side JavaScript.
 */
export function FilterBar({ filters, facets }: { filters: Filters; facets: Facets }) {
  return (
    <form
      method="get"
      className="grid grid-cols-1 gap-3 rounded-lg border border-neutral-200 bg-white p-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6"
    >
      <label className="flex flex-col gap-1 text-xs font-medium text-neutral-600 sm:col-span-2">
        Search
        <input
          type="text"
          name="q"
          defaultValue={filters.q ?? ""}
          placeholder="whey, vegan, brand…"
          className="rounded border border-neutral-300 px-2 py-1.5 text-sm text-neutral-900"
        />
      </label>

      <label className="flex flex-col gap-1 text-xs font-medium text-neutral-600">
        Sort by
        <select
          name="metric"
          defaultValue={filters.metric}
          className="rounded border border-neutral-300 px-2 py-1.5 text-sm text-neutral-900"
        >
          {METRIC_LIST.map((m) => (
            <option key={m.key} value={m.key}>
              {m.label}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1 text-xs font-medium text-neutral-600">
        Order
        <select
          name="order"
          defaultValue={filters.order}
          className="rounded border border-neutral-300 px-2 py-1.5 text-sm text-neutral-900"
        >
          <option value="best">Best first</option>
          <option value="worst">Worst first</option>
        </select>
      </label>

      <label className="flex flex-col gap-1 text-xs font-medium text-neutral-600">
        View
        <select
          name="view"
          defaultValue={filters.view}
          className="rounded border border-neutral-300 px-2 py-1.5 text-sm text-neutral-900"
        >
          <option value="grouped">By product (best offer)</option>
          <option value="all">All offers</option>
        </select>
      </label>

      <label className="flex flex-col gap-1 text-xs font-medium text-neutral-600">
        Brand
        <select
          name="brand"
          defaultValue={filters.brand ?? ""}
          className="rounded border border-neutral-300 px-2 py-1.5 text-sm text-neutral-900"
        >
          <option value="">All brands</option>
          {facets.brands.map((b) => (
            <option key={b} value={b}>
              {b}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1 text-xs font-medium text-neutral-600">
        Retailer
        <select
          name="source"
          defaultValue={filters.source ?? ""}
          className="rounded border border-neutral-300 px-2 py-1.5 text-sm text-neutral-900"
        >
          <option value="">All retailers</option>
          {facets.sources.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1 text-xs font-medium text-neutral-600">
        Max price ($)
        <input
          type="number"
          name="maxPrice"
          min="0"
          step="1"
          defaultValue={filters.maxPriceCents != null ? filters.maxPriceCents / 100 : ""}
          className="rounded border border-neutral-300 px-2 py-1.5 text-sm text-neutral-900"
        />
      </label>

      <label className="flex flex-col gap-1 text-xs font-medium text-neutral-600">
        Min protein/serving (g)
        <input
          type="number"
          name="minProtein"
          min="0"
          step="1"
          defaultValue={filters.minProtein ?? ""}
          className="rounded border border-neutral-300 px-2 py-1.5 text-sm text-neutral-900"
        />
      </label>

      <label className="flex items-center gap-2 self-end text-xs font-medium text-neutral-600">
        <input
          type="checkbox"
          name="inStock"
          value="1"
          defaultChecked={filters.inStockOnly}
          className="h-4 w-4"
        />
        In stock only
      </label>

      <fieldset className="col-span-full flex flex-col gap-1 border-t border-neutral-100 pt-3">
        <legend className="text-xs font-semibold text-neutral-700">Dietary &amp; certifications</legend>
        <div className="flex flex-wrap gap-x-4 gap-y-1.5">
          {DIETARY_OPTIONS.map((o) => (
            <label key={o.value} className="flex items-center gap-1.5 text-xs text-neutral-600">
              <input
                type="checkbox"
                name="dietary"
                value={o.value}
                defaultChecked={filters.dietary.includes(o.value)}
                className="h-4 w-4"
              />
              {o.label}
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="col-span-full flex flex-col gap-1">
        <legend className="text-xs font-semibold text-neutral-700">Free from (exclude allergens)</legend>
        <div className="flex flex-wrap gap-x-4 gap-y-1.5">
          {ALLERGEN_OPTIONS.map((o) => (
            <label key={o.value} className="flex items-center gap-1.5 text-xs text-neutral-600">
              <input
                type="checkbox"
                name="allergenFree"
                value={o.value}
                defaultChecked={filters.allergenFree.includes(o.value)}
                className="h-4 w-4"
              />
              {o.label}
            </label>
          ))}
          <label className="flex items-center gap-1.5 text-xs font-medium text-neutral-700">
            <input
              type="checkbox"
              name="noArtificial"
              value="1"
              defaultChecked={filters.noArtificial}
              className="h-4 w-4"
            />
            No artificial sweeteners
          </label>
        </div>
      </fieldset>

      <div className="flex items-end gap-2 sm:col-span-2 lg:col-span-2">
        <button
          type="submit"
          className="rounded bg-brand-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-brand-700"
        >
          Apply
        </button>
        <a
          href="/"
          className="rounded border border-neutral-300 px-4 py-1.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
        >
          Reset
        </a>
      </div>
    </form>
  );
}
