// site/js/charts/genre_proportions.js
const NS = "http://www.w3.org/2000/svg";
function svg(tag, attrs) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; }

const TOP_N = 8;
const COLORS = ["#d4af37", "#7a102a", "#1d8143", "#641d56", "#444f69", "#874563", "#cc8d6d", "#e6bea7"];

export function render(root, acts) {
  let activeMatch = null;

  function build() {
    while (root.firstChild) root.removeChild(root.firstChild);
    const scope = activeMatch ? acts.filter(activeMatch) : acts;

    if (activeMatch) {
      // Single act: bar chart of that act's genre counts
      const act = scope[0];
      if (!act || !act.genres) {
        const p = document.createElement("p");
        p.className = "song-age-note";
        p.textContent = "No genre data for this act.";
        root.appendChild(p);
        return;
      }
      const counts = {};
      act.genres.split(";").forEach(g => {
        g = g.trim(); if (!g) return;
        counts[g] = (counts[g] || 0) + 1;
      });
      const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
      if (sorted.length === 0) {
        const p = document.createElement("p"); p.className = "song-age-note";
        p.textContent = "No genre tags."; root.appendChild(p); return;
      }
      const max = sorted[0][1];
      const W = 700, BAR_H = 22, GAP = 4, LABEL_W = 180, PAD = 30;
      const H = sorted.length * (BAR_H + GAP) + PAD * 2;
      const svgEl = svg("svg", { width: "100%", viewBox: `0 0 ${W} ${H}`, style: "display:block;" });
      root.appendChild(svgEl);
      const head = svg("text", { x: PAD, y: 18, class: "ta-label" });
      head.setAttribute("fill", "var(--gold)");
      head.textContent = `${act.year} ${act.group} — genres across ${act.song_count} songs`;
      svgEl.appendChild(head);
      sorted.forEach(([g, n], i) => {
        const y = PAD + i * (BAR_H + GAP);
        const barW = (n / max) * (W - LABEL_W - PAD - 60);
        svgEl.appendChild(svg("rect", { x: LABEL_W, y, width: barW, height: BAR_H, fill: "var(--gold)", rx: 2 }));
        const lbl = svg("text", { x: LABEL_W - 8, y: y + BAR_H * 0.7, class: "ta-label", "text-anchor": "end" });
        lbl.textContent = g;
        svgEl.appendChild(lbl);
        const val = svg("text", { x: LABEL_W + barW + 6, y: y + BAR_H * 0.7, class: "ta-value", "text-anchor": "start" });
        val.textContent = String(n);
        svgEl.appendChild(val);
      });
      return;
    }

    const yearCounts = { 2022: {}, 2023: {}, 2024: {}, 2025: {} };
    const totalCounts = {};
    scope.forEach(a => {
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

  build();

  return {
    highlight(matchFn) { activeMatch = matchFn; build(); },
    reset() { activeMatch = null; build(); },
  };
}
