const CURRENCY_BY_MARKET: Record<string, string> = { US: "USD", UK: "GBP", IN: "INR" };
const LOCALE_BY_CURRENCY: Record<string, string> = {
  USD: "en-US",
  GBP: "en-GB",
  INR: "en-IN",
};
const SYMBOL_BY_CURRENCY: Record<string, string> = { USD: "$", GBP: "£", INR: "₹" };

/** ISO currency code for a market (US→USD, UK→GBP, IN→INR). */
export function currencyForMarket(market: string): string {
  return CURRENCY_BY_MARKET[market] ?? "USD";
}

/** Short currency symbol for compact labels/headers. */
export function currencySymbol(currency: string): string {
  return SYMBOL_BY_CURRENCY[currency] ?? "$";
}

export function formatPrice(
  cents: number | null | undefined,
  currency = "USD",
): string {
  if (cents == null) return "—";
  return new Intl.NumberFormat(LOCALE_BY_CURRENCY[currency] ?? "en-US", {
    style: "currency",
    currency,
  }).format(cents / 100);
}

/** US uses imperial (lb); other markets are metric (kg/g). */
export function formatSize(
  grams: number | null | undefined,
  market = "US",
): string {
  if (grams == null) return "—";
  if (market === "US") {
    const lb = grams / 453.59237;
    if (lb >= 1) return `${lb.toFixed(lb < 10 ? 1 : 0)} lb`;
    return `${Math.round(grams)} g`;
  }
  if (grams >= 1000) return `${(grams / 1000).toFixed(grams < 10000 ? 1 : 0)} kg`;
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
