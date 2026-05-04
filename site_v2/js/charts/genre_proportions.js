// site_v2/js/charts/genre_proportions.js
const NS = "http://www.w3.org/2000/svg";
function svg(tag, attrs) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; }

const TOP_N = 8;
const COLORS = ["#d4af37", "#7a102a", "#1d8143", "#641d56", "#444f69", "#874563", "#cc8d6d", "#e6bea7"];

export function render(root, acts) {
  const yearCounts = { 2022: {}, 2023: {}, 2024: {}, 2025: {} };
  const totalCounts = {};
  acts.forEach(a => {
    if (!a.genres) return;
    a.genres.split(";").forEach(g => {
      g = g.trim(); if (!g) return;
      yearCounts[a.year][g] = (yearCounts[a.year][g] || 0) + 1;
      totalCounts[g] = (totalCounts[g] || 0) + 1;
    });
  });
  const topGenres = Object.entries(totalCounts).sort((a, b) => b[1] - a[1]).slice(0, TOP_N).map(([g]) => g);
  const colorOf = g => COLORS[topGenres.indexOf(g) % COLORS.length];

  const W = 700, H = 280, PAD_L = 50, PAD_R = 80, PAD_T = 20, PAD_B = 40;
  const innerW = W - PAD_L - PAD_R, innerH = H - PAD_T - PAD_B;
  const years = [2022, 2023, 2024, 2025];

  while (root.firstChild) root.removeChild(root.firstChild);
  const svgEl = svg("svg", { width: "100%", viewBox: `0 0 ${W} ${H}`, style: "display:block;" });
  root.appendChild(svgEl);

  const bw = innerW / years.length - 16;
  years.forEach((yr, i) => {
    const x = PAD_L + i * (innerW / years.length) + 8;
    const total = topGenres.reduce((s, g) => s + (yearCounts[yr][g] || 0), 0) || 1;
    let cum = 0;
    topGenres.forEach(g => {
      const v = (yearCounts[yr][g] || 0) / total;
      const start = cum; cum += v;
      const y = PAD_T + start * innerH;
      const h = v * innerH;
      svgEl.appendChild(svg("rect", { x, y, width: bw, height: h, fill: colorOf(g) }));
    });
    const lab = svg("text", { x: x + bw / 2, y: PAD_T + innerH + 14, class: "ta-label", "text-anchor": "middle" });
    lab.textContent = String(yr);
    svgEl.appendChild(lab);
  });

  const legend = document.createElement("div");
  legend.className = "genre-legend";
  topGenres.forEach(g => {
    const item = document.createElement("span");
    const sw = document.createElement("i");
    sw.style.background = colorOf(g);
    item.appendChild(sw);
    item.appendChild(document.createTextNode(g));
    legend.appendChild(item);
  });
  root.appendChild(legend);
}
