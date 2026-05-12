// site/js/charts/sat_val_scatter.js
import { isYTSource, isMedal } from "../data.js";

const NS = "http://www.w3.org/2000/svg";
function svg(tag, attrs) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; }
function svgText(parent, x, y, content, cls, anchor) {
  const t = svg("text", { x, y, class: cls, ...(anchor ? { "text-anchor": anchor } : {}) });
  t.textContent = content;
  parent.appendChild(t);
  return t;
}
function svgLine(parent, x1, y1, x2, y2, cls) {
  parent.appendChild(svg("line", { x1, y1, x2, y2, class: cls }));
}

const W = 700, H = 360, PAD_L = 50, PAD_R = 30, PAD_T = 20, PAD_B = 40;

const QUADRANTS = [
  { id: "all",    label: "All",                viewBox: `0 0 ${W} ${H}` },
  { id: "vivid",  label: "Vivid + Bright",     viewBox: `${W/2} 0 ${W/2} ${H/2}` },
  { id: "punch",  label: "Vivid + Dark",       viewBox: `${W/2} ${H/2} ${W/2} ${H/2}` },
  { id: "soft",   label: "Muted + Bright",     viewBox: `0 0 ${W/2} ${H/2}` },
  { id: "moody",  label: "Muted + Dark",       viewBox: `0 ${H/2} ${W/2} ${H/2}` },
];

export function render(root, acts) {
  const valid = acts.filter(isYTSource);
  const innerW = W - PAD_L - PAD_R, innerH = H - PAD_T - PAD_B;

  while (root.firstChild) root.removeChild(root.firstChild);

  // Zoom bar
  const zoomBar = document.createElement("div");
  zoomBar.className = "chart-zoom-controls";
  QUADRANTS.forEach(q => {
    const btn = document.createElement("button");
    btn.className = "chart-zoom-btn" + (q.id === "all" ? " active" : "");
    btn.textContent = q.label;
    btn.dataset.zoom = q.id;
    btn.addEventListener("click", () => {
      zoomBar.querySelectorAll(".chart-zoom-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      svgEl.setAttribute("viewBox", q.viewBox);
    });
    zoomBar.appendChild(btn);
  });
  root.appendChild(zoomBar);

  const svgEl = svg("svg", { width: "100%", viewBox: `0 0 ${W} ${H}`, style: "display:block;background:linear-gradient(180deg,var(--ink-3),var(--ink));border-radius:4px;transition:viewBox .3s ease;" });
  root.appendChild(svgEl);

  const g = svg("g", { transform: `translate(${PAD_L},${PAD_T})` });
  svgEl.appendChild(g);

  for (let i = 1; i < 4; i++) {
    svgLine(g, 0, i * innerH / 4, innerW, i * innerH / 4, "chart-tick");
    svgLine(g, i * innerW / 4, 0, i * innerW / 4, innerH, "chart-tick");
  }
  svgLine(g, 0, innerH, innerW, innerH, "chart-axis");
  svgLine(g, 0, 0, 0, innerH, "chart-axis");
  ["0", ".25", ".5", ".75", "1"].forEach((t, i) => {
    svgText(g, i * innerW / 4, innerH + 14, t, "chart-axis-num", "middle");
    svgText(g, -8, innerH - i * innerH / 4 + 3, t, "chart-axis-num", "end");
  });
  svgText(g, innerW / 2, innerH + 32, "Saturation (muted → vivid)", "chart-axis-label", "middle");
  const yLab = svg("text", { x: -28, y: innerH / 2, class: "chart-axis-label", "text-anchor": "middle", transform: `rotate(-90, -28, ${innerH / 2})` });
  yLab.textContent = "Brightness";
  g.appendChild(yLab);

  // Tooltip
  const tip = document.createElement("div");
  tip.className = "chart-tooltip";
  root.appendChild(tip);

  const dotEntries = [];

  valid.forEach(d => {
    const x = d.avg_sat * innerW;
    const y = (1 - d.avg_val) * innerH;
    const r = isMedal(d.placement) ? 7 : 5;
    const dot = svg("circle", {
      cx: x, cy: y, r, fill: d.dominant,
      stroke: isMedal(d.placement) ? "var(--gold)" : "#000",
      "stroke-width": isMedal(d.placement) ? 1.5 : 0.5,
      class: "chart-dot",
    });
    dot.addEventListener("mousemove", ev => {
      while (tip.firstChild) tip.removeChild(tip.firstChild);
      tip.style.opacity = "1";
      tip.style.left = (ev.clientX + 14) + "px";
      tip.style.top = (ev.clientY + 14) + "px";
      const h4 = document.createElement("h4");
      h4.textContent = d.group + (d.theme ? " — " + d.theme : "");
      tip.appendChild(h4);
      const meta = document.createElement("div");
      meta.className = "meta";
      meta.textContent = `${d.year} · ${d.placement}`;
      tip.appendChild(meta);
      const sw = document.createElement("div");
      sw.className = "swatches";
      d.palette.slice(0, 6).forEach(hh => {
        const c = document.createElement("div");
        c.style.background = hh;
        sw.appendChild(c);
      });
      tip.appendChild(sw);
    });
    dot.addEventListener("mouseleave", () => tip.style.opacity = "0");
    dot.addEventListener("click", () => {
      document.dispatchEvent(new CustomEvent("focus-act", { detail: { year: d.year, group: d.group } }));
    });
    g.appendChild(dot);
    dotEntries.push({ d, dot });
  });

  const exp = document.createElement("p");
  exp.className = "chart-explainer";
  const b1 = document.createElement("b"); b1.textContent = "Saturation"; exp.appendChild(b1);
  exp.appendChild(document.createTextNode(" is how vivid (vs muted) the palette is. "));
  const b2 = document.createElement("b"); b2.textContent = "Brightness"; exp.appendChild(b2);
  exp.appendChild(document.createTextNode(" is how light (vs dark). Top-right: punch-you-in-the-face. Bottom-left: muted-and-moody."));
  root.appendChild(exp);

  function applyFocus(matchFn) {
    dotEntries.forEach(({ d, dot }) => {
      dot.classList.remove("focused", "dimmed");
      if (!matchFn) return;
      if (matchFn(d)) dot.classList.add("focused");
      else dot.classList.add("dimmed");
    });
  }

  return {
    highlight(matchFn) { applyFocus(matchFn); },
    reset() { applyFocus(null); },
  };
}
