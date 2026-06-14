/** Canonical ingredient-facet vocabularies + display labels for filtering. */

export const DIETARY_OPTIONS: { value: string; label: string }[] = [
  { value: "vegan", label: "Vegan" },
  { value: "vegetarian", label: "Vegetarian" },
  { value: "gluten_free", label: "Gluten-Free" },
  { value: "dairy_free", label: "Dairy-Free" },
  { value: "keto", label: "Keto" },
  { value: "organic", label: "Organic" },
  { value: "non_gmo", label: "Non-GMO" },
  { value: "kosher", label: "Kosher" },
  { value: "halal", label: "Halal" },
  { value: "grass_fed", label: "Grass-Fed" },
  { value: "sugar_free", label: "Sugar-Free" },
];

export const ALLERGEN_OPTIONS: { value: string; label: string }[] = [
  { value: "milk", label: "Milk/Dairy" },
  { value: "soy", label: "Soy" },
  { value: "gluten", label: "Gluten/Wheat" },
  { value: "egg", label: "Egg" },
  { value: "tree_nuts", label: "Tree Nuts" },
  { value: "peanut", label: "Peanut" },
  { value: "fish", label: "Fish" },
  { value: "shellfish", label: "Shellfish" },
  { value: "sesame", label: "Sesame" },
];

/** Sweeteners considered artificial (for the "no artificial sweeteners" filter). */
export const ARTIFICIAL_SWEETENERS = ["sucralose", "aspartame", "acesulfame_k", "saccharin"];

const LABELS: Record<string, string> = {
  ...Object.fromEntries(DIETARY_OPTIONS.map((o) => [o.value, o.label])),
  ...Object.fromEntries(ALLERGEN_OPTIONS.map((o) => [o.value, o.label])),
  monk_fruit: "Monk Fruit",
  acesulfame_k: "Acesulfame-K",
};

/** Human-readable label for a facet tag (falls back to title-casing). */
export function facetLabel(tag: string): string {
  return LABELS[tag] ?? tag.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
