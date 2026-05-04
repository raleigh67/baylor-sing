// site_v2/js/data.js

let _acts = null;

export async function loadActs() {
  if (_acts) return _acts;
  const r = await fetch("data/acts.json");
  _acts = await r.json();
  return _acts;
}

export function hexToHsv(h) {
  const r = parseInt(h.slice(1, 3), 16) / 255;
  const g = parseInt(h.slice(3, 5), 16) / 255;
  const b = parseInt(h.slice(5, 7), 16) / 255;
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b);
  const d = mx - mn;
  let H = 0;
  if (d > 0) {
    if (mx === r) H = ((g - b) / d) % 6;
    else if (mx === g) H = (b - r) / d + 2;
    else H = (r - g) / d + 4;
    H /= 6;
    if (H < 0) H += 1;
  }
  const S = mx === 0 ? 0 : d / mx;
  return { h: H, s: S, v: mx };
}

export function isMedal(p) { return p === "1st" || p === "2nd" || p === "3rd"; }
export function isPigskin(p) { return p && (isMedal(p) || (typeof p === "string" && p.includes("Pigskin"))); }
export function isYTSource(act) { return act.palette_source === "youtube"; }

export const PLACEMENT_ORDER = { "1st": 1, "2nd": 2, "3rd": 3, "Pigskin": 4, "Participated": 5 };
