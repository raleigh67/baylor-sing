// site_v2/js/charts/color_wheel.js
import { isYTSource, isMedal, hexToHsv } from "../data.js";

const NS = "http://www.w3.org/2000/svg";
function svg(tag, attrs) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; }

export function render(root, acts) {
  const valid = acts.filter(isYTSource);
  const cx = 200, cy = 200, rMax = 170;

  while (root.firstChild) root.removeChild(root.firstChild);
  const wrap = document.createElement("div");
  wrap.className = "cw-wrap";
  const svgEl = svg("svg", { viewBox: "0 0 400 400", width: "100%" });
  wrap.appendChild(svgEl);
  const tip = document.createElement("div");
  tip.className = "chart-tooltip";
  wrap.appendChild(tip);
  root.appendChild(wrap);

  // Conic gradient hue ring via foreignObject
  const fo = svg("foreignObject", { x: cx - rMax - 12, y: cy - rMax - 12, width: (rMax + 12) * 2, height: (rMax + 12) * 2 });
  const ring = document.createElementNS("http://www.w3.org/1999/xhtml", "div");
  ring.style.cssText = "width:100%;height:100%;border-radius:50%;background:conic-gradient(from -90deg, hsl(0,70%,50%), hsl(60,70%,50%), hsl(120,70%,50%), hsl(180,70%,50%), hsl(240,70%,50%), hsl(300,70%,50%), hsl(360,70%,50%));mask:radial-gradient(circle at center, transparent 70%, black 71%, black 76%, transparent 77%);-webkit-mask:radial-gradient(circle at center, transparent 70%, black 71%, black 76%, transparent 77%);opacity:.4;";
  fo.appendChild(ring);
  svgEl.appendChild(fo);

  svgEl.appendChild(svg("circle", { cx, cy, r: rMax, fill: "none", stroke: "var(--border-quiet)", "stroke-width": 1 }));
  svgEl.appendChild(svg("circle", { cx, cy, r: 3, fill: "var(--text-tertiary)" }));

  [["0°", 0], ["90°", 90], ["180°", 180], ["270°", 270]].forEach(([t, deg]) => {
    const a = (deg - 90) * Math.PI / 180;
    const tx = cx + Math.cos(a) * (rMax + 14);
    const ty = cy + Math.sin(a) * (rMax + 14);
    const lab = svg("text", { x: tx, y: ty + 3, class: "cw-label", "text-anchor": "middle" });
    lab.textContent = t;
    svgEl.appendChild(lab);
  });

  valid.forEach(d => {
    const { h: H, s: S } = hexToHsv(d.dominant);
    const angle = (H * 360 - 90) * Math.PI / 180;
    const r = S * rMax * 0.95;
    const x = cx + Math.cos(angle) * r;
    const y = cy + Math.sin(angle) * r;
    const dot = svg("circle", {
      cx: x, cy: y,
      r: isMedal(d.placement) ? 7 : (d.placement && d.placement.includes && d.placement.includes("Pigskin") ? 5 : 4),
      fill: d.dominant,
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
      meta.textContent = d.year + " · " + d.placement;
      tip.appendChild(meta);
      const sw = document.createElement("div");
      sw.className = "swatches";
      d.palette.slice(0, 6).forEach(hh => {
        const cc = document.createElement("div");
        cc.style.background = hh;
        sw.appendChild(cc);
      });
      tip.appendChild(sw);
    });
    dot.addEventListener("mouseleave", () => tip.style.opacity = "0");
    svgEl.appendChild(dot);
  });
}
