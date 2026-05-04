// site_v2/js/charts/winner_vs_participant.js
import { isPigskin } from "../data.js";

const NS = "http://www.w3.org/2000/svg";
function svg(tag, attrs) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; }

export function render(root, acts) {
  const winners = acts.filter(a => isPigskin(a.placement) && a.valence != null);
  const losers = acts.filter(a => !isPigskin(a.placement) && a.valence != null);
  const features = ["valence", "energy", "danceability", "tempo"];
  const tempoMax = 200;

  function avg(group, key) {
    const vals = group.map(a => a[key]).filter(v => v != null);
    const m = vals.reduce((s, v) => s + v, 0) / (vals.length || 1);
    return key === "tempo" ? m / tempoMax : m;
  }
  const wAvg = features.map(k => avg(winners, k));
  const lAvg = features.map(k => avg(losers, k));

  const cx = 200, cy = 200, rMax = 130;

  while (root.firstChild) root.removeChild(root.firstChild);
  const h = document.createElement("h3"); h.className = "vp-h"; h.textContent = "Winner vs Participant — average audio fingerprint";
  root.appendChild(h);

  const svgEl = svg("svg", { viewBox: "0 0 400 400", width: "100%", style: "max-width:520px;display:block;margin:0 auto;" });
  root.appendChild(svgEl);

  features.forEach((f, i) => {
    const a = (i / features.length * 2 * Math.PI) - Math.PI / 2;
    const x = cx + Math.cos(a) * rMax;
    const y = cy + Math.sin(a) * rMax;
    svgEl.appendChild(svg("line", { x1: cx, y1: cy, x2: x, y2: y, class: "chart-tick" }));
    const lab = svg("text", { x: cx + Math.cos(a) * (rMax + 18), y: cy + Math.sin(a) * (rMax + 18) + 4, class: "vp-label", "text-anchor": "middle" });
    lab.textContent = f === "tempo" ? "tempo (norm.)" : f;
    svgEl.appendChild(lab);
  });
  [0.25, 0.5, 0.75, 1].forEach(p => {
    svgEl.appendChild(svg("circle", { cx, cy, r: rMax * p, fill: "none", stroke: "var(--border-quiet)", "stroke-width": 0.5 }));
  });
  function poly(values, color, fillOpacity) {
    const pts = values.map((v, i) => {
      const a = (i / features.length * 2 * Math.PI) - Math.PI / 2;
      return [cx + Math.cos(a) * rMax * v, cy + Math.sin(a) * rMax * v];
    });
    const d = "M " + pts.map(p => p.join(",")).join(" L ") + " Z";
    svgEl.appendChild(svg("path", { d, fill: color, "fill-opacity": fillOpacity, stroke: color, "stroke-width": 2 }));
  }
  poly(lAvg, "var(--text-tertiary)", 0.15);
  poly(wAvg, "var(--gold)", 0.3);

  const legend = document.createElement("div"); legend.className = "vp-legend";
  [["var(--gold)", `Pigskin (n=${winners.length})`], ["var(--text-tertiary)", `Participated (n=${losers.length})`]].forEach(([c, txt]) => {
    const span = document.createElement("span");
    const sw = document.createElement("i"); sw.style.background = c;
    span.appendChild(sw);
    span.appendChild(document.createTextNode(txt));
    legend.appendChild(span);
  });
  root.appendChild(legend);
}
