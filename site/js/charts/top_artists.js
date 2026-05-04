// site_v2/js/charts/top_artists.js
const NS = "http://www.w3.org/2000/svg";
function svg(tag, attrs) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; }

export function render(root, acts) {
  const counts = new Map();
  acts.forEach(a => {
    if (!a.songs) return;
    a.songs.split(";").forEach(s => {
      const m = s.match(/\(([^)]+)\)\s*$/);
      if (m) {
        const artist = m[1].trim();
        counts.set(artist, (counts.get(artist) || 0) + 1);
      }
    });
  });
  const top = [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 20);
  if (top.length === 0) return;
  const max = top[0][1];
  const W = 700, BAR_H = 22, GAP = 4, LABEL_W = 200, PAD = 16;
  const H = top.length * (BAR_H + GAP) + PAD * 2;

  while (root.firstChild) root.removeChild(root.firstChild);
  const svgEl = svg("svg", { width: "100%", viewBox: `0 0 ${W} ${H}`, style: "display:block;" });
  root.appendChild(svgEl);

  top.forEach(([artist, n], i) => {
    const y = PAD + i * (BAR_H + GAP);
    const barW = (n / max) * (W - LABEL_W - PAD - 60);
    svgEl.appendChild(svg("rect", { x: LABEL_W, y, width: barW, height: BAR_H, fill: "var(--gold)", rx: 2 }));
    const lbl = svg("text", { x: LABEL_W - 8, y: y + BAR_H * 0.7, class: "ta-label", "text-anchor": "end" });
    lbl.textContent = artist;
    svgEl.appendChild(lbl);
    const val = svg("text", { x: LABEL_W + barW + 6, y: y + BAR_H * 0.7, class: "ta-value", "text-anchor": "start" });
    val.textContent = String(n);
    svgEl.appendChild(val);
  });
}
