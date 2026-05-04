// site_v2/js/charts/audio_map.js
import { isMedal, isYTSource } from "../data.js";

const NS = "http://www.w3.org/2000/svg";
function svg(tag, attrs) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; }
function svgText(parent, x, y, content, cls, anchor) {
  const t = svg("text", { x, y, class: cls, ...(anchor ? { "text-anchor": anchor } : {}) });
  t.textContent = content;
  parent.appendChild(t);
  return t;
}
function svgLine(parent, x1, y1, x2, y2, cls) {
  const l = svg("line", { x1, y1, x2, y2, class: cls });
  parent.appendChild(l);
  return l;
}

export function render(root, acts) {
  const plottable = acts.filter(a => a.valence != null && a.energy != null);
  const missing = acts.filter(a => a.valence == null || a.energy == null);
  let activeYear = "all";

  // Build static structure with createElement (no template strings)
  while (root.firstChild) root.removeChild(root.firstChild);

  const controls = document.createElement("div");
  controls.className = "audio-map-controls";
  const labelText = document.createTextNode("Year filter: ");
  controls.appendChild(labelText);
  ["all", "2022", "2023", "2024", "2025"].forEach((yr, i) => {
    const span = document.createElement("span");
    span.className = "chart-year-toggle" + (i === 0 ? " active" : "");
    span.dataset.yr = yr;
    span.textContent = yr === "all" ? "All" : yr;
    span.addEventListener("click", () => {
      controls.querySelectorAll(".chart-year-toggle").forEach(x => x.classList.remove("active"));
      span.classList.add("active");
      activeYear = yr;
      draw();
    });
    controls.appendChild(span);
  });
  root.appendChild(controls);

  const svgEl = svg("svg", { width: "100%", viewBox: "0 0 800 560", style: "display:block;" });
  root.appendChild(svgEl);

  const tooltip = document.createElement("div");
  tooltip.className = "chart-tooltip";
  root.appendChild(tooltip);

  const legend = document.createElement("div");
  legend.className = "audio-map-legend";
  [
    ["legend-medal", "1st / 2nd / 3rd"],
    ["legend-pigskin", "Pigskin top-8"],
    ["legend-grey", "No real palette"],
  ].forEach(([cls, txt]) => {
    const span = document.createElement("span");
    const sw = document.createElement("span");
    sw.className = cls;
    span.appendChild(sw);
    span.appendChild(document.createTextNode(" " + txt));
    legend.appendChild(span);
  });
  root.appendChild(legend);

  const missingNote = document.createElement("p");
  missingNote.className = "chart-footnote";
  root.appendChild(missingNote);

  const explainer = document.createElement("div");
  explainer.className = "chart-explainer";
  explainer.append("Valence", document.createTextNode(" measures musical positivity (sad → happy on a 0–1 scale). "));
  const e2 = document.createElement("b"); e2.textContent = "Energy"; explainer.appendChild(e2);
  explainer.append(document.createTextNode(" measures intensity. Both are computed by Spotify per song and averaged over an act's tracks."));
  // (Replace simple "Valence" text with a <b>)
  explainer.firstChild.remove();
  const e1 = document.createElement("b"); e1.textContent = "Valence";
  explainer.insertBefore(e1, explainer.firstChild);
  root.appendChild(explainer);

  // Chart axes
  const W = 680, H = 500;
  const g = svg("g", { transform: "translate(60,30)" });
  svgEl.appendChild(g);

  svgText(g, 20, 20, "High Energy / Sad", "chart-quad-label");
  svgText(g, 540, 20, "High Energy / Happy", "chart-quad-label", "end");
  svgText(g, 20, 490, "Low Energy / Sad", "chart-quad-label");
  svgText(g, 540, 490, "Low Energy / Happy", "chart-quad-label", "end");
  [125, 250, 375].forEach(y => svgLine(g, 0, y, 680, y, "chart-tick"));
  [170, 340, 510].forEach(x => svgLine(g, x, 0, x, 500, "chart-tick"));
  svgLine(g, 0, 500, 680, 500, "chart-axis");
  svgLine(g, 0, 0, 0, 500, "chart-axis");

  ["0", ".25", ".5", ".75", "1"].forEach((t, i) => {
    svgText(g, -8, 504 - i * 125, t, "chart-axis-num", "end");
    svgText(g, i * 170, 518, t, "chart-axis-num", "middle");
  });
  svgText(g, 340, 545, "Valence (musical positivity →)", "chart-axis-label", "middle");
  const yLab = svg("text", { x: -25, y: 250, class: "chart-axis-label", "text-anchor": "middle", transform: "rotate(-90, -25, 250)" });
  yLab.textContent = "Energy";
  g.appendChild(yLab);

  const dotsLayer = svg("g", {});
  g.appendChild(dotsLayer);

  function rank(p) { return isMedal(p) ? 3 : (p && p.includes && p.includes("Pigskin")) ? 2 : 1; }

  function draw() {
    while (dotsLayer.firstChild) dotsLayer.removeChild(dotsLayer.firstChild);
    const visible = plottable
      .filter(d => activeYear === "all" || d.year === parseInt(activeYear))
      .sort((a, b) => rank(a.placement) - rank(b.placement));

    visible.forEach(d => {
      const cx = d.valence * W;
      const cy = (1 - d.energy) * H;
      const medal = isMedal(d.placement);
      const pigskin = !medal && d.placement && d.placement.includes("Pigskin");
      const r = medal ? 10 : pigskin ? 8 : 6;
      const grp = svg("g", {});
      const fill = isYTSource(d) ? d.dominant : "#555";
      const c = svg("circle", { cx, cy, r, fill, stroke: "#000", "stroke-width": 1, class: "chart-dot" });
      grp.appendChild(c);

      if (medal) {
        const r1 = svg("circle", { cx, cy, r: r + 4, class: "chart-ring-gold", style: "opacity:.95" });
        const r2 = svg("circle", { cx, cy, r: r + 7, class: "chart-ring-gold", style: "opacity:.55" });
        grp.appendChild(r1); grp.appendChild(r2);
        const lbl = svg("text", { x: cx + 14, y: cy + 4, class: "chart-label-medal" });
        lbl.textContent = d.placement;
        grp.appendChild(lbl);
      } else if (pigskin) {
        grp.appendChild(svg("circle", { cx, cy, r: r + 3, class: "chart-ring-bronze" }));
      }

      grp.addEventListener("mousemove", ev => showTip(ev, d));
      grp.addEventListener("mouseleave", hideTip);
      dotsLayer.appendChild(grp);
    });

    const miss = missing.filter(m => activeYear === "all" || m.year === parseInt(activeYear));
    if (miss.length) {
      missingNote.textContent = "Not on map (no audio data): " + miss.map(m => m.year + " " + m.group).join(" · ");
    } else {
      missingNote.textContent = "";
    }
  }

  function showTip(ev, d) {
    while (tooltip.firstChild) tooltip.removeChild(tooltip.firstChild);
    tooltip.style.opacity = "1";
    tooltip.style.left = (ev.clientX + 14) + "px";
    tooltip.style.top = (ev.clientY + 14) + "px";
    const h = document.createElement("h4");
    h.textContent = d.group + (d.theme ? " — " + d.theme : "");
    tooltip.appendChild(h);
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = `${d.year} · ${d.placement} · valence ${d.valence.toFixed(2)} · energy ${d.energy.toFixed(2)}`;
    tooltip.appendChild(meta);
    const sw = document.createElement("div");
    sw.className = "swatches";
    if (isYTSource(d)) {
      d.palette.slice(0, 6).forEach(hh => {
        const cc = document.createElement("div");
        cc.style.background = hh;
        sw.appendChild(cc);
      });
    } else {
      const i = document.createElement("i");
      i.style.color = "var(--text-tertiary)";
      i.style.fontSize = "10px";
      i.textContent = "no real palette";
      sw.appendChild(i);
    }
    tooltip.appendChild(sw);
  }
  function hideTip() { tooltip.style.opacity = "0"; }

  draw();

  return {
    highlight(matchFn) {
      // Pulse matching dot
      const dots = dotsLayer.querySelectorAll("g");
      dots.forEach((grp) => {
        const idx = Array.from(dotsLayer.children).indexOf(grp);
        // can't index plottable safely after sort; instead match via stored data
      });
      // Re-walk: rebuild with highlight
      const matched = plottable.filter(matchFn);
      matched.forEach(d => {
        // Find the circle at that x,y by scanning current dots
        const cx = d.valence * W;
        const cy = (1 - d.energy) * H;
        dotsLayer.querySelectorAll("circle.chart-dot").forEach(c => {
          if (Math.abs(parseFloat(c.getAttribute("cx")) - cx) < 0.1 &&
              Math.abs(parseFloat(c.getAttribute("cy")) - cy) < 0.1) {
            c.classList.add("highlight-pulse");
            setTimeout(() => c.classList.remove("highlight-pulse"), 2000);
          }
        });
      });
    },
  };
}
