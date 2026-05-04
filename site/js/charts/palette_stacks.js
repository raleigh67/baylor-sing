// site_v2/js/charts/palette_stacks.js
import { isYTSource, isMedal } from "../data.js";

export function render(root, acts) {
  const valid = acts.filter(isYTSource);
  while (root.firstChild) root.removeChild(root.firstChild);
  [2022, 2023, 2024, 2025].forEach(yr => {
    const subset = valid.filter(a => a.year === yr).sort((a, b) => a.group.localeCompare(b.group));
    const row = document.createElement("div");
    row.className = "ps-row";
    const yrLab = document.createElement("div");
    yrLab.className = "ps-yr";
    const it = document.createElement("i");
    it.textContent = String(yr);
    yrLab.appendChild(it);
    row.appendChild(yrLab);

    const strip = document.createElement("div");
    strip.className = "ps-strip";
    subset.forEach(a => {
      const mini = document.createElement("div");
      mini.className = "ps-act";
      if (isMedal(a.placement)) mini.classList.add("ps-medal");
      mini.title = a.group + (a.theme ? " — " + a.theme : "") + " · " + a.placement;
      a.palette.forEach((h, i) => {
        const seg = document.createElement("div");
        seg.style.background = h;
        seg.style.flex = String(a.props[i] || 0.05);
        mini.appendChild(seg);
      });
      strip.appendChild(mini);
    });
    row.appendChild(strip);
    root.appendChild(row);
  });
}
