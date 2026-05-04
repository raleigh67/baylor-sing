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
    card.dataset.year = a.year;
    card.dataset.group = a.group;
    card.style.cursor = "pointer";
    card.addEventListener("click", () => {
      document.dispatchEvent(new CustomEvent("focus-act", { detail: { year: a.year, group: a.group } }));
    });

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
  // === Derive a slate of facts ===
  const audioActs = acts.filter(a => a.valence != null);
  const ytActs = acts.filter(a => a.palette_source === "youtube");
  const avgVal = audioActs.reduce((s, a) => s + a.valence, 0) / (audioActs.length || 1);
  const avgEnergy = audioActs.reduce((s, a) => s + a.energy, 0) / (audioActs.length || 1);

  // Most-covered artist
  const artistCounts = new Map();
  acts.forEach(a => {
    if (!a.songs) return;
    a.songs.split(";").forEach(s => {
      const m = s.match(/\(([^)]+)\)\s*$/);
      if (m) artistCounts.set(m[1].trim(), (artistCounts.get(m[1].trim()) || 0) + 1);
    });
  });
  const sortedArtists = [...artistCounts.entries()].sort((a, b) => b[1] - a[1]);
  const [topArtist, topCount] = sortedArtists[0] || ["—", 0];

  // Most-covered song title
  const songCounts = new Map();
  acts.forEach(a => {
    if (!a.songs) return;
    a.songs.split(";").forEach(s => {
      const m = s.match(/^(.+?)\s*\(([^)]+)\)\s*$/);
      const title = (m ? m[1] : s).trim().toLowerCase();
      if (title) songCounts.set(title, (songCounts.get(title) || 0) + 1);
    });
  });
  const repeatedSongs = [...songCounts.entries()].filter(([, n]) => n > 1).sort((a, b) => b[1] - a[1]);

  // Most-vivid + most-muted year
  const yearAvgSat = {};
  [2022, 2023, 2024, 2025].forEach(yr => {
    const yt = ytActs.filter(a => a.year === yr);
    yearAvgSat[yr] = yt.length ? yt.reduce((s, a) => s + a.avg_sat, 0) / yt.length : 0;
  });
  const vividYearSorted = Object.entries(yearAvgSat).sort((a, b) => b[1] - a[1]);
  const vividYear = vividYearSorted[0][0];

  // Group most appearances
  const groupCounts = new Map();
  acts.forEach(a => groupCounts.set(a.group, (groupCounts.get(a.group) || 0) + 1));
  const [topGroup, topGroupCount] = [...groupCounts.entries()].sort((a, b) => b[1] - a[1])[0];
  const topGroupAct = acts.find(a => a.group === topGroup);

  // Oldest song performed
  let oldestSong = null;
  acts.forEach(a => (a.song_ages || []).forEach(s => {
    if (!oldestSong || s.age > oldestSong.age) oldestSong = { ...s, act: a };
  }));

  // Average song age
  const allSongAges = acts.flatMap(a => (a.song_ages || []).map(s => s.age));
  const avgSongAge = allSongAges.reduce((s, x) => s + x, 0) / (allSongAges.length || 1);

  // Most-danceable + highest-tempo + most-energetic acts
  const mostDanceable = [...audioActs].sort((a, b) => b.danceability - a.danceability)[0];
  const fastestTempo = [...audioActs].filter(a => a.tempo).sort((a, b) => b.tempo - a.tempo)[0];
  const mostEnergetic = [...audioActs].sort((a, b) => b.energy - a.energy)[0];

  // Joint acts
  const jointActs = acts.filter(a => /\s(&|and)\s/i.test(a.group)).length;

  // Unique artists count
  const uniqueArtists = artistCounts.size;

  // Average song popularity
  const popVals = acts.map(a => a.popularity).filter(v => v != null);
  const avgPopularity = popVals.reduce((s, v) => s + v, 0) / (popVals.length || 1);

  // === Render ===
  while (root.firstChild) root.removeChild(root.firstChild);

  const grid = document.createElement("div");
  grid.className = "encore-grid";
  root.appendChild(grid);

  function card(cls, builderFn) {
    const c = document.createElement("div");
    c.className = "encore-card " + cls;
    builderFn(c);
    grid.appendChild(c);
  }

  function num(parent, txt) {
    const n = document.createElement("div"); n.className = "encore-num"; n.textContent = txt; parent.appendChild(n); return n;
  }
  function lab(parent, txt) {
    const l = document.createElement("div"); l.className = "encore-lab"; l.textContent = txt; parent.appendChild(l); return l;
  }
  function cap(parent, parts) {
    const c = document.createElement("div"); c.className = "encore-cap";
    parts.forEach(p => {
      if (typeof p === "string") c.append(p);
      else { const it = document.createElement("i"); it.textContent = p.italic; c.appendChild(it); }
    });
    parent.appendChild(c);
  }
  function strip(parent, palette, props) {
    const s = document.createElement("div"); s.className = "encore-strip";
    palette.slice(0, 6).forEach((h, i) => {
      const seg = document.createElement("div");
      seg.style.background = h;
      seg.style.flex = String(props[i] || 0.05);
      s.appendChild(seg);
    });
    parent.appendChild(s);
  }

  // 1. Average valence — wide hero card
  card("ec-hero", c => {
    num(c, `${(avgVal * 100).toFixed(0)}%`);
    cap(c, ["average ", { italic: "valence" }, ` across ${audioActs.length} acts — Sing leans bright and major-key, happier than three out of four pop songs.`]);
  });

  // 2. Top artist
  card("", c => {
    lab(c, "Most-covered artist");
    num(c, topArtist);
    cap(c, [`${topCount} acts pulled at least one of their songs.`]);
  });

  // 3. Most-vivid year
  card("", c => {
    lab(c, "Most vivid year");
    num(c, vividYear);
    cap(c, [`${(yearAvgSat[vividYear] * 100).toFixed(0)}% average saturation across the year's palettes.`]);
  });

  // 4. Most-appearing group with palette
  card("ec-with-strip", c => {
    lab(c, "Most appearances");
    num(c, topGroup);
    cap(c, [`${topGroupCount} acts in four years` + (topGroupAct ? ` — palette below from their ${topGroupAct.year} act.` : ".")]);
    if (topGroupAct) strip(c, topGroupAct.palette, topGroupAct.props);
  });

  // 5. Oldest song
  if (oldestSong) {
    card("", c => {
      lab(c, "The oldest cover");
      num(c, `${oldestSong.age} yrs`);
      cap(c, [{ italic: oldestSong.title }, ` (${oldestSong.release_year}) — ${oldestSong.act.year} ${oldestSong.act.group}.`]);
    });
  }

  // 6. Most danceable
  if (mostDanceable) {
    card("ec-with-strip", c => {
      lab(c, "Most danceable");
      num(c, mostDanceable.group);
      cap(c, [`Danceability ${mostDanceable.danceability.toFixed(2)} · ${mostDanceable.year}` + (mostDanceable.theme ? ` "${mostDanceable.theme}"` : "")]);
      strip(c, mostDanceable.palette, mostDanceable.props);
    });
  }

  // 7. Fastest tempo
  if (fastestTempo) {
    card("", c => {
      lab(c, "Fastest tempo");
      num(c, `${Math.round(fastestTempo.tempo)} BPM`);
      cap(c, [`${fastestTempo.year} ${fastestTempo.group}` + (fastestTempo.theme ? ` — ${fastestTempo.theme}` : "")]);
    });
  }

  // 8. Most energetic
  if (mostEnergetic) {
    card("", c => {
      lab(c, "Most energetic");
      num(c, mostEnergetic.group);
      cap(c, [`Energy ${mostEnergetic.energy.toFixed(2)} · ${mostEnergetic.year}` + (mostEnergetic.theme ? ` "${mostEnergetic.theme}"` : "")]);
    });
  }

  // 9. Repeated songs (mini list)
  if (repeatedSongs.length > 0) {
    card("ec-list", c => {
      lab(c, "Songs covered more than once");
      const ul = document.createElement("ul");
      ul.className = "encore-list";
      repeatedSongs.slice(0, 5).forEach(([title, n]) => {
        const li = document.createElement("li");
        const t = document.createElement("span"); t.className = "ec-li-title"; t.textContent = title.replace(/\b\w/g, c => c.toUpperCase());
        const v = document.createElement("span"); v.className = "ec-li-count"; v.textContent = `× ${n}`;
        li.appendChild(t); li.appendChild(v);
        ul.appendChild(li);
      });
      c.appendChild(ul);
    });
  }

  // 10. Average song age
  card("", c => {
    lab(c, "Average song age");
    num(c, `${avgSongAge.toFixed(1)} yrs`);
    cap(c, [`Across ${allSongAges.length} songs · oldest 25 yrs, freshest released the same year as the show.`]);
  });

  // 11. Unique artists
  card("", c => {
    lab(c, "Unique artists covered");
    num(c, String(uniqueArtists));
    cap(c, [`${acts.reduce((s, a) => s + a.song_count, 0)} total song slots filled across ${acts.length} acts.`]);
  });

  // 12. Joint acts
  if (jointActs > 0) {
    card("", c => {
      lab(c, "Joint acts");
      num(c, String(jointActs));
      cap(c, [`Two-group collaborations across the four years.`]);
    });
  }

  // 13. Spotify popularity avg
  card("", c => {
    lab(c, "Average song popularity");
    num(c, `${avgPopularity.toFixed(0)}/100`);
    cap(c, [`Spotify's 0–100 popularity score, averaged. Sing acts skew toward songs with broad reach.`]);
  });
}

async function init() {
  const acts = await loadActs();
  console.log(`loaded ${acts.length} acts`);
  requestAnimationFrame(() => {
    document.getElementById("scene-curtain").classList.add("curtains-open");
  });
  charts.castGrid = renderCastGrid(document.getElementById("cast-grid"), acts);
  charts.audioMap = renderAudioMap(document.getElementById("audio-map"), acts);
  charts.topArtists = renderTopArtists(document.getElementById("top-artists"), acts);
  charts.songAge = renderSongAge(document.getElementById("song-age"), acts);
  charts.genre = renderGenre(document.getElementById("genre-proportions"), acts);
  charts.paletteStacks = renderPaletteStacks(document.getElementById("palette-stacks"), acts);
  charts.colorWheel = renderColorWheel(document.getElementById("color-wheel"), acts);
  charts.satVal = renderSatVal(document.getElementById("sat-val-scatter"), acts);
  renderExtremes(document.getElementById("extremes"), acts);
  renderPigskinReveal(document.getElementById("pigskin-reveal"), acts);
  renderFirstPlaceSpotlights(document.getElementById("first-place-spotlights"), acts);
  renderEncore(document.getElementById("big-numbers"), acts);
  window.__sing = { acts, charts };

  // === Per-act focus: click a cast tile (or any chart dot) -> filter all downstream ===
  const focusBar = document.getElementById("selected-act-bar");
  const focusName = focusBar.querySelector(".selected-name");
  const focusClear = focusBar.querySelector(".selected-clear");

  function setFocus(year, group) {
    const matchFn = d => d.year === year && d.group === group;
    const act = acts.find(matchFn);
    if (!act) return;
    focusBar.hidden = false;
    focusName.textContent = `${act.year} ${act.group}` + (act.theme ? ` — ${act.theme}` : "");
    Object.values(charts).forEach(c => { if (c && c.highlight) c.highlight(matchFn); });
    // Tag cast/verdict tiles too (they're DOM-level, not chart instances)
    document.querySelectorAll(".cast-tile, .verdict-tile").forEach(el => {
      el.classList.remove("focused", "dimmed");
      const matches = String(el.dataset.year || "") === String(year)
        && String(el.dataset.group || "") === String(group);
      if (matches) el.classList.add("focused");
      else el.classList.add("dimmed");
    });
  }
  function clearFocus() {
    focusBar.hidden = true;
    Object.values(charts).forEach(c => { if (c && c.reset) c.reset(); });
    document.querySelectorAll(".cast-tile, .verdict-tile").forEach(el => {
      el.classList.remove("focused", "dimmed");
    });
  }
  focusClear.addEventListener("click", clearFocus);

  document.addEventListener("cast-tile-click", e => {
    const { year, group } = e.detail;
    setFocus(year, group);
    document.getElementById("scene-sound").scrollIntoView({ behavior: "smooth", block: "start" });
  });
  document.addEventListener("focus-act", e => {
    const { year, group } = e.detail;
    setFocus(year, group);
  });

  // scrollama is a UMD bundle; it attaches `scrollama` to window
  const script = document.createElement("script");
  script.src = "js/scrollama.min.js";
  script.onload = () => {
    const scroller = window.scrollama();
    scroller.setup({ step: ".scene", offset: 0.5 }).onStepEnter(({ element }) => {
      document.querySelectorAll(".scene").forEach(s => s.classList.remove("in-view"));
      element.classList.add("in-view");
    });
    window.addEventListener("resize", () => scroller.resize());
  };
  document.head.appendChild(script);
}
init();
