// site/js/charts/palette_stacks.js
import { isYTSource, isMedal } from "../data.js";

export function render(root, acts) {
  const valid = acts.filter(isYTSource);

  // Tooltip lives once at root level
  let tip = root.querySelector(".ps-tooltip");
  if (!tip) {
    tip = document.createElement("div");
    tip.className = "ps-tooltip";
    root.appendChild(tip);
  }

  const allTiles = [];

  function build() {
    // Clear everything except the tooltip
    Array.from(root.children).forEach(c => { if (c !== tip) root.removeChild(c); });
    allTiles.length = 0;

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
        mini.dataset.year = a.year;
        mini.dataset.group = a.group;
        a.palette.forEach((h, i) => {
          const seg = document.createElement("div");
          seg.style.background = h;
          seg.style.flex = String(a.props[i] || 0.05);
          mini.appendChild(seg);
        });
        mini.addEventListener("mousemove", ev => {
          tip.style.opacity = "1";
          tip.style.left = (ev.clientX + 14) + "px";
          tip.style.top = (ev.clientY + 14) + "px";
          while (tip.firstChild) tip.removeChild(tip.firstChild);
          const h4 = document.createElement("h4");
          h4.textContent = a.group + (a.theme ? " — " + a.theme : "");
          tip.appendChild(h4);
          const meta = document.createElement("div");
          meta.className = "meta";
          meta.textContent = `${a.year} · ${a.placement}`;
          tip.appendChild(meta);
          const sw = document.createElement("div");
          sw.className = "swatches";
          a.palette.slice(0, 6).forEach(hh => {
            const c = document.createElement("div");
            c.style.background = hh;
            sw.appendChild(c);
          });
          tip.appendChild(sw);
        });
        mini.addEventListener("mouseleave", () => { tip.style.opacity = "0"; });
        mini.addEventListener("click", () => {
          document.dispatchEvent(new CustomEvent("focus-act", { detail: { year: a.year, group: a.group } }));
        });
        strip.appendChild(mini);
        allTiles.push({ act: a, el: mini });
      });
      row.appendChild(strip);
      root.appendChild(row);
    });
  }
  build();

  function applyFocus(matchFn) {
    allTiles.forEach(({ act, el }) => {
      el.classList.remove("focused", "dimmed");
      if (!matchFn) return;
      if (matchFn(act)) el.classList.add("focused");
      else el.classList.add("dimmed");
    });
  }

  return {
    highlight(matchFn) { applyFocus(matchFn); },
    reset() { applyFocus(null); },
  };
}
