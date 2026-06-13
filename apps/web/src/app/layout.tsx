import type { Metadata } from "next";
import Link from "next/link";

import "./globals.css";

export const metadata: Metadata = {
  title: "SuppSearch — compare protein supplements",
  description:
    "Compare protein supplements by the metrics that matter: most protein per dollar, cheapest per 30g protein, least fat per gram of protein, and more.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <header className="border-b border-neutral-200 bg-white">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
            <Link href="/" className="text-lg font-bold tracking-tight">
              Supp<span className="text-brand-600">Search</span>
            </Link>
            <span className="hidden text-sm text-neutral-500 sm:inline">
              Compare protein supplements by what matters
            </span>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
        <footer className="mx-auto max-w-7xl px-4 py-8 text-xs text-neutral-400">
          Prices and nutrition are scraped from public sources and may be out of date.
          Always confirm on the retailer&apos;s site before buying.
        </footer>
      </body>
    </html>
  );
}
