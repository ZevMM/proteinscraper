export function formatPrice(cents: number | null | undefined): string {
  if (cents == null) return "—";
  return `$${(cents / 100).toFixed(2)}`;
}

export function formatSize(grams: number | null | undefined): string {
  if (grams == null) return "—";
  const lb = grams / 453.59237;
  if (lb >= 1) return `${lb.toFixed(lb < 10 ? 1 : 0)} lb`;
  return `${Math.round(grams)} g`;
}

/** Percent off if compareAt is a genuine markdown above the current price. */
export function salePercent(
  priceCents: number,
  compareAtCents: number | null | undefined,
): number | null {
  if (compareAtCents == null || compareAtCents <= priceCents) return null;
  return Math.round((1 - priceCents / compareAtCents) * 100);
}

export function titleCase(value: string | null | undefined): string {
  if (!value) return "";
  return value
    .split(/[-\s]+/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}
