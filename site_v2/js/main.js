import { loadActs } from "./data.js";
import { render as renderCastGrid } from "./charts/cast_grid.js";

const charts = {};

async function init() {
  const acts = await loadActs();
  console.log(`loaded ${acts.length} acts`);
  requestAnimationFrame(() => {
    document.getElementById("scene-curtain").classList.add("curtains-open");
  });
  charts.castGrid = renderCastGrid(document.getElementById("cast-grid"), acts);
  window.__sing = { acts, charts };
}
init();
