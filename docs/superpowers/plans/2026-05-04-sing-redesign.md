# Sing Site Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a new theatrical scrollytelling site at `site_v2/` that uses real per-act color palettes alongside Spotify audio features to tell the story of Baylor Sing 2022–2025, then cut over from the existing `site/`.

**Architecture:** Single-page document with 7 narrative scenes. Vanilla JS + hand-rolled SVG for charts. `scrollama` for scroll-pinning. Build-time data assembly into a single `acts.json`. Theatrical bookends (red velvet, gold) on scenes I, V, VI, VII; dark-theatrical analytical surfaces on II, III, IV.

**Tech Stack:** Python 3.12 + pandas (data build), HTML / CSS / vanilla JS (frontend), `scrollama` (scroll observer), pytest (data-builder tests), `python3 -m http.server` (dev server).

**Reference materials in this repo:**
- Spec: `docs/superpowers/specs/2026-05-04-sing-redesign-design.md`
- Working chart prototypes (production-quality SVG) saved at `.superpowers/brainstorm/86706-1777904002/content/`:
  - `audit-grid.html` — Cast grid prototype
  - `audio-map-v2.html` — Audio Map prototype with medal rings + tooltip + year filter
  - `color-charts.html` — All four Scene IV charts (palette stacks, color wheel, sat-val scatter, extremes)

**Code style note:** All chart modules use `document.createElement` + `appendChild` + `textContent` for DOM construction. SVG is built with `document.createElementNS("http://www.w3.org/2000/svg", ...)`. No string-interpolated HTML. The prototypes use template strings for speed — when porting, convert to safe DOM API.

---

## File Structure

```
site_v2/
├── index.html
├── data/
│   └── acts.json                 # built by scripts/07_build_acts_json.py
├── css/
│   ├── tokens.css                # design tokens
│   ├── theatrical.css            # red velvet, curtains, gold
│   ├── editorial.css             # dark analytical surfaces
│   └── charts.css                # axes, dots, tooltips
└── js/
    ├── main.js                   # orchestrator: data load, scrollama, init charts
    ├── data.js                   # acts.json loader + helpers (hexToHsv, isMedal...)
    ├── scrollama.min.js          # vendored from existing site/
    └── charts/                   # one ES module per chart, exporting render(root, acts)
        ├── cast_grid.js          # Scene II
        ├── audio_map.js          # Scene III/1
        ├── top_artists.js        # Scene III/2
        ├── song_age.js           # Scene III/3
        ├── genre_proportions.js  # Scene III/4
        ├── palette_stacks.js     # Scene IV/1
        ├── color_wheel.js        # Scene IV/2
        ├── sat_val_scatter.js    # Scene IV/3
        ├── extremes.js           # Scene IV/4
        └── winner_vs_participant.js  # Scene V

scripts/
└── 07_build_acts_json.py         # NEW

tests/
└── test_build_acts_json.py       # NEW
```

After cutover (Task 15): `site/` → `site_legacy/`, `site_v2/` → `site/`.

---

## Task 1: Build the `acts.json` data shape

**Files:**
- Create: `scripts/07_build_acts_json.py`
- Create: `tests/test_build_acts_json.py`
- Reads: `data/sing_enriched.parquet`, `data/color_palettes.csv`
- Writes: `site_v2/data/acts.json`

This is the single JSON file the entire frontend consumes. All derived fields (dominant color, weighted-avg HSV, palette source) are computed once here so JS does no math.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_build_acts_json.py
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "07_build_acts_json.py"
OUT = ROOT / "site_v2" / "data" / "acts.json"


def test_build_produces_expected_shape():
    result = subprocess.run([sys.executable, str(SCRIPT)],
                            capture_output=True, text=True, cwd=str(ROOT))
    assert result.returncode == 0, f"build failed: {result.stderr}"
    assert OUT.exists()

    data = json.loads(OUT.read_text())
    assert isinstance(data, list)
    assert 60 < len(data) < 80, f"expected 60-80 acts, got {len(data)}"

    required = {
        "year", "group", "theme", "placement", "songs",
        "valence", "energy", "danceability", "tempo", "popularity",
        "genres", "song_count",
        "palette", "props", "dominant",
        "avg_hue", "avg_sat", "avg_val",
        "palette_source", "n_images",
    }
    for a in data:
        missing = required - set(a.keys())
        assert not missing, f"act {a.get('group')} missing fields: {missing}"

    assert all(2022 <= a["year"] <= 2025 for a in data)
    for a in data:
        assert a["dominant"] in a["palette"], \
            f"{a['year']} {a['group']}: dominant {a['dominant']} not in palette"
    assert all(a["palette_source"] in ("youtube", "bing") for a in data)


def test_dominant_picks_most_vivid_in_top6():
    import colorsys
    data = json.loads(OUT.read_text())
    for a in data:
        candidates = list(zip(a["palette"][:6], a["props"][:6]))
        scores = []
        for h, p in candidates:
            r = int(h[1:3], 16) / 255
            g = int(h[3:5], 16) / 255
            b = int(h[5:7], 16) / 255
            _, s, v = colorsys.rgb_to_hsv(r, g, b)
            scores.append((s * v * (1 + 0.3 * p), h))
        expected = max(scores)[1]
        assert a["dominant"] == expected, \
            f"{a['year']} {a['group']}: dominant {a['dominant']}, expected {expected}"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/raleightognela/Documents/sing_data
python3 -m pytest tests/test_build_acts_json.py -v
```

Expected: FAIL — script doesn't exist.

- [ ] **Step 3: Write the script**

```python
# scripts/07_build_acts_json.py
"""Build site_v2/data/acts.json from sing_enriched.parquet + color_palettes.csv.

Filters to 2022-2025, joins palettes onto acts, computes derived fields
(dominant color, weighted-avg HSV, palette source) so the frontend has
everything pre-baked.
"""
from __future__ import annotations

import colorsys
import json
import math
import re
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
PARQUET = BASE_DIR / "data" / "sing_enriched.parquet"
PALETTE_CSV = BASE_DIR / "data" / "color_palettes.csv"
OUT = BASE_DIR / "site_v2" / "data" / "acts.json"


def safe_group(g: str) -> str:
    g = g.replace("&", "and")
    g = re.sub(r"[^A-Za-z0-9 _-]", "", g)
    return re.sub(r"\s+", "_", g.strip())


def hex_to_hsv(h: str) -> tuple[float, float, float]:
    r = int(h[1:3], 16) / 255.0
    g = int(h[3:5], 16) / 255.0
    b = int(h[5:7], 16) / 255.0
    return colorsys.rgb_to_hsv(r, g, b)


def vivid_pick(hexes: list[str], props: list[float]) -> str:
    """Most-vivid color from top 6 by proportion: max(S * V * (1 + 0.3 * p))."""
    best, best_score = hexes[0], -1.0
    for h, p in zip(hexes[:6], props[:6]):
        _, s, v = hex_to_hsv(h)
        score = s * v * (1 + 0.3 * p)
        if score > best_score:
            best_score, best = score, h
    return best


def weighted_hsv(hexes: list[str], props: list[float]) -> tuple[float, float, float]:
    """Weighted-average circular hue, saturation, brightness over palette,
    skipping near-black (V < 0.15)."""
    sx = sy = ssat = sval = wt = 0.0
    for h, p in zip(hexes, props):
        hh, ss, vv = hex_to_hsv(h)
        if vv < 0.15:
            continue
        sx += math.cos(hh * 2 * math.pi) * p
        sy += math.sin(hh * 2 * math.pi) * p
        ssat += ss * p
        sval += vv * p
        wt += p
    if wt == 0:
        return 0.0, 0.0, 0.0
    avg_hue = (math.atan2(sy / wt, sx / wt) / (2 * math.pi)) % 1.0
    return avg_hue, ssat / wt, sval / wt


def main() -> None:
    df = pd.read_parquet(PARQUET)
    palettes = pd.read_csv(PALETTE_CSV)
    palette_idx = {row.group_dir: row for _, row in palettes.iterrows()}

    acts = []
    for _, r in df[(df.Year >= 2022) & (df.Year <= 2025)].sort_values(["Year", "Group"]).iterrows():
        key = f"{int(r.Year)}_{safe_group(r.Group)}"
        p = palette_idx.get(key)
        if p is None:
            continue
        hexes = p.palette_hex.split(";")
        props = [float(x) for x in p.palette_proportions.split(";")]
        avg_h, avg_s, avg_v = weighted_hsv(hexes, props)
        acts.append({
            "year": int(r.Year),
            "group": r.Group,
            "theme": r.Theme if pd.notna(r.Theme) else "",
            "placement": r.Placement if pd.notna(r.Placement) else "Participated",
            "songs": r.Songs if pd.notna(r.Songs) else "",
            "valence": float(r.valence) if pd.notna(r.valence) else None,
            "energy": float(r.energy) if pd.notna(r.energy) else None,
            "danceability": float(r.danceability) if pd.notna(r.danceability) else None,
            "tempo": float(r.tempo) if pd.notna(r.tempo) else None,
            "popularity": float(r.popularity) if pd.notna(r.popularity) else None,
            "genres": r.genres if pd.notna(r.genres) else "",
            "song_count": int(r.song_count) if pd.notna(r.song_count) else 0,
            "palette": hexes,
            "props": props,
            "dominant": vivid_pick(hexes, props),
            "avg_hue": avg_h,
            "avg_sat": avg_s,
            "avg_val": avg_v,
            "palette_source": p.image_source,
            "n_images": int(p.n_images),
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(acts, separators=(",", ":")))
    print(f"wrote {len(acts)} acts to {OUT.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run script + tests**

```bash
python3 scripts/07_build_acts_json.py
python3 -m pytest tests/test_build_acts_json.py -v
```

Expected: script prints "wrote 67 acts to site_v2/data/acts.json"; both tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/07_build_acts_json.py tests/test_build_acts_json.py site_v2/data/acts.json
git commit -m "feat: build acts.json data shape for site redesign"
```

---

## Task 2: HTML scaffold + scrollama vendor

**Files:**
- Create: `site_v2/index.html`
- Create: `site_v2/js/scrollama.min.js` (copy from `site/js/`)

Empty scene divs first; charts get filled in later tasks. This commit gets the page structure committed so subsequent chart tasks have a target.

- [ ] **Step 1: Vendor scrollama**

```bash
mkdir -p site_v2/js
cp site/js/scrollama.min.js site_v2/js/scrollama.min.js
```

- [ ] **Step 2: Create the HTML scaffold**

`site_v2/index.html` — see full file below. Save exactly as written.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>The Sound &amp; Color of Sing</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700;1,900&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="css/tokens.css">
  <link rel="stylesheet" href="css/theatrical.css">
  <link rel="stylesheet" href="css/editorial.css">
  <link rel="stylesheet" href="css/charts.css">
</head>
<body>

  <section id="scene-curtain" class="scene scene-theatrical">
    <div class="curtain curtain-left"></div>
    <div class="curtain curtain-right"></div>
    <div class="hero">
      <h1 class="logo"><i>Sing</i></h1>
      <p class="subtitle-line">Four years. Sixty-seven acts. The data behind the show.</p>
    </div>
    <div class="scroll-cue">&#x2193;</div>
  </section>

  <section id="scene-cast" class="scene scene-editorial">
    <header class="scene-header">
      <h2>The Cast</h2>
      <p class="scene-sub">Sixty-seven acts, 2022&ndash;2025.</p>
    </header>
    <div class="scene-controls">
      <button class="sort-btn active" data-sort="year">By Year</button>
      <button class="sort-btn" data-sort="placement">By Placement</button>
      <button class="sort-btn" data-sort="hue">By Hue</button>
    </div>
    <div id="cast-grid"></div>
  </section>

  <section id="scene-sound" class="scene scene-editorial">
    <header class="scene-header"><h2>The Sound</h2></header>
    <div class="chart-block">
      <div class="chart-prose"><h3>The Audio Map</h3><p>Each act lives somewhere on this map of <b>valence</b> (musical positivity) and <b>energy</b> (intensity). Both are computed by Spotify on a 0&ndash;1 scale.</p></div>
      <div class="chart-mount" id="audio-map"></div>
    </div>
    <div class="chart-block">
      <div class="chart-prose"><h3>The Sing Jukebox</h3><p>The twenty most-covered artists across four years of Sing.</p></div>
      <div class="chart-mount" id="top-artists"></div>
    </div>
    <div class="chart-block">
      <div class="chart-prose"><h3>How Old Are These Songs?</h3><p>Spotify popularity bucket for each act's average song.</p></div>
      <div class="chart-mount" id="song-age"></div>
    </div>
    <div class="chart-block">
      <div class="chart-prose"><h3>Genre DNA of a Medley</h3><p>The genre mix per year.</p></div>
      <div class="chart-mount" id="genre-proportions"></div>
    </div>
  </section>

  <section id="scene-color" class="scene scene-editorial">
    <header class="scene-header"><h2>The Color</h2></header>
    <div class="chart-block"><div class="chart-prose"><h3>The Years in Color</h3><p>Each year as a horizontal stack of every act's palette.</p></div><div class="chart-mount" id="palette-stacks"></div></div>
    <div class="chart-block"><div class="chart-prose"><h3>The Color Wheel</h3><p>Acts plotted by hue (angle) and saturation (radius).</p></div><div class="chart-mount" id="color-wheel"></div></div>
    <div class="chart-block"><div class="chart-prose"><h3>Vivid &middot; Muted &middot; Bright &middot; Dark</h3><p>The visual analog of the audio map.</p></div><div class="chart-mount" id="sat-val-scatter"></div></div>
    <div class="chart-block"><div class="chart-prose"><h3>The Extremes</h3><p>The four most distinctive acts on color.</p></div><div class="chart-mount" id="extremes"></div></div>
  </section>

  <section id="scene-verdict" class="scene scene-theatrical">
    <header class="scene-header"><h2>The Verdict</h2></header>
    <div id="pigskin-reveal"></div>
    <div id="winner-vs-participant"></div>
    <div id="first-place-spotlights"></div>
  </section>

  <section id="scene-methodology" class="scene scene-theatrical">
    <header class="scene-header"><h2>Behind the Curtain</h2></header>
    <div class="methodology-panels">
      <article class="method-panel">
        <h3>Songs</h3>
        <p>We named the songs in each act, then enriched them through the Spotify API to get audio features (valence, energy, danceability, tempo, acousticness, loudness) and genre tags. Where Spotify had multiple matches, we picked the most popular. Audio averages per act are means across the act&rsquo;s songs.</p>
      </article>
      <article class="method-panel">
        <h3>Color</h3>
        <p>We pulled YouTube videos for each act, sampled eight evenly-spaced frames per video, and ran K-means clustering (K=10) on the pooled pixels. Near-black background and very desaturated pixels were filtered out so costume and set colors would dominate. The &ldquo;dominant&rdquo; color for each act is the most vivid one &mdash; highest saturation &times; brightness &mdash; among the top six by share.</p>
      </article>
    </div>
  </section>

  <section id="scene-encore" class="scene scene-theatrical">
    <header class="scene-header"><h2>Encore</h2></header>
    <div id="big-numbers"></div>
    <div class="fin"><span><i>Fin.</i></span></div>
    <footer class="credits">
      <p>Data: Spotify &middot; baylor-sing-all-acts-final.csv &middot; The Baylor Sing Archive (YouTube)</p>
      <p>Source &amp; methodology on GitHub.</p>
    </footer>
  </section>

  <script type="module" src="js/main.js"></script>
</body>
</html>
```

- [ ] **Step 3: Verify page loads (200, will be unstyled)**

```bash
python3 -m http.server 8000 --directory site_v2 &
SERVER_PID=$!
sleep 1
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/
kill $SERVER_PID 2>/dev/null
```

Expected: `200`.

- [ ] **Step 4: Commit**

```bash
git add site_v2/index.html site_v2/js/scrollama.min.js
git commit -m "feat: scaffold site_v2 HTML with seven scene structure"
```

---

## Task 3: CSS — tokens, theatrical, editorial, charts

**Files:**
- Create: `site_v2/css/tokens.css`
- Create: `site_v2/css/theatrical.css`
- Create: `site_v2/css/editorial.css`
- Create: `site_v2/css/charts.css`

- [ ] **Step 1: Create tokens.css**

```css
/* site_v2/css/tokens.css */
:root {
  --velvet: #6b1117;
  --velvet-deep: #2a0608;
  --gold: #d4af37;
  --gold-bright: #f5d97a;
  --gold-dim: #8a6d3a;
  --bronze: #8a6d3a;
  --ink: #0a0506;
  --ink-2: #14080a;
  --ink-3: #1a0e10;
  --paper: #f7f4ec;
  --text-primary: #f0e6c0;
  --text-secondary: #a89260;
  --text-tertiary: #5a4a3a;
  --border-quiet: #2a1a1c;
  --border-active: #d4af37;

  --font-display: "Playfair Display", Georgia, serif;
  --font-body: "Inter", system-ui, sans-serif;

  --pad-scene: 80px 32px;
  --gap-stack: 18px;
  --ease: cubic-bezier(.4,0,.2,1);
}

* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: var(--ink); color: var(--text-primary); font-family: var(--font-body); }
html { scroll-behavior: smooth; }
.scene { min-height: 100vh; padding: var(--pad-scene); position: relative; }
.scene-header { max-width: 720px; margin: 0 auto 32px; }
.scene-header h2 { font-family: var(--font-display); font-style: italic; font-size: 56px; color: var(--gold); margin: 0 0 8px; line-height: 1; }
.scene-header .scene-sub { color: var(--text-secondary); font-size: 14px; letter-spacing: 1px; text-transform: uppercase; margin: 0; }
a { color: var(--gold); }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
  html { scroll-behavior: auto; }
}
```

- [ ] **Step 2: Create theatrical.css**

```css
/* site_v2/css/theatrical.css */
.scene-theatrical {
  background: radial-gradient(ellipse at top, var(--velvet) 0%, var(--velvet-deep) 60%, var(--ink) 100%);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
}
.scene-theatrical .scene-header { text-align: center; }
.scene-theatrical .scene-header h2 { color: var(--gold-bright); text-shadow: 0 2px 8px rgba(0,0,0,.5); }

/* Curtain (Scene I) */
.curtain {
  position: absolute; top: 0; bottom: 0; width: 25%;
  background: repeating-linear-gradient(90deg, var(--velvet) 0px, #4a0b0f 10px, var(--velvet) 22px);
  box-shadow: inset 0 0 60px rgba(0,0,0,.4);
  transition: transform 1.2s var(--ease);
}
.curtain-left { left: 0; border-right: 2px solid var(--gold); }
.curtain-right { right: 0; border-left: 2px solid var(--gold); transform: scaleX(-1); }
.curtains-open .curtain-left { transform: translateX(-100%); }
.curtains-open .curtain-right { transform: translateX(100%) scaleX(-1); }

.hero { position: relative; z-index: 2; text-align: center; }
.hero .logo {
  font-family: var(--font-display); font-style: italic; font-weight: 900;
  font-size: 144px; line-height: 1; margin: 0;
  color: transparent;
  background: linear-gradient(180deg, var(--gold-bright), var(--gold) 50%, var(--gold-dim));
  -webkit-background-clip: text; background-clip: text;
  text-shadow: 0 4px 12px rgba(0,0,0,.6);
  opacity: 0; transition: opacity 1.4s var(--ease) 0.6s;
}
.curtains-open .hero .logo { opacity: 1; }
.hero .subtitle-line {
  font-family: var(--font-display); font-style: italic;
  color: var(--text-primary); font-size: 18px; margin-top: 16px;
  opacity: 0; transition: opacity 0.8s var(--ease) 1.4s;
}
.curtains-open .hero .subtitle-line { opacity: 1; }

.scroll-cue {
  position: absolute; bottom: 24px; left: 50%; transform: translateX(-50%);
  color: var(--gold); font-size: 24px; opacity: 0;
  animation: scroll-cue-blink 2s ease-in-out infinite;
  animation-delay: 2.6s;
}
@keyframes scroll-cue-blink { 0%, 100% { opacity: .3; transform: translateX(-50%) translateY(0); } 50% { opacity: 1; transform: translateX(-50%) translateY(8px); } }

/* Methodology */
.methodology-panels { display: grid; grid-template-columns: 1fr 1fr; gap: 32px; max-width: 960px; margin: 0 auto; }
.method-panel { background: var(--ink-2); border: 1px solid var(--border-quiet); border-radius: 6px; padding: 24px 28px; }
.method-panel h3 { font-family: var(--font-display); font-style: italic; color: var(--gold); margin: 0 0 12px; font-size: 22px; }
.method-panel p { color: var(--text-primary); font-size: 14px; line-height: 1.7; margin: 0; }

/* Encore */
.fin { text-align: center; margin: 80px 0 32px; }
.fin span { font-family: var(--font-display); font-style: italic; font-weight: 900; font-size: 96px; line-height: 1; color: transparent; background: linear-gradient(180deg, var(--gold-bright), var(--gold-dim)); -webkit-background-clip: text; background-clip: text; }
.credits { text-align: center; color: var(--text-tertiary); font-size: 12px; line-height: 1.8; }
.credits a { color: var(--text-secondary); }

@media (max-width: 720px) {
  .hero .logo { font-size: 88px; }
  .methodology-panels { grid-template-columns: 1fr; }
  .fin span { font-size: 64px; }
}
```

- [ ] **Step 3: Create editorial.css**

```css
/* site_v2/css/editorial.css */
.scene-editorial { background: var(--ink); padding: var(--pad-scene); }

.scene-controls { max-width: 1100px; margin: 0 auto 16px; display: flex; gap: 8px; }
.sort-btn { background: var(--ink-2); border: 1px solid var(--border-quiet); color: var(--text-secondary); padding: 6px 14px; border-radius: 3px; font-family: var(--font-body); font-size: 12px; cursor: pointer; transition: all .15s var(--ease); }
.sort-btn:hover { color: var(--gold); border-color: var(--gold-dim); }
.sort-btn.active { background: var(--ink-3); color: var(--gold-bright); border-color: var(--gold); }

.chart-block {
  display: grid; grid-template-columns: 1fr 2fr; gap: 32px;
  max-width: 1200px; margin: 0 auto 48px; align-items: start;
  padding: 24px;
  background: var(--ink-2); border: 1px solid var(--border-quiet);
  border-radius: 6px; position: relative;
}
.chart-block::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: linear-gradient(180deg, var(--gold), var(--gold-dim)); }
.chart-prose h3 { font-family: var(--font-display); font-style: italic; color: var(--gold-bright); font-size: 24px; margin: 0 0 12px; }
.chart-prose p { color: var(--text-primary); font-size: 14px; line-height: 1.6; margin: 0; }
.chart-mount { background: var(--ink); border-radius: 4px; padding: 16px; min-height: 200px; }

/* Cast grid (Scene II) */
.yr-row { max-width: 1200px; margin: 0 auto 28px; }
.yr-label { font-family: var(--font-display); font-style: italic; font-size: 26px; color: var(--gold); margin: 0 0 10px 4px; }
.yr-label .yr-count { font-size: 14px; color: var(--text-tertiary); font-style: normal; }
.yr-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 8px; }
.cast-tile { background: var(--ink-2); border: 1px solid var(--border-quiet); border-radius: 4px; overflow: hidden; cursor: pointer; transition: all .15s var(--ease); }
.cast-tile:hover { transform: translateY(-2px); border-color: var(--gold-dim); }
.cast-tile-bing { opacity: .7; }
.cast-tile-strip { display: flex; height: 18px; }
.cast-tile-body { display: flex; gap: 10px; padding: 8px 10px; align-items: center; }
.cast-dom { width: 36px; height: 36px; border-radius: 3px; flex-shrink: 0; }
.cast-text { flex: 1; min-width: 0; }
.cast-group { font-size: 12px; font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cast-meta { font-size: 10px; color: var(--text-secondary); margin-top: 2px; }
.cast-meta .placement-medal { color: var(--gold); font-weight: 600; }
.cast-meta .placement-pigskin { color: var(--gold-dim); }
.badge-no-video { display: inline-block; padding: 1px 6px; margin-left: 4px; background: var(--ink-3); border: 1px solid var(--border-quiet); color: var(--text-tertiary); font-size: 9px; letter-spacing: 1px; text-transform: uppercase; border-radius: 2px; }

@media (max-width: 900px) { .chart-block { grid-template-columns: 1fr; } }
```

- [ ] **Step 4: Create charts.css**

```css
/* site_v2/css/charts.css */
.chart-axis { stroke: var(--text-tertiary); stroke-width: 1; }
.chart-tick { stroke: var(--border-quiet); }
.chart-axis-label { fill: var(--text-secondary); font-family: var(--font-display); font-style: italic; font-size: 14px; }
.chart-axis-num { fill: var(--text-tertiary); font-family: var(--font-body); font-size: 10px; }
.chart-quad-label { fill: var(--gold); opacity: .5; font-family: var(--font-display); font-style: italic; font-size: 11px; letter-spacing: 1px; text-transform: uppercase; }

.chart-dot { transition: r .15s var(--ease), stroke-width .15s var(--ease); cursor: pointer; }
.chart-dot:hover { stroke: var(--gold-bright) !important; stroke-width: 3 !important; }

.chart-ring-gold { fill: none; stroke: var(--gold); stroke-width: 1.6; }
.chart-ring-bronze { fill: none; stroke: var(--bronze); stroke-width: 1.2; opacity: .7; }
.chart-label-medal { fill: var(--gold-bright); font-family: var(--font-display); font-style: italic; font-size: 11px; pointer-events: none; }

.chart-tooltip { position: fixed; pointer-events: none; background: var(--ink-2); border: 1px solid var(--gold); padding: 8px 12px; border-radius: 4px; font-family: var(--font-body); font-size: 12px; color: var(--text-primary); opacity: 0; transition: opacity .15s var(--ease); z-index: 100; min-width: 200px; box-shadow: 0 4px 16px rgba(0,0,0,.6); }
.chart-tooltip h4 { margin: 0 0 4px; font-family: var(--font-display); font-style: italic; color: var(--gold); font-size: 14px; }
.chart-tooltip .meta { color: var(--text-secondary); font-size: 11px; margin-bottom: 6px; }
.chart-tooltip .swatches { display: flex; gap: 2px; margin-top: 6px; }
.chart-tooltip .swatches div { width: 22px; height: 18px; border-radius: 2px; }

.chart-year-toggle { display: inline-block; margin-left: 8px; padding: 2px 8px; background: var(--ink-2); border: 1px solid var(--border-quiet); border-radius: 3px; cursor: pointer; color: var(--text-secondary); font-family: var(--font-body); font-size: 11px; }
.chart-year-toggle.active { background: var(--ink-3); border-color: var(--gold); color: var(--gold-bright); }

.chart-explainer { font-family: var(--font-body); font-size: 11px; color: var(--text-secondary); margin-top: 12px; padding: 10px 14px; background: var(--ink-3); border-left: 2px solid var(--gold-dim); border-radius: 2px; line-height: 1.5; }
.chart-explainer b { color: var(--gold); }

.chart-footnote { font-family: var(--font-body); font-size: 10px; color: var(--text-secondary); margin: 12px 0 0; padding-top: 10px; border-top: 1px dashed var(--border-quiet); font-style: italic; }

@keyframes highlight-pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.6); } }
.highlight-pulse { animation: highlight-pulse 1s var(--ease) 2; transform-origin: center; transform-box: fill-box; }

/* Audio map specifics */
.audio-map-controls { font-family: var(--font-body); font-size: 11px; color: var(--text-secondary); margin-bottom: 12px; }
.audio-map-legend { display: flex; gap: 18px; margin-top: 14px; font-family: var(--font-body); font-size: 11px; color: var(--text-secondary); flex-wrap: wrap; }
.audio-map-legend > span { display: flex; align-items: center; gap: 6px; }
.legend-medal, .legend-pigskin, .legend-grey { display: inline-block; width: 14px; height: 14px; border-radius: 50%; background: #555; position: relative; }
.legend-medal::after { content: ''; position: absolute; inset: -3px; border: 1.5px solid var(--gold); border-radius: 50%; }
.legend-pigskin::after { content: ''; position: absolute; inset: -2px; border: 1.2px solid var(--bronze); border-radius: 50%; }

/* Bar charts */
.ta-label { fill: var(--text-primary); font-family: var(--font-body); font-size: 12px; }
.ta-value { fill: var(--gold-bright); font-family: var(--font-body); font-size: 11px; }

/* Genre legend */
.genre-legend { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 12px; font-family: var(--font-body); font-size: 11px; color: var(--text-secondary); }
.genre-legend i { display: inline-block; width: 10px; height: 10px; margin-right: 4px; border-radius: 1px; }

/* Color charts */
.ps-row { display: flex; align-items: center; gap: 12px; margin-bottom: 6px; }
.ps-yr { font-family: var(--font-display); font-style: italic; color: var(--gold); font-size: 16px; width: 50px; }
.ps-strip { display: flex; flex: 1; height: 48px; gap: 1px; }
.ps-act { flex: 1; display: flex; flex-direction: column; min-width: 0; transition: transform .15s var(--ease); }
.ps-act > div { flex: 1; }
.ps-act:hover { transform: scaleY(1.15); }
.ps-medal { box-shadow: 0 0 0 1px var(--gold); }

.cw-wrap { display: flex; justify-content: center; padding: 8px; position: relative; }
.cw-wrap svg { background: radial-gradient(circle, var(--ink-3), var(--ink)); border-radius: 50%; max-width: 520px; }
.cw-label { fill: var(--text-secondary); font-family: var(--font-body); font-size: 11px; }

.extremes-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.extreme-card { background: var(--ink); border: 1px solid var(--border-quiet); border-radius: 4px; padding: 12px; }
.extreme-label { font-family: var(--font-body); color: var(--gold); font-size: 10px; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 6px; }
.extreme-swatch { height: 48px; border-radius: 3px; margin-bottom: 6px; }
.extreme-name { font-size: 11px; color: var(--text-primary); line-height: 1.3; }
.extreme-meta { font-size: 10px; color: var(--text-secondary); margin-top: 2px; }
@media (max-width: 720px) { .extremes-grid { grid-template-columns: repeat(2, 1fr); } }

/* Verdict */
.verdict-headline { text-align: center; font-family: var(--font-display); font-style: italic; color: var(--gold-bright); font-size: 24px; line-height: 1.4; margin: 24px 0 32px; }
.verdict-headline div { display: block; }
.verdict-headline i { color: var(--gold); }
.verdict-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 10px; max-width: 1200px; margin: 0 auto; }
.verdict-tile { background: var(--ink-2); border: 1px solid var(--border-quiet); border-radius: 4px; overflow: hidden; }
.vt-medal { box-shadow: 0 0 0 1px var(--gold); }
.vt-gold { box-shadow: 0 0 0 2px var(--gold); }
.vt-strip { display: flex; height: 18px; }
.vt-body { padding: 8px 12px; }
.vt-placement { font-family: var(--font-body); color: var(--gold); font-size: 11px; letter-spacing: 1px; }
.vt-name { font-size: 13px; color: var(--text-primary); margin-top: 2px; font-weight: 600; }
.vt-meta { font-size: 11px; color: var(--text-secondary); margin-top: 2px; }

.spotlight-h { font-family: var(--font-display); font-style: italic; color: var(--gold); text-align: center; margin: 48px 0 16px; }
.spotlight-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; max-width: 1100px; margin: 0 auto; }
.spotlight-card { background: var(--ink-2); border: 1px solid var(--gold); border-radius: 6px; padding: 20px 18px; text-align: center; }
.spotlight-yr { font-family: var(--font-display); font-style: italic; color: var(--gold-bright); font-size: 28px; line-height: 1; }
.spotlight-name { font-size: 14px; color: var(--text-primary); margin-top: 8px; font-weight: 600; }
.spotlight-theme { font-family: var(--font-display); color: var(--text-secondary); font-size: 12px; margin-top: 6px; }
.spotlight-strip { display: flex; height: 12px; margin-top: 16px; gap: 1px; }

.vp-h { font-family: var(--font-display); font-style: italic; color: var(--gold); text-align: center; margin: 48px 0 16px; }
.vp-label { fill: var(--text-secondary); font-family: var(--font-body); font-size: 11px; }
.vp-legend { display: flex; gap: 18px; justify-content: center; margin-top: 12px; font-family: var(--font-body); font-size: 11px; color: var(--text-secondary); }
.vp-legend i { display: inline-block; width: 12px; height: 12px; border-radius: 2px; margin-right: 4px; }

@media (max-width: 720px) { .spotlight-grid { grid-template-columns: 1fr 1fr; } }

/* Encore big numbers */
#big-numbers { max-width: 720px; margin: 32px auto; }
.bignum { text-align: center; margin-bottom: 48px; }
.bn-num { font-family: var(--font-display); font-style: italic; font-weight: 900; font-size: 88px; line-height: 1; color: transparent; background: linear-gradient(180deg, var(--gold-bright), var(--gold), var(--gold-dim)); -webkit-background-clip: text; background-clip: text; }
.bn-cap { font-family: var(--font-display); font-style: italic; color: var(--text-primary); font-size: 18px; margin-top: 8px; line-height: 1.4; }
.bn-cap i { color: var(--gold); }
```

- [ ] **Step 5: Verify in browser (will look styled but empty)**

```bash
python3 -m http.server 8000 --directory site_v2 &
SERVER_PID=$!
sleep 1
echo "Open http://localhost:8000/. Page should be dark with red velvet sections at scenes I, V, VI, VII. Curtain panels visible but stationary (animation triggers via JS in Task 4)."
kill $SERVER_PID 2>/dev/null
```

- [ ] **Step 6: Commit**

```bash
git add site_v2/css/
git commit -m "feat: site_v2 CSS — tokens, theatrical, editorial, charts"
```

---

## Task 4: Shared JS — data.js + main.js skeleton

**Files:**
- Create: `site_v2/js/data.js`
- Create: `site_v2/js/main.js`

`data.js` exports the loaded acts and shared helpers. `main.js` loads data, fires the curtain animation, and (in later tasks) calls each chart's `render`.

- [ ] **Step 1: Create data.js**

```javascript
// site_v2/js/data.js

let _acts = null;

export async function loadActs() {
  if (_acts) return _acts;
  const r = await fetch("data/acts.json");
  _acts = await r.json();
  return _acts;
}

export function hexToHsv(h) {
  const r = parseInt(h.slice(1, 3), 16) / 255;
  const g = parseInt(h.slice(3, 5), 16) / 255;
  const b = parseInt(h.slice(5, 7), 16) / 255;
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b);
  const d = mx - mn;
  let H = 0;
  if (d > 0) {
    if (mx === r) H = ((g - b) / d) % 6;
    else if (mx === g) H = (b - r) / d + 2;
    else H = (r - g) / d + 4;
    H /= 6;
    if (H < 0) H += 1;
  }
  const S = mx === 0 ? 0 : d / mx;
  return { h: H, s: S, v: mx };
}

export function isMedal(p) { return p === "1st" || p === "2nd" || p === "3rd"; }
export function isPigskin(p) { return p && (isMedal(p) || (typeof p === "string" && p.includes("Pigskin"))); }
export function isYTSource(act) { return act.palette_source === "youtube"; }

export const PLACEMENT_ORDER = { "1st": 1, "2nd": 2, "3rd": 3, "Pigskin": 4, "Participated": 5 };
```

- [ ] **Step 2: Create main.js**

```javascript
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
```

- [ ] **Step 3: Verify curtain animation + console log**

```bash
python3 -m http.server 8000 --directory site_v2 &
sleep 1
echo "Open http://localhost:8000/. Curtains animate aside, gold 'Sing' fades in, console logs 'loaded 67 acts'."
pkill -f "http.server 8000" 2>/dev/null
```

- [ ] **Step 4: Commit**

```bash
git add site_v2/js/data.js site_v2/js/main.js
git commit -m "feat: site_v2 JS — data loader, helpers, curtain animation"
```

---

## Task 5: Cast grid (Scene II)

**Files:**
- Create: `site_v2/js/charts/cast_grid.js`
- Modify: `site_v2/js/main.js`

Port the audit-grid prototype at `.superpowers/brainstorm/86706-1777904002/content/audit-grid.html`. Use safe DOM construction (createElement / appendChild / textContent), not template strings. Render: year-grouped tile rows with palette strips + dominant + group/theme/placement; bing-fallback acts get a 5-stop grey palette + "no video" badge.

- [ ] **Step 1: Create cast_grid.js**

```javascript
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
```

- [ ] **Step 2: Wire into main.js**

Update `site_v2/js/main.js`:

```javascript
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
```

- [ ] **Step 3: Verify in browser**

```bash
python3 -m http.server 8000 --directory site_v2 & sleep 1
echo "Open http://localhost:8000/, scroll to The Cast. 67 tiles in 4 year bands; 16 bing-fallback acts visibly dimmer with grey strips and 'no video' badge. Sort buttons re-order."
pkill -f "http.server 8000" 2>/dev/null
```

In browser console: `document.querySelectorAll('.cast-tile').length === 67`.

- [ ] **Step 4: Commit**

```bash
git add site_v2/js/charts/cast_grid.js site_v2/js/main.js
git commit -m "feat: Scene II cast grid with sort + bing-fallback handling"
```

---

## Task 6: Audio Map (Scene III/1)

**Files:**
- Create: `site_v2/js/charts/audio_map.js`
- Modify: `site_v2/js/main.js`

Port `audio-map-v2.html` prototype. Use safe DOM (createElementNS for SVG, appendChild). Bing-source acts get grey dot fill. Includes the valence/energy explainer in the chart-explainer block.

- [ ] **Step 1: Create audio_map.js**

```javascript
// site_v2/js/charts/audio_map.js
import { isMedal, isYTSource } from "../data.js";

const NS = "http://www.w3.org/2000/svg";
function svg(tag, attrs) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; }
function svgText(parent, x, y, content, cls, anchor) {
  const t = svg("text", { x, y, class: cls, ...(anchor ? { "text-anchor": anchor } : {}) });
  t.textContent = content;
  parent.appendChild(t);
  return t;
}
function svgLine(parent, x1, y1, x2, y2, cls) {
  const l = svg("line", { x1, y1, x2, y2, class: cls });
  parent.appendChild(l);
  return l;
}

export function render(root, acts) {
  const plottable = acts.filter(a => a.valence != null && a.energy != null);
  const missing = acts.filter(a => a.valence == null || a.energy == null);
  let activeYear = "all";

  // Build static structure with createElement (no template strings)
  while (root.firstChild) root.removeChild(root.firstChild);

  const controls = document.createElement("div");
  controls.className = "audio-map-controls";
  const labelText = document.createTextNode("Year filter: ");
  controls.appendChild(labelText);
  ["all", "2022", "2023", "2024", "2025"].forEach((yr, i) => {
    const span = document.createElement("span");
    span.className = "chart-year-toggle" + (i === 0 ? " active" : "");
    span.dataset.yr = yr;
    span.textContent = yr === "all" ? "All" : yr;
    span.addEventListener("click", () => {
      controls.querySelectorAll(".chart-year-toggle").forEach(x => x.classList.remove("active"));
      span.classList.add("active");
      activeYear = yr;
      draw();
    });
    controls.appendChild(span);
  });
  root.appendChild(controls);

  const svgEl = svg("svg", { width: "100%", viewBox: "0 0 800 560", style: "display:block;" });
  root.appendChild(svgEl);

  const tooltip = document.createElement("div");
  tooltip.className = "chart-tooltip";
  root.appendChild(tooltip);

  const legend = document.createElement("div");
  legend.className = "audio-map-legend";
  [
    ["legend-medal", "1st / 2nd / 3rd"],
    ["legend-pigskin", "Pigskin top-8"],
    ["legend-grey", "No real palette"],
  ].forEach(([cls, txt]) => {
    const span = document.createElement("span");
    const sw = document.createElement("span");
    sw.className = cls;
    span.appendChild(sw);
    span.appendChild(document.createTextNode(" " + txt));
    legend.appendChild(span);
  });
  root.appendChild(legend);

  const missingNote = document.createElement("p");
  missingNote.className = "chart-footnote";
  root.appendChild(missingNote);

  const explainer = document.createElement("div");
  explainer.className = "chart-explainer";
  explainer.append("Valence", document.createTextNode(" measures musical positivity (sad → happy on a 0–1 scale). "));
  const e2 = document.createElement("b"); e2.textContent = "Energy"; explainer.appendChild(e2);
  explainer.append(document.createTextNode(" measures intensity. Both are computed by Spotify per song and averaged over an act's tracks."));
  // (Replace simple "Valence" text with a <b>)
  explainer.firstChild.remove();
  const e1 = document.createElement("b"); e1.textContent = "Valence";
  explainer.insertBefore(e1, explainer.firstChild);
  root.appendChild(explainer);

  // Chart axes
  const W = 680, H = 500;
  const g = svg("g", { transform: "translate(60,30)" });
  svgEl.appendChild(g);

  svgText(g, 20, 20, "High Energy / Sad", "chart-quad-label");
  svgText(g, 540, 20, "High Energy / Happy", "chart-quad-label", "end");
  svgText(g, 20, 490, "Low Energy / Sad", "chart-quad-label");
  svgText(g, 540, 490, "Low Energy / Happy", "chart-quad-label", "end");
  [125, 250, 375].forEach(y => svgLine(g, 0, y, 680, y, "chart-tick"));
  [170, 340, 510].forEach(x => svgLine(g, x, 0, x, 500, "chart-tick"));
  svgLine(g, 0, 500, 680, 500, "chart-axis");
  svgLine(g, 0, 0, 0, 500, "chart-axis");

  ["0", ".25", ".5", ".75", "1"].forEach((t, i) => {
    svgText(g, -8, 504 - i * 125, t, "chart-axis-num", "end");
    svgText(g, i * 170, 518, t, "chart-axis-num", "middle");
  });
  svgText(g, 340, 545, "Valence (musical positivity →)", "chart-axis-label", "middle");
  const yLab = svg("text", { x: -25, y: 250, class: "chart-axis-label", "text-anchor": "middle", transform: "rotate(-90, -25, 250)" });
  yLab.textContent = "Energy";
  g.appendChild(yLab);

  const dotsLayer = svg("g", {});
  g.appendChild(dotsLayer);

  function rank(p) { return isMedal(p) ? 3 : (p && p.includes && p.includes("Pigskin")) ? 2 : 1; }

  function draw() {
    while (dotsLayer.firstChild) dotsLayer.removeChild(dotsLayer.firstChild);
    const visible = plottable
      .filter(d => activeYear === "all" || d.year === parseInt(activeYear))
      .sort((a, b) => rank(a.placement) - rank(b.placement));

    visible.forEach(d => {
      const cx = d.valence * W;
      const cy = (1 - d.energy) * H;
      const medal = isMedal(d.placement);
      const pigskin = !medal && d.placement && d.placement.includes("Pigskin");
      const r = medal ? 10 : pigskin ? 8 : 6;
      const grp = svg("g", {});
      const fill = isYTSource(d) ? d.dominant : "#555";
      const c = svg("circle", { cx, cy, r, fill, stroke: "#000", "stroke-width": 1, class: "chart-dot" });
      grp.appendChild(c);

      if (medal) {
        const r1 = svg("circle", { cx, cy, r: r + 4, class: "chart-ring-gold", style: "opacity:.95" });
        const r2 = svg("circle", { cx, cy, r: r + 7, class: "chart-ring-gold", style: "opacity:.55" });
        grp.appendChild(r1); grp.appendChild(r2);
        const lbl = svg("text", { x: cx + 14, y: cy + 4, class: "chart-label-medal" });
        lbl.textContent = d.placement;
        grp.appendChild(lbl);
      } else if (pigskin) {
        grp.appendChild(svg("circle", { cx, cy, r: r + 3, class: "chart-ring-bronze" }));
      }

      grp.addEventListener("mousemove", ev => showTip(ev, d));
      grp.addEventListener("mouseleave", hideTip);
      dotsLayer.appendChild(grp);
    });

    const miss = missing.filter(m => activeYear === "all" || m.year === parseInt(activeYear));
    if (miss.length) {
      missingNote.textContent = "Not on map (no audio data): " + miss.map(m => m.year + " " + m.group).join(" · ");
    } else {
      missingNote.textContent = "";
    }
  }

  function showTip(ev, d) {
    while (tooltip.firstChild) tooltip.removeChild(tooltip.firstChild);
    tooltip.style.opacity = "1";
    tooltip.style.left = (ev.clientX + 14) + "px";
    tooltip.style.top = (ev.clientY + 14) + "px";
    const h = document.createElement("h4");
    h.textContent = d.group + (d.theme ? " — " + d.theme : "");
    tooltip.appendChild(h);
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = `${d.year} · ${d.placement} · valence ${d.valence.toFixed(2)} · energy ${d.energy.toFixed(2)}`;
    tooltip.appendChild(meta);
    const sw = document.createElement("div");
    sw.className = "swatches";
    if (isYTSource(d)) {
      d.palette.slice(0, 6).forEach(hh => {
        const cc = document.createElement("div");
        cc.style.background = hh;
        sw.appendChild(cc);
      });
    } else {
      const i = document.createElement("i");
      i.style.color = "var(--text-tertiary)";
      i.style.fontSize = "10px";
      i.textContent = "no real palette";
      sw.appendChild(i);
    }
    tooltip.appendChild(sw);
  }
  function hideTip() { tooltip.style.opacity = "0"; }

  draw();

  return {
    highlight(matchFn) {
      // Pulse matching dot
      const dots = dotsLayer.querySelectorAll("g");
      dots.forEach((grp) => {
        const idx = Array.from(dotsLayer.children).indexOf(grp);
        // can't index plottable safely after sort; instead match via stored data
      });
      // Re-walk: rebuild with highlight
      const matched = plottable.filter(matchFn);
      matched.forEach(d => {
        // Find the circle at that x,y by scanning current dots
        const cx = d.valence * W;
        const cy = (1 - d.energy) * H;
        dotsLayer.querySelectorAll("circle.chart-dot").forEach(c => {
          if (Math.abs(parseFloat(c.getAttribute("cx")) - cx) < 0.1 &&
              Math.abs(parseFloat(c.getAttribute("cy")) - cy) < 0.1) {
            c.classList.add("highlight-pulse");
            setTimeout(() => c.classList.remove("highlight-pulse"), 2000);
          }
        });
      });
    },
  };
}
```

- [ ] **Step 2: Wire into main.js**

Add to imports + init:

```javascript
import { render as renderAudioMap } from "./charts/audio_map.js";
// in init() after castGrid:
charts.audioMap = renderAudioMap(document.getElementById("audio-map"), acts);
```

- [ ] **Step 3: Browser verify**

```bash
python3 -m http.server 8000 --directory site_v2 & sleep 1
echo "Open localhost:8000/, scroll to The Sound. Audio map shows 65 dots; 2 listed as missing in footnote; year toggles filter; tooltip on hover; medal acts have gold rings + labels; explainer block visible."
pkill -f "http.server 8000" 2>/dev/null
```

- [ ] **Step 4: Commit**

```bash
git add site_v2/js/charts/audio_map.js site_v2/js/main.js
git commit -m "feat: Scene III audio map with valence/energy explainer"
```

---

## Task 7: Top Artists, Song Age, Genre Proportions (Scene III/2-4)

**Files:**
- Create: `site_v2/js/charts/top_artists.js`
- Create: `site_v2/js/charts/song_age.js`
- Create: `site_v2/js/charts/genre_proportions.js`
- Modify: `site_v2/js/main.js`

Three new charts, all simple SVG with safe DOM. Note: true song-age requires per-song release_year which isn't in the parquet; v1 uses the act's avg Spotify popularity score as a proxy histogram.

- [ ] **Step 1: top_artists.js**

```javascript
// site_v2/js/charts/top_artists.js
const NS = "http://www.w3.org/2000/svg";
function svg(tag, attrs) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; }

export function render(root, acts) {
  const counts = new Map();
  acts.forEach(a => {
    if (!a.songs) return;
    a.songs.split(";").forEach(s => {
      const m = s.match(/\(([^)]+)\)\s*$/);
      if (m) {
        const artist = m[1].trim();
        counts.set(artist, (counts.get(artist) || 0) + 1);
      }
    });
  });
  const top = [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 20);
  if (top.length === 0) return;
  const max = top[0][1];
  const W = 700, BAR_H = 22, GAP = 4, LABEL_W = 200, PAD = 16;
  const H = top.length * (BAR_H + GAP) + PAD * 2;

  while (root.firstChild) root.removeChild(root.firstChild);
  const svgEl = svg("svg", { width: "100%", viewBox: `0 0 ${W} ${H}`, style: "display:block;" });
  root.appendChild(svgEl);

  top.forEach(([artist, n], i) => {
    const y = PAD + i * (BAR_H + GAP);
    const barW = (n / max) * (W - LABEL_W - PAD - 60);
    svgEl.appendChild(svg("rect", { x: LABEL_W, y, width: barW, height: BAR_H, fill: "var(--gold)", rx: 2 }));
    const lbl = svg("text", { x: LABEL_W - 8, y: y + BAR_H * 0.7, class: "ta-label", "text-anchor": "end" });
    lbl.textContent = artist;
    svgEl.appendChild(lbl);
    const val = svg("text", { x: LABEL_W + barW + 6, y: y + BAR_H * 0.7, class: "ta-value", "text-anchor": "start" });
    val.textContent = String(n);
    svgEl.appendChild(val);
  });
}
```

- [ ] **Step 2: song_age.js**

```javascript
// site_v2/js/charts/song_age.js
const NS = "http://www.w3.org/2000/svg";
function svg(tag, attrs) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; }

export function render(root, acts) {
  const data = acts.filter(a => a.popularity != null);
  const W = 700, H = 280, PAD_L = 50, PAD_R = 20, PAD_T = 20, PAD_B = 40;
  const innerW = W - PAD_L - PAD_R, innerH = H - PAD_T - PAD_B;

  const buckets = Array.from({ length: 10 }, () => 0);
  data.forEach(a => {
    const b = Math.min(9, Math.floor(a.popularity / 10));
    buckets[b]++;
  });
  const max = Math.max(...buckets, 1);

  while (root.firstChild) root.removeChild(root.firstChild);
  const svgEl = svg("svg", { width: "100%", viewBox: `0 0 ${W} ${H}`, style: "display:block;" });
  root.appendChild(svgEl);

  buckets.forEach((count, i) => {
    const x = PAD_L + i * (innerW / 10);
    const w = innerW / 10 - 4;
    const h = (count / max) * innerH;
    const y = PAD_T + innerH - h;
    svgEl.appendChild(svg("rect", { x, y, width: w, height: h, fill: "var(--gold-dim)", rx: 1 }));
    const cnt = svg("text", { x: x + w / 2, y: y - 4, class: "ta-value", "text-anchor": "middle" });
    cnt.textContent = String(count);
    svgEl.appendChild(cnt);
    const lab = svg("text", { x: x + w / 2, y: PAD_T + innerH + 14, class: "ta-label", "text-anchor": "middle" });
    lab.textContent = `${i * 10}-${i * 10 + 9}`;
    svgEl.appendChild(lab);
  });
  const ax = svg("text", { x: W / 2, y: H - 8, class: "chart-axis-label", "text-anchor": "middle" });
  ax.textContent = "Avg song popularity (0–100, Spotify)";
  svgEl.appendChild(ax);

  const exp = document.createElement("p");
  exp.className = "chart-explainer";
  const b = document.createElement("b"); b.textContent = "Spotify popularity";
  exp.appendChild(b);
  exp.appendChild(document.createTextNode(" is a 0–100 score per song; this chart shows each act's average across their songs."));
  root.appendChild(exp);
}
```

- [ ] **Step 3: genre_proportions.js**

```javascript
// site_v2/js/charts/genre_proportions.js
const NS = "http://www.w3.org/2000/svg";
function svg(tag, attrs) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; }

const TOP_N = 8;
const COLORS = ["#d4af37", "#7a102a", "#1d8143", "#641d56", "#444f69", "#874563", "#cc8d6d", "#e6bea7"];

export function render(root, acts) {
  const yearCounts = { 2022: {}, 2023: {}, 2024: {}, 2025: {} };
  const totalCounts = {};
  acts.forEach(a => {
    if (!a.genres) return;
    a.genres.split(";").forEach(g => {
      g = g.trim(); if (!g) return;
      yearCounts[a.year][g] = (yearCounts[a.year][g] || 0) + 1;
      totalCounts[g] = (totalCounts[g] || 0) + 1;
    });
  });
  const topGenres = Object.entries(totalCounts).sort((a, b) => b[1] - a[1]).slice(0, TOP_N).map(([g]) => g);
  const colorOf = g => COLORS[topGenres.indexOf(g) % COLORS.length];

  const W = 700, H = 280, PAD_L = 50, PAD_R = 80, PAD_T = 20, PAD_B = 40;
  const innerW = W - PAD_L - PAD_R, innerH = H - PAD_T - PAD_B;
  const years = [2022, 2023, 2024, 2025];

  while (root.firstChild) root.removeChild(root.firstChild);
  const svgEl = svg("svg", { width: "100%", viewBox: `0 0 ${W} ${H}`, style: "display:block;" });
  root.appendChild(svgEl);

  const bw = innerW / years.length - 16;
  years.forEach((yr, i) => {
    const x = PAD_L + i * (innerW / years.length) + 8;
    const total = topGenres.reduce((s, g) => s + (yearCounts[yr][g] || 0), 0) || 1;
    let cum = 0;
    topGenres.forEach(g => {
      const v = (yearCounts[yr][g] || 0) / total;
      const start = cum; cum += v;
      const y = PAD_T + start * innerH;
      const h = v * innerH;
      svgEl.appendChild(svg("rect", { x, y, width: bw, height: h, fill: colorOf(g) }));
    });
    const lab = svg("text", { x: x + bw / 2, y: PAD_T + innerH + 14, class: "ta-label", "text-anchor": "middle" });
    lab.textContent = String(yr);
    svgEl.appendChild(lab);
  });

  const legend = document.createElement("div");
  legend.className = "genre-legend";
  topGenres.forEach(g => {
    const item = document.createElement("span");
    const sw = document.createElement("i");
    sw.style.background = colorOf(g);
    item.appendChild(sw);
    item.appendChild(document.createTextNode(g));
    legend.appendChild(item);
  });
  root.appendChild(legend);
}
```

- [ ] **Step 4: Wire all three into main.js**

```javascript
import { render as renderTopArtists } from "./charts/top_artists.js";
import { render as renderSongAge } from "./charts/song_age.js";
import { render as renderGenre } from "./charts/genre_proportions.js";
// in init() after audioMap:
renderTopArtists(document.getElementById("top-artists"), acts);
renderSongAge(document.getElementById("song-age"), acts);
renderGenre(document.getElementById("genre-proportions"), acts);
```

- [ ] **Step 5: Browser verify**

Expected: 20 horizontal gold bars in top-artists; 10-bucket histogram; 4 stacked year bars in genre with legend.

- [ ] **Step 6: Commit**

```bash
git add site_v2/js/charts/top_artists.js site_v2/js/charts/song_age.js site_v2/js/charts/genre_proportions.js site_v2/js/main.js
git commit -m "feat: Scene III top artists, song age, genre proportions"
```

---

## Task 8: Color charts — palette stacks + color wheel (Scene IV/1-2)

**Files:**
- Create: `site_v2/js/charts/palette_stacks.js`
- Create: `site_v2/js/charts/color_wheel.js`
- Modify: `site_v2/js/main.js`

Both filter `palette_source === 'youtube'` so unreliable bing data doesn't shape aggregate views.

- [ ] **Step 1: palette_stacks.js**

```javascript
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
```

- [ ] **Step 2: color_wheel.js**

```javascript
// site_v2/js/charts/color_wheel.js
import { isYTSource, isMedal, hexToHsv } from "../data.js";

const NS = "http://www.w3.org/2000/svg";
function svg(tag, attrs) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; }

export function render(root, acts) {
  const valid = acts.filter(isYTSource);
  const cx = 200, cy = 200, rMax = 170;

  while (root.firstChild) root.removeChild(root.firstChild);
  const wrap = document.createElement("div");
  wrap.className = "cw-wrap";
  const svgEl = svg("svg", { viewBox: "0 0 400 400", width: "100%" });
  wrap.appendChild(svgEl);
  const tip = document.createElement("div");
  tip.className = "chart-tooltip";
  wrap.appendChild(tip);
  root.appendChild(wrap);

  // Conic gradient hue ring via foreignObject
  const fo = svg("foreignObject", { x: cx - rMax - 12, y: cy - rMax - 12, width: (rMax + 12) * 2, height: (rMax + 12) * 2 });
  const ring = document.createElementNS("http://www.w3.org/1999/xhtml", "div");
  ring.style.cssText = "width:100%;height:100%;border-radius:50%;background:conic-gradient(from -90deg, hsl(0,70%,50%), hsl(60,70%,50%), hsl(120,70%,50%), hsl(180,70%,50%), hsl(240,70%,50%), hsl(300,70%,50%), hsl(360,70%,50%));mask:radial-gradient(circle at center, transparent 70%, black 71%, black 76%, transparent 77%);-webkit-mask:radial-gradient(circle at center, transparent 70%, black 71%, black 76%, transparent 77%);opacity:.4;";
  fo.appendChild(ring);
  svgEl.appendChild(fo);

  svgEl.appendChild(svg("circle", { cx, cy, r: rMax, fill: "none", stroke: "var(--border-quiet)", "stroke-width": 1 }));
  svgEl.appendChild(svg("circle", { cx, cy, r: 3, fill: "var(--text-tertiary)" }));

  [["0°", 0], ["90°", 90], ["180°", 180], ["270°", 270]].forEach(([t, deg]) => {
    const a = (deg - 90) * Math.PI / 180;
    const tx = cx + Math.cos(a) * (rMax + 14);
    const ty = cy + Math.sin(a) * (rMax + 14);
    const lab = svg("text", { x: tx, y: ty + 3, class: "cw-label", "text-anchor": "middle" });
    lab.textContent = t;
    svgEl.appendChild(lab);
  });

  valid.forEach(d => {
    const { h: H, s: S } = hexToHsv(d.dominant);
    const angle = (H * 360 - 90) * Math.PI / 180;
    const r = S * rMax * 0.95;
    const x = cx + Math.cos(angle) * r;
    const y = cy + Math.sin(angle) * r;
    const dot = svg("circle", {
      cx: x, cy: y,
      r: isMedal(d.placement) ? 7 : (d.placement && d.placement.includes && d.placement.includes("Pigskin") ? 5 : 4),
      fill: d.dominant,
      stroke: isMedal(d.placement) ? "var(--gold)" : "#000",
      "stroke-width": isMedal(d.placement) ? 1.5 : 0.5,
      class: "chart-dot",
    });
    dot.addEventListener("mousemove", ev => {
      while (tip.firstChild) tip.removeChild(tip.firstChild);
      tip.style.opacity = "1";
      tip.style.left = (ev.clientX + 14) + "px";
      tip.style.top = (ev.clientY + 14) + "px";
      const h4 = document.createElement("h4");
      h4.textContent = d.group + (d.theme ? " — " + d.theme : "");
      tip.appendChild(h4);
      const meta = document.createElement("div");
      meta.className = "meta";
      meta.textContent = d.year + " · " + d.placement;
      tip.appendChild(meta);
      const sw = document.createElement("div");
      sw.className = "swatches";
      d.palette.slice(0, 6).forEach(hh => {
        const cc = document.createElement("div");
        cc.style.background = hh;
        sw.appendChild(cc);
      });
      tip.appendChild(sw);
    });
    dot.addEventListener("mouseleave", () => tip.style.opacity = "0");
    svgEl.appendChild(dot);
  });
}
```

- [ ] **Step 3: Wire and verify**

```javascript
import { render as renderPaletteStacks } from "./charts/palette_stacks.js";
import { render as renderColorWheel } from "./charts/color_wheel.js";
renderPaletteStacks(document.getElementById("palette-stacks"), acts);
renderColorWheel(document.getElementById("color-wheel"), acts);
```

- [ ] **Step 4: Commit**

```bash
git add site_v2/js/charts/palette_stacks.js site_v2/js/charts/color_wheel.js site_v2/js/main.js
git commit -m "feat: Scene IV palette stacks + color wheel"
```

---

## Task 9: Color charts — sat-val scatter + extremes (Scene IV/3-4)

**Files:**
- Create: `site_v2/js/charts/sat_val_scatter.js`
- Create: `site_v2/js/charts/extremes.js`
- Modify: `site_v2/js/main.js`

- [ ] **Step 1: sat_val_scatter.js**

```javascript
// site_v2/js/charts/sat_val_scatter.js
import { isYTSource, isMedal } from "../data.js";

const NS = "http://www.w3.org/2000/svg";
function svg(tag, attrs) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; }
function svgText(parent, x, y, content, cls, anchor) {
  const t = svg("text", { x, y, class: cls, ...(anchor ? { "text-anchor": anchor } : {}) });
  t.textContent = content;
  parent.appendChild(t);
  return t;
}
function svgLine(parent, x1, y1, x2, y2, cls) {
  parent.appendChild(svg("line", { x1, y1, x2, y2, class: cls }));
}

export function render(root, acts) {
  const valid = acts.filter(isYTSource);
  const W = 700, H = 360, PAD_L = 50, PAD_R = 30, PAD_T = 20, PAD_B = 40;
  const innerW = W - PAD_L - PAD_R, innerH = H - PAD_T - PAD_B;

  while (root.firstChild) root.removeChild(root.firstChild);
  const svgEl = svg("svg", { width: "100%", viewBox: `0 0 ${W} ${H}`, style: "display:block;background:linear-gradient(180deg,var(--ink-3),var(--ink));border-radius:4px;" });
  root.appendChild(svgEl);

  const g = svg("g", { transform: `translate(${PAD_L},${PAD_T})` });
  svgEl.appendChild(g);

  for (let i = 1; i < 4; i++) {
    svgLine(g, 0, i * innerH / 4, innerW, i * innerH / 4, "chart-tick");
    svgLine(g, i * innerW / 4, 0, i * innerW / 4, innerH, "chart-tick");
  }
  svgLine(g, 0, innerH, innerW, innerH, "chart-axis");
  svgLine(g, 0, 0, 0, innerH, "chart-axis");
  ["0", ".25", ".5", ".75", "1"].forEach((t, i) => {
    svgText(g, i * innerW / 4, innerH + 14, t, "chart-axis-num", "middle");
    svgText(g, -8, innerH - i * innerH / 4 + 3, t, "chart-axis-num", "end");
  });
  svgText(g, innerW / 2, innerH + 32, "Saturation (muted → vivid)", "chart-axis-label", "middle");
  const yLab = svg("text", { x: -28, y: innerH / 2, class: "chart-axis-label", "text-anchor": "middle", transform: `rotate(-90, -28, ${innerH / 2})` });
  yLab.textContent = "Brightness";
  g.appendChild(yLab);

  valid.forEach(d => {
    const x = d.avg_sat * innerW;
    const y = (1 - d.avg_val) * innerH;
    const r = isMedal(d.placement) ? 7 : 5;
    const dot = svg("circle", {
      cx: x, cy: y, r, fill: d.dominant,
      stroke: isMedal(d.placement) ? "var(--gold)" : "#000",
      "stroke-width": isMedal(d.placement) ? 1.5 : 0.5,
      class: "chart-dot",
    });
    const t = svg("title", {});
    t.textContent = `${d.year} ${d.group}${d.theme ? " — " + d.theme : ""}`;
    dot.appendChild(t);
    g.appendChild(dot);
  });

  const exp = document.createElement("p");
  exp.className = "chart-explainer";
  const b1 = document.createElement("b"); b1.textContent = "Saturation"; exp.appendChild(b1);
  exp.appendChild(document.createTextNode(" is how vivid (vs muted) the palette is. "));
  const b2 = document.createElement("b"); b2.textContent = "Brightness"; exp.appendChild(b2);
  exp.appendChild(document.createTextNode(" is how light (vs dark). Top-right: punch-you-in-the-face. Bottom-left: muted-and-moody."));
  root.appendChild(exp);
}
```

- [ ] **Step 2: extremes.js**

```javascript
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
```

- [ ] **Step 3: Wire and verify, then commit**

```javascript
import { render as renderSatVal } from "./charts/sat_val_scatter.js";
import { render as renderExtremes } from "./charts/extremes.js";
renderSatVal(document.getElementById("sat-val-scatter"), acts);
renderExtremes(document.getElementById("extremes"), acts);
```

```bash
git add site_v2/js/charts/sat_val_scatter.js site_v2/js/charts/extremes.js site_v2/js/main.js
git commit -m "feat: Scene IV sat-val scatter + extremes callouts"
```

---

## Task 10: Verdict scene — Pigskin reveal + 1st-place spotlights (Scene V)

**Files:**
- Create: `site_v2/js/charts/winner_vs_participant.js`
- Modify: `site_v2/js/main.js`

Three sub-renders (the first two as helpers in main.js, the radar as its own module).

- [ ] **Step 1: Add helpers to main.js**

```javascript
import { isMedal, isPigskin } from "./data.js";

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

// in init():
renderPigskinReveal(document.getElementById("pigskin-reveal"), acts);
renderFirstPlaceSpotlights(document.getElementById("first-place-spotlights"), acts);
```

- [ ] **Step 2: winner_vs_participant.js (radar)**

```javascript
// site_v2/js/charts/winner_vs_participant.js
import { isPigskin } from "../data.js";

const NS = "http://www.w3.org/2000/svg";
function svg(tag, attrs) { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; }

export function render(root, acts) {
  const winners = acts.filter(a => isPigskin(a.placement) && a.valence != null);
  const losers = acts.filter(a => !isPigskin(a.placement) && a.valence != null);
  const features = ["valence", "energy", "danceability", "tempo"];
  const tempoMax = 200;

  function avg(group, key) {
    const vals = group.map(a => a[key]).filter(v => v != null);
    const m = vals.reduce((s, v) => s + v, 0) / (vals.length || 1);
    return key === "tempo" ? m / tempoMax : m;
  }
  const wAvg = features.map(k => avg(winners, k));
  const lAvg = features.map(k => avg(losers, k));

  const cx = 200, cy = 200, rMax = 130;

  while (root.firstChild) root.removeChild(root.firstChild);
  const h = document.createElement("h3"); h.className = "vp-h"; h.textContent = "Winner vs Participant — average audio fingerprint";
  root.appendChild(h);

  const svgEl = svg("svg", { viewBox: "0 0 400 400", width: "100%", style: "max-width:520px;display:block;margin:0 auto;" });
  root.appendChild(svgEl);

  features.forEach((f, i) => {
    const a = (i / features.length * 2 * Math.PI) - Math.PI / 2;
    const x = cx + Math.cos(a) * rMax;
    const y = cy + Math.sin(a) * rMax;
    svgEl.appendChild(svg("line", { x1: cx, y1: cy, x2: x, y2: y, class: "chart-tick" }));
    const lab = svg("text", { x: cx + Math.cos(a) * (rMax + 18), y: cy + Math.sin(a) * (rMax + 18) + 4, class: "vp-label", "text-anchor": "middle" });
    lab.textContent = f === "tempo" ? "tempo (norm.)" : f;
    svgEl.appendChild(lab);
  });
  [0.25, 0.5, 0.75, 1].forEach(p => {
    svgEl.appendChild(svg("circle", { cx, cy, r: rMax * p, fill: "none", stroke: "var(--border-quiet)", "stroke-width": 0.5 }));
  });
  function poly(values, color, fillOpacity) {
    const pts = values.map((v, i) => {
      const a = (i / features.length * 2 * Math.PI) - Math.PI / 2;
      return [cx + Math.cos(a) * rMax * v, cy + Math.sin(a) * rMax * v];
    });
    const d = "M " + pts.map(p => p.join(",")).join(" L ") + " Z";
    svgEl.appendChild(svg("path", { d, fill: color, "fill-opacity": fillOpacity, stroke: color, "stroke-width": 2 }));
  }
  poly(lAvg, "var(--text-tertiary)", 0.15);
  poly(wAvg, "var(--gold)", 0.3);

  const legend = document.createElement("div"); legend.className = "vp-legend";
  [["var(--gold)", `Pigskin (n=${winners.length})`], ["var(--text-tertiary)", `Participated (n=${losers.length})`]].forEach(([c, txt]) => {
    const span = document.createElement("span");
    const sw = document.createElement("i"); sw.style.background = c;
    span.appendChild(sw);
    span.appendChild(document.createTextNode(txt));
    legend.appendChild(span);
  });
  root.appendChild(legend);
}
```

- [ ] **Step 3: Wire**

```javascript
import { render as renderWvP } from "./charts/winner_vs_participant.js";
renderWvP(document.getElementById("winner-vs-participant"), acts);
```

- [ ] **Step 4: Verify and commit**

```bash
python3 -m http.server 8000 --directory site_v2 & sleep 1
echo "Verify: 33 verdict tiles total (12 medal-outlined, 4 gold-outlined); radar shows two overlaid shapes; 4 first-place spotlight cards."
pkill -f "http.server 8000" 2>/dev/null
git add site_v2/js/charts/winner_vs_participant.js site_v2/js/main.js
git commit -m "feat: Scene V verdict reveal + radar + first-place spotlights"
```

---

## Task 11: Encore (Scene VII)

**Files:**
- Modify: `site_v2/js/main.js`

Compute three big-number findings, render as Playfair-italic gold callouts above the "Fin." closer.

- [ ] **Step 1: Add encore renderer to main.js**

```javascript
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

// in init():
renderEncore(document.getElementById("big-numbers"), acts);
```

- [ ] **Step 2: Verify + commit**

```bash
python3 -m http.server 8000 --directory site_v2 & sleep 1
echo "Verify: three big-number callouts, then 'Fin.', then credits."
pkill -f "http.server 8000" 2>/dev/null
git add site_v2/js/main.js
git commit -m "feat: Scene VII encore with derived big-number findings"
```

---

## Task 12: Cast tile click → audio map highlight

**Files:**
- Modify: `site_v2/js/main.js`

- [ ] **Step 1: Add the listener**

In `init()` after all charts rendered:

```javascript
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
```

- [ ] **Step 2: Verify + commit**

```bash
python3 -m http.server 8000 --directory site_v2 & sleep 1
echo "Click any tile in The Cast. Page scrolls to The Sound; matching audio map dot pulses for ~2s."
pkill -f "http.server 8000" 2>/dev/null
git add site_v2/js/main.js
git commit -m "feat: cast tile click highlights audio map dot"
```

---

## Task 13: Scrollama scene tracking

**Files:**
- Modify: `site_v2/js/main.js`

- [ ] **Step 1: Wire scrollama**

Add at end of init():

```javascript
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
```

- [ ] **Step 2: Verify + commit**

```bash
python3 -m http.server 8000 --directory site_v2 & sleep 1
echo "Scroll through full page. No console errors; .scene.in-view class toggles per scene (verify in devtools elements panel)."
pkill -f "http.server 8000" 2>/dev/null
git add site_v2/js/main.js
git commit -m "feat: scrollama scene tracking"
```

---

## Task 14: Final pre-cutover walkthrough

**Files:** none — pure verification.

- [ ] **Step 1: Walk all 7 scenes**

```bash
python3 -m http.server 8000 --directory site_v2 & sleep 1
echo "Open localhost:8000/. Slowly scroll through every scene. Verify:"
echo "  - Scene I: Curtain animates open, gold logo fades in"
echo "  - Scene II: 67 cast tiles; sort buttons reorder; click → scroll to audio map"
echo "  - Scene III: 4 charts render; tooltips work; year filter works on audio map"
echo "  - Scene IV: 4 color charts render with proper data"
echo "  - Scene V: 33 verdict tiles, radar with 2 overlaid shapes, 4 spotlight cards"
echo "  - Scene VI: 2 methodology paragraphs visible"
echo "  - Scene VII: 3 big numbers, Fin., credits"
echo "  - No console errors"
read -p "Press enter when verified..."
pkill -f "http.server 8000" 2>/dev/null
```

- [ ] **Step 2: If anything broken, fix it and re-commit before Task 15.**

---

## Task 15: Cutover — promote site_v2 to site

**Files:**
- Move: `site/` → `site_legacy/`, `site_v2/` → `site/`
- Modify: `scripts/07_build_acts_json.py` (output path)
- Modify: `tests/test_build_acts_json.py` (output path)

- [ ] **Step 1: Rename directories**

```bash
cd /Users/raleightognela/Documents/sing_data
git mv site site_legacy
git mv site_v2 site
```

- [ ] **Step 2: Update build script output path**

In `scripts/07_build_acts_json.py`, change:
```python
OUT = BASE_DIR / "site_v2" / "data" / "acts.json"
```
to:
```python
OUT = BASE_DIR / "site" / "data" / "acts.json"
```

- [ ] **Step 3: Update test output path**

In `tests/test_build_acts_json.py`, change:
```python
OUT = ROOT / "site_v2" / "data" / "acts.json"
```
to:
```python
OUT = ROOT / "site" / "data" / "acts.json"
```

- [ ] **Step 4: Re-run build + tests**

```bash
python3 scripts/07_build_acts_json.py
python3 -m pytest tests/test_build_acts_json.py -v
```

Expected: prints "wrote 67 acts to site/data/acts.json"; tests pass.

- [ ] **Step 5: Final smoke test**

```bash
python3 -m http.server 8000 --directory site & sleep 1
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/
pkill -f "http.server 8000" 2>/dev/null
```

Expected: `200`. Final manual check in browser.

- [ ] **Step 6: Commit cutover**

```bash
git add -A
git commit -m "feat: cutover — promote site_v2 to site, archive previous as site_legacy"
```

---

## Self-review

**1. Spec coverage check:**
- Scene I (Curtain Rise) ✓ Tasks 2, 3, 4
- Scene II (Cast) ✓ Task 5; click→highlight ✓ Task 12
- Scene III (Sound) — Audio Map ✓ Task 6 (with valence/energy explainer); other 3 charts ✓ Task 7
- Scene IV (Color) — palette stacks/wheel ✓ Task 8; sat-val/extremes ✓ Task 9
- Scene V (Verdict) ✓ Task 10
- Scene VI (Behind the Curtain) ✓ Task 2 (HTML has the methodology copy inline)
- Scene VII (Encore) ✓ Task 11
- Cutover ✓ Task 15
- Acts.json data shape ✓ Task 1
- Bing-fallback consistent treatment: cast grid (Task 5), audio map (Task 6), aggregate color charts excluded (Tasks 8, 9)
- Scrollama wiring ✓ Task 13

**2. Placeholder scan:** No "TBD" / "TODO" / "implement later". Song-age uses popularity-as-proxy noted in Task 7 prose; acceptable v1.

**3. Type / API consistency:**
- Every chart module exports `render(root, acts)` and (optionally for audio_map) returns `{ highlight(matchFn) }`.
- `data.js` exports: `loadActs`, `hexToHsv`, `isMedal`, `isPigskin`, `isYTSource`, `PLACEMENT_ORDER`. All consumed correctly.
- The `cast-tile-click` event detail schema `{ year, group }` matches between Task 5 (dispatch) and Task 12 (listen).

**4. Scope check:** This plan produces a working site_v2 → site swap as a single integrated implementation. Each task self-contains its file edits + verification + commit. Reasonable for a single execution session.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-04-sing-redesign.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints for review.

**Which approach?**
