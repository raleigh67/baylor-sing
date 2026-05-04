import { loadActs, isMedal, isPigskin } from "./data.js";
import { render as renderCastGrid } from "./charts/cast_grid.js";
import { render as renderAudioMap } from "./charts/audio_map.js";
import { render as renderTopArtists } from "./charts/top_artists.js";
import { render as renderSongAge } from "./charts/song_age.js";
import { render as renderGenre } from "./charts/genre_proportions.js";
import { render as renderPaletteStacks } from "./charts/palette_stacks.js";
import { render as renderColorWheel } from "./charts/color_wheel.js";
import { render as renderSatVal } from "./charts/sat_val_scatter.js";
import { render as renderExtremes } from "./charts/extremes.js";
import { render as renderWvP } from "./charts/winner_vs_participant.js";

const charts = {};

const PLACE_RANK = { "1st": 1, "2nd": 2, "3rd": 3, "Pigskin": 4 };

function renderPigskinReveal(root, acts) {
  const top = acts
    .filter(a => a.placement && (isMedal(a.placement) || a.placement.includes("Pigskin")))
    .sort((a, b) => a.year - b.year || (PLACE_RANK[a.placement] || 9) - (PLACE_RANK[b.placement] || 9));
  const medals = top.filter(a => isMedal(a.placement));
  const golds = top.filter(a => a.placement === "1st");

  while (root.firstChild) root.removeChild(root.firstChild);

  const headline = document.createElement("div");
  headline.className = "verdict-headline";
  [
    [`${top.length} acts made `, "Pigskin", "."],
    [`${medals.length} took home `, "medals", "."],
    [`${golds.length} were `, "crowned", "."],
  ].forEach(parts => {
    const div = document.createElement("div");
    div.append(parts[0]);
    const it = document.createElement("i"); it.textContent = parts[1];
    div.appendChild(it);
    div.append(parts[2]);
    headline.appendChild(div);
  });
  root.appendChild(headline);

  const grid = document.createElement("div");
  grid.className = "verdict-grid";
  top.forEach(a => {
    const card = document.createElement("div");
    card.className = "verdict-tile " + (isMedal(a.placement) ? "vt-medal" : "vt-pigskin");
    if (a.placement === "1st") card.classList.add("vt-gold");

    const strip = document.createElement("div");
    strip.className = "vt-strip";
    a.palette.slice(0, 6).forEach((h, i) => {
      const seg = document.createElement("div");
      seg.style.background = h;
      seg.style.flex = String(a.props[i] || 0.05);
      strip.appendChild(seg);
    });
    card.appendChild(strip);

    const body = document.createElement("div");
    body.className = "vt-body";
    const placement = document.createElement("div");
    placement.className = "vt-placement";
    placement.textContent = a.placement;
    body.appendChild(placement);
    const name = document.createElement("div");
    name.className = "vt-name";
    name.textContent = a.group;
    body.appendChild(name);
    const meta = document.createElement("div");
    meta.className = "vt-meta";
    meta.textContent = a.year + (a.theme ? " · " + a.theme : "");
    body.appendChild(meta);
    card.appendChild(body);

    grid.appendChild(card);
  });
  root.appendChild(grid);
}

function renderFirstPlaceSpotlights(root, acts) {
  const golds = acts.filter(a => a.placement === "1st").sort((a, b) => a.year - b.year);
  while (root.firstChild) root.removeChild(root.firstChild);
  const h3 = document.createElement("h3"); h3.className = "spotlight-h"; h3.textContent = "First-Place Acts";
  root.appendChild(h3);
  const grid = document.createElement("div"); grid.className = "spotlight-grid";
  golds.forEach(a => {
    const card = document.createElement("div"); card.className = "spotlight-card";
    const yr = document.createElement("div"); yr.className = "spotlight-yr";
    const yrIt = document.createElement("i"); yrIt.textContent = String(a.year); yr.appendChild(yrIt);
    card.appendChild(yr);
    const name = document.createElement("div"); name.className = "spotlight-name"; name.textContent = a.group;
    card.appendChild(name);
    if (a.theme) {
      const theme = document.createElement("div"); theme.className = "spotlight-theme";
      const it = document.createElement("i"); it.textContent = `"${a.theme}"`;
      theme.appendChild(it);
      card.appendChild(theme);
    }
    const strip = document.createElement("div"); strip.className = "spotlight-strip";
    a.palette.slice(0, 8).forEach((h, i) => {
      const seg = document.createElement("div");
      seg.style.background = h;
      seg.style.flex = String(a.props[i] || 0.05);
      strip.appendChild(seg);
    });
    card.appendChild(strip);
    grid.appendChild(card);
  });
  root.appendChild(grid);
}

function renderEncore(root, acts) {
  const vals = acts.map(a => a.valence).filter(v => v != null);
  const avgVal = vals.reduce((s, v) => s + v, 0) / vals.length;

  const counts = new Map();
  acts.forEach(a => {
    if (!a.songs) return;
    a.songs.split(";").forEach(s => {
      const m = s.match(/\(([^)]+)\)\s*$/);
      if (m) counts.set(m[1].trim(), (counts.get(m[1].trim()) || 0) + 1);
    });
  });
  const [topArtist, topCount] = [...counts.entries()].sort((a, b) => b[1] - a[1])[0] || ["—", 0];

  const yearAvgSat = {};
  [2022, 2023, 2024, 2025].forEach(yr => {
    const yt = acts.filter(a => a.year === yr && a.palette_source === "youtube");
    yearAvgSat[yr] = yt.length ? yt.reduce((s, a) => s + a.avg_sat, 0) / yt.length : 0;
  });
  const vividYear = Object.entries(yearAvgSat).sort((a, b) => b[1] - a[1])[0][0];

  while (root.firstChild) root.removeChild(root.firstChild);
  function bignum(num, capParts) {
    const div = document.createElement("div");
    div.className = "bignum";
    const n = document.createElement("div");
    n.className = "bn-num";
    n.textContent = num;
    div.appendChild(n);
    const cap = document.createElement("div");
    cap.className = "bn-cap";
    capParts.forEach(p => {
      if (typeof p === "string") cap.append(p);
      else { const it = document.createElement("i"); it.textContent = p.italic; cap.appendChild(it); }
    });
    div.appendChild(cap);
    root.appendChild(div);
  }

  bignum(`${(avgVal * 100).toFixed(0)}%`, ["average valence — happier than three out of four pop songs."]);
  bignum(String(topCount), ["acts covered ", { italic: topArtist }, " — the most-covered artist of the era."]);
  bignum(vividYear, ["the most vivid year on stage."]);
}

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
  renderPigskinReveal(document.getElementById("pigskin-reveal"), acts);
  renderWvP(document.getElementById("winner-vs-participant"), acts);
  renderFirstPlaceSpotlights(document.getElementById("first-place-spotlights"), acts);
  renderEncore(document.getElementById("big-numbers"), acts);
  window.__sing = { acts, charts };

  document.addEventListener("cast-tile-click", e => {
    const { year, group } = e.detail;
    const audioMap = document.getElementById("audio-map");
    audioMap.scrollIntoView({ behavior: "smooth", block: "center" });
    setTimeout(() => {
      if (charts.audioMap && charts.audioMap.highlight) {
        charts.audioMap.highlight(d => d.year === year && d.group === group);
      }
    }, 700);
  });
}
init();
