// Sequential impact ramp (0..100) -> RGBA. Calm low, hot high.
const STOPS = [
  [0, [40, 60, 95]],     // deep blue (low)
  [40, [80, 140, 170]],  // teal
  [65, [240, 190, 70]],  // amber
  [82, [240, 120, 40]],  // orange
  [100, [220, 40, 50]],  // red (critical)
];
export function impactColor(v, alpha = 200) {
  const x = Math.max(0, Math.min(100, v ?? 0));
  for (let i = 1; i < STOPS.length; i++) {
    if (x <= STOPS[i][0]) {
      const [lo, c0] = STOPS[i - 1], [hi, c1] = STOPS[i];
      const t = (x - lo) / (hi - lo || 1);
      return [0, 1, 2].map((k) => Math.round(c0[k] + t * (c1[k] - c0[k]))).concat(alpha);
    }
  }
  return [...STOPS[STOPS.length - 1][1], alpha];
}
export const slaColor = { Low: "#3ddc97", Medium: "#f0be46", Critical: "#dc2832" };
