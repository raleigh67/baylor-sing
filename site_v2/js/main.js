import { loadActs } from "./data.js";
import { render as renderCastGrid } from "./charts/cast_grid.js";
import { render as renderAudioMap } from "./charts/audio_map.js";

const charts = {};

async function init() {
  const acts = await loadActs();
  console.log(`loaded ${acts.length} acts`);
  requestAnimationFrame(() => {
    document.getElementById("scene-curtain").classList.add("curtains-open");
  });
  charts.castGrid = renderCastGrid(document.getElementById("cast-grid"), acts);
  charts.audioMap = renderAudioMap(document.getElementById("audio-map"), acts);
  window.__sing = { acts, charts };
}
init();
