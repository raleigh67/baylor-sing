// site_v2/js/main.js
import { loadActs } from "./data.js";

const charts = {};

async function init() {
  const acts = await loadActs();
  console.log(`loaded ${acts.length} acts`);
  requestAnimationFrame(() => {
    document.getElementById("scene-curtain").classList.add("curtains-open");
  });
  window.__sing = { acts, charts };
}

init();
