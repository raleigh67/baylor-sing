// site_v2/js/charts/song_age.js
const NS = "http://www.w3.org/2000/svg";
function svg(tag, attrs) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; }

export function render(root, acts) {
  const data = acts.filter(a => a.popularity != null);
  const W = 700, H = 280, PAD_L = 50, PAD_R = 20, PAD_T = 20, PAD_B = 40;
  const innerW = W - PAD_L - PAD_R, innerH = H - PAD_T - PAD_B;

  const buckets = Array.from({ length: 10 }, () => 0);
  data.forEach(a => {
    const b = Math.min(9, Math.floor(a.popularity / 10));
    buckets[b]++;
  });
  const max = Math.max(...buckets, 1);

  while (root.firstChild) root.removeChild(root.firstChild);
  const svgEl = svg("svg", { width: "100%", viewBox: `0 0 ${W} ${H}`, style: "display:block;" });
  root.appendChild(svgEl);

  buckets.forEach((count, i) => {
    const x = PAD_L + i * (innerW / 10);
    const w = innerW / 10 - 4;
    const h = (count / max) * innerH;
    const y = PAD_T + innerH - h;
    svgEl.appendChild(svg("rect", { x, y, width: w, height: h, fill: "var(--gold-dim)", rx: 1 }));
    const cnt = svg("text", { x: x + w / 2, y: y - 4, class: "ta-value", "text-anchor": "middle" });
    cnt.textContent = String(count);
    svgEl.appendChild(cnt);
    const lab = svg("text", { x: x + w / 2, y: PAD_T + innerH + 14, class: "ta-label", "text-anchor": "middle" });
    lab.textContent = `${i * 10}-${i * 10 + 9}`;
    svgEl.appendChild(lab);
  });
  const ax = svg("text", { x: W / 2, y: H - 8, class: "chart-axis-label", "text-anchor": "middle" });
  ax.textContent = "Avg song popularity (0–100, Spotify)";
  svgEl.appendChild(ax);

  const exp = document.createElement("p");
  exp.className = "chart-explainer";
  const b = document.createElement("b"); b.textContent = "Spotify popularity";
  exp.appendChild(b);
  exp.appendChild(document.createTextNode(" is a 0–100 score per song; this chart shows each act's average across their songs."));
  root.appendChild(exp);
}
