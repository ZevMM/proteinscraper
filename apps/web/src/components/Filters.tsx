import { MultiSelect, type MultiSelectItem } from "@/components/MultiSelect";
import { ALLERGEN_OPTIONS, DIETARY_OPTIONS } from "@/lib/facets";
import { METRIC_LIST } from "@/lib/metrics";
import type { Facets } from "@/lib/queries";
import type { Filters } from "@/lib/queries";

/**
 * A plain GET form: submitting encodes all state in the URL, so every filtered
 * view is shareable and bookmarkable. The multi-select dropdowns are thin client
 * components whose checkboxes are real form inputs, so they submit the same way.
 */
export function FilterBar({ filters, facets }: { filters: Filters; facets: Facets }) {
  const brandItems: MultiSelectItem[] = facets.brands.map((b) => ({
    name: "brand",
    value: b,
    label: b,
    checked: filters.brands.includes(b),
  }));
  const retailerItems: MultiSelectItem[] = facets.sources.map((s) => ({
    name: "source",
    value: s,
    label: s,
    checked: filters.sources.includes(s),
  }));
  const dietaryItems: MultiSelectItem[] = DIETARY_OPTIONS.map((o) => ({
    name: "dietary",
    value: o.value,
    label: o.label,
    checked: filters.dietary.includes(o.value),
  }));
  const freeFromItems: MultiSelectItem[] = [
    ...ALLERGEN_OPTIONS.map((o) => ({
      name: "allergenFree",
      value: o.value,
      label: o.label,
      checked: filters.allergenFree.includes(o.value),
    })),
    {
      name: "noArtificial",
      value: "1",
      label: "Artificial sweeteners",
      checked: filters.noArtificial,
    },
  ];

  return (
    <form
      method="get"
      className="flex flex-col gap-4 rounded-lg border border-neutral-200 bg-white p-4"
    >
      {/* Primary controls: search + how results are ranked/capped. */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-6">
        <label className="flex flex-col gap-1 text-xs font-medium text-neutral-600 sm:col-span-2 lg:col-span-3">
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
      </div>

      {/* Filter section: narrow the set of products. */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Filters
          </span>
          <span className="h-px flex-1 bg-neutral-100" />
        </div>
        <div className="grid grid-cols-1 items-end gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5">
          <MultiSelect label="Brand" items={brandItems} placeholder="All brands" />
          <MultiSelect label="Retailer" items={retailerItems} placeholder="All retailers" />
          <MultiSelect label="Dietary & certifications" items={dietaryItems} placeholder="Any" />
          <MultiSelect label="Free from" items={freeFromItems} placeholder="None excluded" />

          <label className="flex items-center gap-2 self-end py-1.5 text-xs font-medium text-neutral-600">
            <input
              type="checkbox"
              name="inStock"
              value="1"
              defaultChecked={filters.inStockOnly}
              className="h-4 w-4"
            />
            In stock only
          </label>
        </div>
      </div>

      <div className="mt-2 flex gap-2">
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
