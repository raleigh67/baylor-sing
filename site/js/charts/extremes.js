// site_v2/js/charts/extremes.js
import { isYTSource, hexToHsv } from "../data.js";

export function render(root, acts) {
  const valid = acts.filter(isYTSource);
  if (valid.length === 0) return;
  const mostVivid = [...valid].sort((a, b) => {
    const av = hexToHsv(a.dominant);
    const bv = hexToHsv(b.dominant);
    return (bv.s * bv.v) - (av.s * av.v);
  })[0];
  const mostMuted = [...valid].sort((a, b) => a.avg_sat - b.avg_sat)[0];
  const brightest = [...valid].sort((a, b) => b.avg_val - a.avg_val)[0];
  const darkest = [...valid].sort((a, b) => a.avg_val - b.avg_val)[0];

  while (root.firstChild) root.removeChild(root.firstChild);
  const grid = document.createElement("div");
  grid.className = "extremes-grid";
  [
    ["Most Vivid", mostVivid],
    ["Most Muted", mostMuted],
    ["Brightest", brightest],
    ["Darkest", darkest],
  ].forEach(([lab, d]) => {
    const card = document.createElement("div");
    card.className = "extreme-card";
    const labEl = document.createElement("div");
    labEl.className = "extreme-label";
    labEl.textContent = lab;
    card.appendChild(labEl);
    const swatch = document.createElement("div");
    swatch.className = "extreme-swatch";
    swatch.style.background = d.dominant;
    card.appendChild(swatch);
    const name = document.createElement("div");
    name.className = "extreme-name";
    name.textContent = `${d.year} · ${d.group}`;
    card.appendChild(name);
    const meta = document.createElement("div");
    meta.className = "extreme-meta";
    meta.textContent = d.theme || d.placement;
    card.appendChild(meta);
    grid.appendChild(card);
  });
  root.appendChild(grid);
}
