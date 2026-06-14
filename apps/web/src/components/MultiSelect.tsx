"use client";

import { useEffect, useRef, useState } from "react";

export interface MultiSelectItem {
  /** Form field name this checkbox submits under. */
  name: string;
  value: string;
  label: string;
  checked: boolean;
}

/**
 * A dropdown of checkboxes that live inside the parent GET form. The popover is
 * just presentation — the checkboxes are real inputs, so selections submit (and
 * become shareable URL params) exactly like the rest of the filter bar. Items
 * filtered out by the search box are hidden with CSS, not unmounted, so a
 * checked-but-hidden item still submits.
 */
export function MultiSelect({
  label,
  items,
  placeholder = "All",
}: {
  label: string;
  items: MultiSelectItem[];
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  const count = items.filter((i) => i.checked).length;
  const showFilter = items.length > 10;
  const q = query.trim().toLowerCase();

  return (
    <div className="flex flex-col gap-1 text-xs font-medium text-neutral-600" ref={ref}>
      {label}
      <div className="relative">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          className="flex w-full items-center justify-between gap-2 rounded border border-neutral-300 px-2 py-1.5 text-sm text-neutral-900"
        >
          <span className="truncate">
            {count > 0 ? `${count} selected` : placeholder}
          </span>
          <span className="text-neutral-400">▾</span>
        </button>

        {open ? (
          <div className="absolute left-0 z-20 mt-1 max-h-72 w-full min-w-[12rem] overflow-auto rounded border border-neutral-200 bg-white p-2 shadow-lg">
            {showFilter ? (
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Filter…"
                className="mb-2 w-full rounded border border-neutral-300 px-2 py-1 text-sm font-normal text-neutral-900"
              />
            ) : null}
            <div className="flex flex-col gap-1">
              {items.map((item) => {
                const hidden = q.length > 0 && !item.label.toLowerCase().includes(q);
                return (
                  <label
                    key={`${item.name}:${item.value}`}
                    className={`flex items-center gap-2 rounded px-1 py-0.5 font-normal text-neutral-700 hover:bg-neutral-50 ${
                      hidden ? "hidden" : ""
                    }`}
                  >
                    <input
                      type="checkbox"
                      name={item.name}
                      value={item.value}
                      defaultChecked={item.checked}
                      className="h-4 w-4"
                    />
                    {item.label}
                  </label>
                );
              })}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
