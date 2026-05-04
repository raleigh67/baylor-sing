import { loadActs } from "./data.js";
import { render as renderCastGrid } from "./charts/cast_grid.js";
import { render as renderAudioMap } from "./charts/audio_map.js";
import { render as renderTopArtists } from "./charts/top_artists.js";
import { render as renderSongAge } from "./charts/song_age.js";
import { render as renderGenre } from "./charts/genre_proportions.js";
import { render as renderPaletteStacks } from "./charts/palette_stacks.js";
import { render as renderColorWheel } from "./charts/color_wheel.js";
import { render as renderSatVal } from "./charts/sat_val_scatter.js";
import { render as renderExtremes } from "./charts/extremes.js";

const charts = {};

async function init() {
  const acts = await loadActs();
  console.log(`loaded ${acts.length} acts`);
  requestAnimationFrame(() => {
    document.getElementById("scene-curtain").classList.add("curtains-open");
  });
  charts.castGrid = renderCastGrid(document.getElementById("cast-grid"), acts);
  charts.audioMap = renderAudioMap(document.getElementById("audio-map"), acts);
  renderTopArtists(document.getElementById("top-artists"), acts);
  renderSongAge(document.getElementById("song-age"), acts);
  renderGenre(document.getElementById("genre-proportions"), acts);
  renderPaletteStacks(document.getElementById("palette-stacks"), acts);
  renderColorWheel(document.getElementById("color-wheel"), acts);
  renderSatVal(document.getElementById("sat-val-scatter"), acts);
  renderExtremes(document.getElementById("extremes"), acts);
  window.__sing = { acts, charts };
}
init();
