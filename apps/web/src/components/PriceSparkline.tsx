/** Minimal dependency-free SVG sparkline for a price series. */
export function PriceSparkline({ points }: { points: { t: number; v: number }[] }) {
  if (points.length === 0) {
    return <p className="text-sm text-neutral-400">No price history yet.</p>;
  }

  const sorted = [...points].sort((a, b) => a.t - b.t);
  const values = sorted.map((p) => p.v);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const width = 480;
  const height = 64;
  const span = max - min || 1;

  const coords = sorted.map((p, i) => {
    const x = sorted.length === 1 ? width / 2 : (i / (sorted.length - 1)) * width;
    const y = height - ((p.v - min) / span) * (height - 8) - 4;
    return { x, y };
  });

  const path = coords.map((c, i) => `${i === 0 ? "M" : "L"}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(" ");
  const latest = values[values.length - 1] ?? max;

  return (
    <div>
      <svg viewBox={`0 0 ${width} ${height}`} className="h-16 w-full" preserveAspectRatio="none">
        {sorted.length > 1 && (
          <path d={path} fill="none" stroke="#f54c20" strokeWidth={2} />
        )}
        {coords.map((c, i) => (
          <circle key={i} cx={c.x} cy={c.y} r={2.5} fill="#f54c20" />
        ))}
      </svg>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="text-base font-semibold text-neutral-900">
          ${(latest / 100).toFixed(2)}
        </span>
        <span className="text-xs text-neutral-400">current</span>
        {max !== min ? (
          <span className="ml-2 text-xs text-neutral-500">
            range ${(min / 100).toFixed(2)}–${(max / 100).toFixed(2)}
          </span>
        ) : null}
      </div>
    </div>
  );
}
