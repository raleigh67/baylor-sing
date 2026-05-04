// site_v2/js/charts/cast_grid.js
import { isMedal, hexToHsv, PLACEMENT_ORDER } from "../data.js";

export function render(root, acts) {
  let mode = "year";

  function order(list) {
    if (mode === "year") return [...list].sort((a, b) => a.year - b.year || a.group.localeCompare(b.group));
    if (mode === "placement") return [...list].sort((a, b) =>
      (PLACEMENT_ORDER[a.placement] || 9) - (PLACEMENT_ORDER[b.placement] || 9) || a.year - b.year);
    if (mode === "hue") return [...list].sort((a, b) => hexToHsv(a.dominant).h - hexToHsv(b.dominant).h);
    return list;
  }

  function makeTile(a) {
    const tile = document.createElement("div");
    tile.className = "cast-tile";
    tile.dataset.year = a.year;
    tile.dataset.group = a.group;
    if (a.palette_source !== "youtube") tile.classList.add("cast-tile-bing");

    const strip = document.createElement("div");
    strip.className = "cast-tile-strip";
    if (a.palette_source === "youtube") {
      a.palette.forEach((h, i) => {
        const seg = document.createElement("div");
        seg.style.background = h;
        seg.style.flex = String(a.props[i] || 0.05);
        strip.appendChild(seg);
      });
    } else {
      ["#1a1a1a", "#2a2a2a", "#3a3a3a", "#4a4a4a", "#5a5a5a"].forEach(g => {
        const seg = document.createElement("div");
        seg.style.background = g;
        seg.style.flex = "1";
        strip.appendChild(seg);
      });
    }
    tile.appendChild(strip);

    const body = document.createElement("div");
    body.className = "cast-tile-body";
    const dom = document.createElement("div");
    dom.className = "cast-dom";
    dom.style.background = a.palette_source === "youtube" ? a.dominant : "#444";
    body.appendChild(dom);

    const txt = document.createElement("div");
    txt.className = "cast-text";
    const groupEl = document.createElement("div");
    groupEl.className = "cast-group";
    groupEl.textContent = a.group;
    txt.appendChild(groupEl);

    const meta = document.createElement("div");
    meta.className = "cast-meta";
    if (a.theme) {
      const themeEl = document.createElement("i");
      themeEl.textContent = a.theme;
      meta.appendChild(themeEl);
      meta.appendChild(document.createTextNode(" · "));
    }
    const placementEl = document.createElement("span");
    placementEl.textContent = a.placement;
    if (isMedal(a.placement)) placementEl.className = "placement-medal";
    else if (a.placement && a.placement.includes("Pigskin")) placementEl.className = "placement-pigskin";
    meta.appendChild(placementEl);
    if (a.palette_source !== "youtube") {
      const badge = document.createElement("span");
      badge.className = "badge-no-video";
      badge.textContent = "no video";
      meta.appendChild(document.createTextNode(" "));
      meta.appendChild(badge);
    }
    txt.appendChild(meta);
    body.appendChild(txt);
    tile.appendChild(body);

    tile.addEventListener("click", () => {
      const ev = new CustomEvent("cast-tile-click", { detail: { year: a.year, group: a.group } });
      document.dispatchEvent(ev);
    });
    return tile;
  }

  function build() {
    while (root.firstChild) root.removeChild(root.firstChild);
    const ordered = order(acts);
    if (mode === "year") {
      [2022, 2023, 2024, 2025].forEach(yr => {
        const subset = ordered.filter(a => a.year === yr);
        const row = document.createElement("div");
        row.className = "yr-row";
        const lab = document.createElement("h3");
        lab.className = "yr-label";
        const it = document.createElement("i");
        it.textContent = String(yr);
        lab.appendChild(it);
        const cnt = document.createElement("span");
        cnt.className = "yr-count";
        cnt.textContent = ` (${subset.length})`;
        lab.appendChild(cnt);
        row.appendChild(lab);
        const grid = document.createElement("div");
        grid.className = "yr-grid";
        subset.forEach(a => grid.appendChild(makeTile(a)));
        row.appendChild(grid);
        root.appendChild(row);
      });
    } else {
      const grid = document.createElement("div");
      grid.className = "yr-grid";
      ordered.forEach(a => grid.appendChild(makeTile(a)));
      root.appendChild(grid);
    }
  }

  document.querySelectorAll(".sort-btn").forEach(b => {
    b.addEventListener("click", () => {
      document.querySelectorAll(".sort-btn").forEach(x => x.classList.remove("active"));
      b.classList.add("active");
      mode = b.dataset.sort;
      build();
    });
  });

  build();
  return { build };
}
