# The Sound & Color of Sing — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a scrollytelling data visualization analyzing 73 years of Baylor Sing competition through music choices and visual aesthetics.

**Architecture:** Python enrichment pipeline (3 scripts) produces a master dataset. A chart generation script exports Plotly JSON specs. A static HTML site uses Scrollama.js for scroll-driven narrative and Plotly.js to render charts. All analysis happens in Python; JS is only presentation plumbing.

**Tech Stack:** Python 3.12+, pandas, spotipy, instaloader, Pillow, scikit-learn, plotly, rapidfuzz; HTML/CSS/JS with Scrollama.js + Plotly.js

**Spec:** `docs/superpowers/specs/2026-03-25-sound-and-color-of-sing-design.md`

---

## Phase 1: Project Setup & Data Enrichment Pipeline

### Task 1: Project scaffolding and dependencies

**Files:**
- Create: `requirements.txt`
- Create: `scripts/__init__.py` (empty, makes scripts importable for testing)
- Create: `data/.gitkeep`
- Create: `site/css/.gitkeep`
- Create: `site/js/.gitkeep`
- Create: `site/charts/.gitkeep`
- Create: `site/assets/.gitkeep`

- [ ] **Step 1: Create directory structure**

```bash
cd /Users/raleightognela/Documents/sing_data
mkdir -p scripts data site/css site/js site/charts site/assets
touch scripts/__init__.py data/.gitkeep site/css/.gitkeep site/js/.gitkeep site/charts/.gitkeep site/assets/.gitkeep
```

- [ ] **Step 2: Create requirements.txt**

```
pandas>=2.0
spotipy>=2.23
instaloader>=4.10
Pillow>=10.0
scikit-learn>=1.3
plotly>=5.18
rapidfuzz>=3.5
colorgram.py>=1.2
yt-dlp>=2024.1
openpyxl>=3.1
```

- [ ] **Step 3: Install dependencies**

```bash
pip install -r requirements.txt
```
Expected: All packages install successfully.

- [ ] **Step 4: Download Kaggle dataset**

Download the Spotify 1M Tracks dataset from https://www.kaggle.com/datasets/amitanshjoshi/spotify-1million-tracks.
Place the CSV file at `data/kaggle_spotify_tracks.csv`.

```bash
# Verify the file exists and has expected columns
python3 -c "
import pandas as pd
df = pd.read_csv('data/kaggle_spotify_tracks.csv', nrows=5)
print(f'Columns: {list(df.columns)}')
print(f'Shape: {df.shape}')
print(df.head(2))
"
```
Expected: Columns include track name, artist, tempo, energy, valence, danceability.

---

### Task 2: Spotify enrichment — Kaggle fuzzy matching

**Files:**
- Create: `scripts/01_spotify_enrich.py`
- Create: `scripts/spotify_enrich_utils.py`
- Create: `tests/test_spotify_enrich.py`

- [ ] **Step 1: Write test for song parsing from CSV**

```python
# tests/test_spotify_enrich.py
import pytest

def test_parse_songs_from_csv_row():
    """Songs column is semicolon-delimited with artist in parens."""
    from scripts.spotify_enrich_utils import parse_songs

    raw = "Jolene (Dolly Parton); Viva La Vida (Coldplay)"
    result = parse_songs(raw)
    assert result == [
        {"title": "Jolene", "artist": "Dolly Parton"},
        {"title": "Viva La Vida", "artist": "Coldplay"},
    ]

def test_parse_songs_empty():
    from scripts.spotify_enrich_utils import parse_songs
    assert parse_songs("") == []
    assert parse_songs(None) == []

def test_parse_songs_no_artist():
    """Some songs have no artist in parens."""
    from scripts.spotify_enrich_utils import parse_songs
    result = parse_songs("Jolene")
    assert result == [{"title": "Jolene", "artist": ""}]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_spotify_enrich.py -v
```
Expected: FAIL -- module not found.

- [ ] **Step 3: Write song parsing utility**

```python
# scripts/spotify_enrich_utils.py
"""Utilities for Spotify enrichment pipeline."""
import re
import pandas as pd


def parse_songs(raw: str | None) -> list[dict[str, str]]:
    """Parse semicolon-delimited songs with optional artist in parens.

    Format: "Title (Artist); Title2 (Artist2)"
    Returns: [{"title": "Title", "artist": "Artist"}, ...]
    """
    if not raw or (isinstance(raw, float) and pd.isna(raw)) or str(raw).strip() == "":
        return []

    songs = []
    for entry in str(raw).split(";"):
        entry = entry.strip()
        if not entry:
            continue
        match = re.match(r"^(.+?)\s*\(([^)]+)\)\s*$", entry)
        if match:
            songs.append({"title": match.group(1).strip(), "artist": match.group(2).strip()})
        else:
            songs.append({"title": entry.strip(), "artist": ""})
    return songs
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_spotify_enrich.py -v
```
Expected: 3 tests PASS.

- [ ] **Step 5: Write test for Kaggle fuzzy matching**

```python
# append to tests/test_spotify_enrich.py
def test_fuzzy_match_kaggle():
    """Match our songs against Kaggle dataset by title + artist."""
    from scripts.spotify_enrich_utils import fuzzy_match_kaggle
    import pandas as pd

    kaggle_df = pd.DataFrame({
        "track_name": ["Jolene", "Viva La Vida", "Bohemian Rhapsody"],
        "artists": ["Dolly Parton", "Coldplay", "Queen"],
        "tempo": [110.0, 138.0, 71.0],
        "energy": [0.6, 0.8, 0.4],
        "valence": [0.6, 0.4, 0.2],
        "danceability": [0.5, 0.5, 0.3],
    })

    song = {"title": "Jolene", "artist": "Dolly Parton"}
    result = fuzzy_match_kaggle(song, kaggle_df, threshold=70)
    assert result is not None
    assert result["tempo"] == 110.0
    assert result["energy"] == 0.6

def test_fuzzy_match_kaggle_no_match():
    from scripts.spotify_enrich_utils import fuzzy_match_kaggle
    import pandas as pd

    kaggle_df = pd.DataFrame({
        "track_name": ["Bohemian Rhapsody"],
        "artists": ["Queen"],
        "tempo": [71.0], "energy": [0.4], "valence": [0.2], "danceability": [0.3],
    })

    song = {"title": "Some Obscure Song", "artist": "Unknown Artist"}
    result = fuzzy_match_kaggle(song, kaggle_df, threshold=70)
    assert result is None
```

- [ ] **Step 6: Run test to verify it fails**

```bash
pytest tests/test_spotify_enrich.py::test_fuzzy_match_kaggle -v
```
Expected: FAIL -- function not defined.

- [ ] **Step 7: Implement fuzzy matching**

```python
# append to scripts/spotify_enrich_utils.py
from rapidfuzz import fuzz


def fuzzy_match_kaggle(
    song: dict[str, str],
    kaggle_df: pd.DataFrame,
    threshold: int = 70,
) -> dict | None:
    """Fuzzy match a song against Kaggle dataset. Returns best match or None."""
    title = song["title"].lower().strip()
    artist = song["artist"].lower().strip()

    best_score = 0
    best_idx = None

    for idx, row in kaggle_df.iterrows():
        k_title = str(row["track_name"]).lower().strip()
        k_artist = str(row["artists"]).lower().strip()

        title_score = fuzz.ratio(title, k_title)
        if artist:
            artist_score = fuzz.partial_ratio(artist, k_artist)
            combined = title_score * 0.6 + artist_score * 0.4
        else:
            combined = title_score

        if combined > best_score:
            best_score = combined
            best_idx = idx

    if best_score >= threshold and best_idx is not None:
        row = kaggle_df.loc[best_idx]
        return {
            "matched_title": row["track_name"],
            "matched_artist": row["artists"],
            "match_score": round(best_score, 1),
            "tempo": row.get("tempo"),
            "energy": row.get("energy"),
            "valence": row.get("valence"),
            "danceability": row.get("danceability"),
            "acousticness": row.get("acousticness"),
            "loudness": row.get("loudness"),
        }
    return None
```

- [ ] **Step 8: Run tests to verify they pass**

```bash
pytest tests/test_spotify_enrich.py -v
```
Expected: 5 tests PASS.

- [ ] **Step 9: Write the main enrichment script**

Create `scripts/01_spotify_enrich.py` — reads CSV, loads Kaggle dataset, fuzzy-matches all songs, optionally calls Spotify API for genre/release year/popularity, outputs `data/spotify_features.csv`. See spec for full details. The script should:
- Load `baylor-sing-all-acts-final.csv` and parse all songs
- Load `data/kaggle_spotify_tracks.csv` and fuzzy-match each song
- If `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` env vars are set, also call Spotify API for genre/release year/popularity
- Merge both sources and save to `data/spotify_features.csv`
- Print match rate statistics

- [ ] **Step 10: Test the enrichment script against real data (Kaggle only first)**

```bash
python3 -c "
import pandas as pd
from scripts.spotify_enrich_utils import parse_songs, fuzzy_match_kaggle
acts = pd.read_csv('baylor-sing-all-acts-final.csv')
kaggle = pd.read_csv('data/kaggle_spotify_tracks.csv')
print(f'Kaggle tracks: {len(kaggle)}')
test_songs = parse_songs(acts[acts['Year']==2025].iloc[0]['Songs'])
for s in test_songs[:3]:
    match = fuzzy_match_kaggle(s, kaggle)
    status = f'MATCH ({match[\"match_score\"]})' if match else 'NO MATCH'
    print(f'  {s[\"title\"]} by {s[\"artist\"]}: {status}')
"
```
Expected: At least some matches found.

- [ ] **Step 11: Run full enrichment**

```bash
export SPOTIFY_CLIENT_ID="2bf85714b94e4ed38cdc166e05454eed"
export SPOTIFY_CLIENT_SECRET="fe192150fdef46c0a3fbf54fbcadc8f5"
python3 scripts/01_spotify_enrich.py
```
Expected: `data/spotify_features.csv` created with enriched song data.

- [ ] **Step 12: Commit**

```bash
git add scripts/01_spotify_enrich.py scripts/spotify_enrich_utils.py tests/test_spotify_enrich.py requirements.txt data/spotify_features.csv
git commit -m "feat: add Spotify enrichment pipeline with Kaggle fuzzy matching"
```

---

### Task 3: Image collection — Instagram + Google + YouTube

**Files:**
- Create: `scripts/02_image_collect.py`

This task involves scraping and will require manual intervention if sources block requests. The script should be run interactively and is designed to be resumable.

- [ ] **Step 1: Write image collection script**

Create `scripts/02_image_collect.py` with three collection modes:

1. **Instagram** (`instaloader`): Scrape @tomatbaylor posts, match to acts via caption parsing (group names + year references). Copy matched images to `data/images/{year}_{group}/`.
2. **YouTube frames** (`yt-dlp` + `ffmpeg`): For acts with YouTube_Link, download lowest quality video, extract 8 frames at regular intervals, save as `frame_00.jpg` through `frame_07.jpg`.
3. **Google Images** (SerpAPI, optional): Search `"[Group] Baylor Sing [Year]"`, download top 3 results. Requires `SERPAPI_KEY` env var; skip gracefully if missing.

The script should:
- Be resumable (skip acts that already have images)
- Build a metadata CSV at `data/image_metadata.csv` cataloging all collected images
- Handle errors gracefully (print warnings, continue to next act)

- [ ] **Step 2: Test YouTube frame extraction on one video**

```bash
python3 -c "
from scripts.image_collect import extract_youtube_frames
import pandas as pd
acts = pd.read_csv('baylor-sing-all-acts-final.csv')
test = acts[acts['YouTube_Link'].notna()].head(1)
extract_youtube_frames(test, frames_per_video=3)
"
```
Expected: 3 frame JPGs in `data/images/{year}_{group}/`.

- [ ] **Step 3: Run Instagram scraping (may need manual fallback)**

```bash
python3 -c "from scripts.image_collect import scrape_instagram; scrape_instagram(max_posts=100)"
```
Expected: Downloads posts or prints fallback instructions if blocked.

- [ ] **Step 4: Run full image collection pipeline**

```bash
python3 scripts/02_image_collect.py
```
Expected: Images in `data/images/`, metadata at `data/image_metadata.csv`.

- [ ] **Step 5: Commit**

```bash
echo "data/images/" >> .gitignore
git add scripts/02_image_collect.py data/image_metadata.csv .gitignore
git commit -m "feat: add image collection pipeline (Instagram, YouTube, Google)"
```

---

### Task 4: Color palette extraction

**Files:**
- Create: `scripts/03_color_extract.py`
- Create: `scripts/color_extract_utils.py`
- Create: `tests/test_color_extract.py`

- [ ] **Step 1: Write test for color extraction from a single image**

```python
# tests/test_color_extract.py
import pytest


def test_extract_palette_returns_hex_colors():
    from scripts.color_extract_utils import extract_palette
    from PIL import Image

    # Create test image with known colors (red and blue halves)
    img = Image.new("RGB", (100, 100))
    pixels = img.load()
    for x in range(50):
        for y in range(100):
            pixels[x, y] = (255, 0, 0)
    for x in range(50, 100):
        for y in range(100):
            pixels[x, y] = (0, 0, 255)

    palette = extract_palette(img, n_colors=2)
    assert len(palette) == 2
    for color in palette:
        assert "hex" in color
        assert "rgb" in color
        assert "proportion" in color
        assert color["hex"].startswith("#")
        assert len(color["hex"]) == 7


def test_compute_hsv_stats():
    from scripts.color_extract_utils import compute_hsv_stats

    palette = [
        {"hex": "#FF0000", "rgb": (255, 0, 0), "proportion": 0.5},
        {"hex": "#0000FF", "rgb": (0, 0, 255), "proportion": 0.5},
    ]
    stats = compute_hsv_stats(palette)
    assert "avg_brightness" in stats
    assert "avg_saturation" in stats
    assert 0 <= stats["avg_brightness"] <= 1
    assert 0 <= stats["avg_saturation"] <= 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_color_extract.py -v
```
Expected: FAIL -- module not found.

- [ ] **Step 3: Implement color extraction utilities**

Create `scripts/color_extract_utils.py` with:
- `extract_palette(img, n_colors=6)` -- resize image to 200x200, run KMeans on pixels, return list of `{"hex", "rgb", "proportion"}` dicts sorted by proportion
- `compute_hsv_stats(palette)` -- weighted average of HSV values across palette, return `{"avg_hue", "avg_saturation", "avg_brightness"}`

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_color_extract.py -v
```
Expected: 2 tests PASS.

- [ ] **Step 5: Write main color extraction script**

Create `scripts/03_color_extract.py`:
- Iterate `data/images/` directories
- For each act: extract palette from each image, re-cluster merged palettes for final act palette
- Render swatch PNGs to `data/palette_swatches/`
- Save `data/color_palettes.csv` with hex colors, proportions, HSV stats, image count

- [ ] **Step 6: Test on real images (after Task 3 has run)**

```bash
python3 scripts/03_color_extract.py
```
Expected: `data/color_palettes.csv` created, swatches in `data/palette_swatches/`.

- [ ] **Step 7: Commit**

```bash
git add scripts/03_color_extract.py scripts/color_extract_utils.py tests/test_color_extract.py
git commit -m "feat: add color palette extraction with k-means clustering"
```

---

### Task 5: Master dataset merge

**Files:**
- Create: `scripts/04_merge_dataset.py`

- [ ] **Step 1: Write merge script**

Create `scripts/04_merge_dataset.py`:
- Load `baylor-sing-all-acts-final.csv` as base
- Load `data/spotify_features.csv`, aggregate per act (mean of audio features, concatenate genres), merge on Year + Group
- Load `data/color_palettes.csv`, merge on Year + group directory name
- Save to `data/sing_enriched.csv` and `data/sing_enriched.parquet`
- Print coverage statistics for each column

- [ ] **Step 2: Run merge**

```bash
python3 scripts/04_merge_dataset.py
```
Expected: `data/sing_enriched.csv` and `data/sing_enriched.parquet` created.

- [ ] **Step 3: Commit**

```bash
git add scripts/04_merge_dataset.py data/sing_enriched.csv
git commit -m "feat: add master dataset merge script"
```

---

## Phase 2: Chart Generation

### Task 6: Generate all Plotly chart specs

**Files:**
- Create: `scripts/05_generate_charts.py`

- [ ] **Step 1: Write chart generation script**

Create `scripts/05_generate_charts.py` that loads `data/sing_enriched.csv` and generates Plotly JSON specs in `site/charts/`. Apply a consistent dark theme (`#0a0a0f` background, light text). Generate these charts:

1. **sound1_energy.json, sound1_valence.json, sound1_danceability.json** -- Violin plots comparing winners vs. field for each audio feature
2. **sound2_top_artists.json** -- Horizontal bar chart of top 20 most covered artists
3. **sound2_song_age.json** -- Histogram of (performance year - song release year)
4. **sound3_genre_stream.json** -- Stacked area chart of top 10 genre proportions over time
5. **color1_brightness_scatter.json** -- Scatter plot of saturation vs. brightness colored by placement
6. **color2_correlation.json** -- Heatmap of audio features vs. color features correlation
7. **appendix_completeness.json** -- Heatmap of data completeness by year and field
8. **dashboard_data.json** -- Full enriched dataset as JSON array for dashboard

Each chart function should check for required data and print a skip message if missing.

- [ ] **Step 2: Run chart generation**

```bash
python3 scripts/05_generate_charts.py
```
Expected: JSON files in `site/charts/`.

- [ ] **Step 3: Quick visual check**

```bash
python3 -c "
import plotly.io as pio
from pathlib import Path
charts = list(Path('site/charts').glob('*.json'))
if charts:
    fig = pio.from_json(charts[0].read_text())
    fig.show()
    print(f'Opened {charts[0].name}')
"
```
Expected: Chart opens in browser with dark theme.

- [ ] **Step 4: Commit**

```bash
git add scripts/05_generate_charts.py site/charts/
git commit -m "feat: add Plotly chart generation for all scrollytelling sections"
```

---

## Phase 3: Scrollytelling Site

### Task 7: HTML structure and CSS theme

**Files:**
- Create: `site/index.html`
- Create: `site/css/style.css`

- [ ] **Step 1: Create the main HTML page**

Create `site/index.html` with this structure:
- `<head>`: load Plotly.js from CDN, Inter font from Google Fonts, link style.css
- **INTRO section**: title "The Sound & Color of Sing", subtitle, animated counter element (starts at 13), hook text
- **ACT I header**: "Act I / The Sound"
- **Sound sections** (sound1, sound2, sound3): each has `.scroll-text` on left (40% width) with `.step` elements containing narrative text and `data-chart` attributes, and `.scroll-graphic.sticky` on right with a chart container div
- **ACT II header**: "Act II / The Color"
- **Color sections** (color1, color2): same scroll layout
- **EXPLORE header**: "Explore / Your Turn"
- **Dashboard section**: controls (year range sliders, placement dropdown, search input) and an act grid container
- **APPENDIX**: scroll section with completeness chart
- **Footer**: attribution
- Load Scrollama.js from CDN, then `js/scroll.js` and `js/dashboard.js`

- [ ] **Step 2: Create the CSS dark theme**

Create `site/css/style.css` with:
- CSS variables: `--bg-dark: #0a0a0f`, `--bg-section: #111118`, `--accent-red: #e94560`, `--accent-blue: #0f3460`, `--accent-purple: #533483`, `--accent-green: #16c79a`
- Inter font family
- Full-viewport intro with gradient title text
- Act headers: centered, 50vh min-height
- Scroll sections: flexbox with 40% text / 60% sticky graphic
- Steps: 80vh min-height, start at 0.3 opacity, `.is-active` at full opacity
- Dashboard: grid layout for act cards, detail panel
- Act cards: dark bg, red hover border, palette bar at bottom (flex row of color divs)
- Responsive: stack vertically below 768px
- Dark footer with border-top

- [ ] **Step 3: Verify HTML loads in browser**

```bash
open site/index.html
```
Expected: Dark page loads with title and section headers. Charts empty until JS runs.

- [ ] **Step 4: Commit**

```bash
git add site/index.html site/css/style.css
git commit -m "feat: add scrollytelling HTML structure and dark theme CSS"
```

---

### Task 8: Scrollama JS and chart loading

**Files:**
- Create: `site/js/scroll.js`

- [ ] **Step 1: Write scroll controller**

Create `site/js/scroll.js`:
- Chart cache object to avoid re-fetching
- `loadChart(chartName, containerId)` -- fetch `charts/{name}.json`, call `Plotly.react()` with responsive config and no mode bar
- Map section IDs to chart container IDs
- `initScrollama()` -- for each section, set up a Scrollama scroller with 0.5 offset. On step enter: activate step (toggle `.is-active` class), load the chart named in `data-chart` attribute
- `animateCounter()` -- animate the intro counter from 13 to 3000 over 2 seconds with ease-out, triggered by IntersectionObserver
- Init both on DOMContentLoaded

- [ ] **Step 2: Test with a local server**

```bash
cd /Users/raleightognela/Documents/sing_data/site && python3 -m http.server 8080 &
```
Open http://localhost:8080. Expected: scrolling triggers chart loading and step highlighting.

- [ ] **Step 3: Commit**

```bash
git add site/js/scroll.js
git commit -m "feat: add Scrollama scroll controller and chart loading"
```

---

### Task 9: Dashboard JS (interactive explorer)

**Files:**
- Create: `site/js/dashboard.js`

- [ ] **Step 1: Write dashboard JS**

Create `site/js/dashboard.js`:
- `loadDashboardData()` -- fetch `charts/dashboard_data.json`, store in `allActs` array
- `renderGrid()` -- populate `#act-grid` with act cards. Each card shows year, group name, theme, and a palette bar (colored divs from palette_hex). Use `document.createElement` and DOM methods (not innerHTML) to build cards safely.
- `showDetail(index)` -- populate `#act-detail` with expanded info: year, placement, group, theme, audio stats (energy/valence/danceability as large numbers), palette swatches (colored divs), song list. Use DOM methods for safe rendering.
- `setupFilters()` -- wire up year range inputs, placement dropdown, and search box. On input, filter `allActs` into `filteredActs` and re-render grid.
- Init on DOMContentLoaded

- [ ] **Step 2: Regenerate charts with dashboard data**

```bash
python3 scripts/05_generate_charts.py
```

- [ ] **Step 3: Test dashboard in browser**

Scroll to "Your Turn" section. Verify: cards render, filters narrow results, clicking a card shows detail panel.

- [ ] **Step 4: Commit**

```bash
git add site/js/dashboard.js
git commit -m "feat: add interactive dashboard explorer with filters and act detail cards"
```

---

### Task 10: Build script and final assembly

**Files:**
- Create: `scripts/06_build_site.py`

- [ ] **Step 1: Write build script**

Create `scripts/06_build_site.py`:
- Copy `data/palette_swatches/` to `site/assets/swatches/`
- Run `scripts/05_generate_charts.py`
- Verify required files exist (index.html, style.css, scroll.js, dashboard.js, chart JSONs)
- Print site status summary and local serve instructions

- [ ] **Step 2: Run full build**

```bash
python3 scripts/06_build_site.py
```
Expected: site/ is complete.

- [ ] **Step 3: Final browser test**

```bash
cd /Users/raleightognela/Documents/sing_data/site && python3 -m http.server 8080
```
Walk through entire experience: intro animation, all scroll sections, dashboard, appendix.

- [ ] **Step 4: Commit**

```bash
git add scripts/06_build_site.py site/assets/
git commit -m "feat: add build script and finalize site assembly"
```

---

## Phase 4: Polish & Deploy

### Task 11: Visual polish and responsive fixes

- [ ] **Step 1: Review all charts for visual consistency** -- check titles, axes, colors, dark theme
- [ ] **Step 2: Test responsive layout at 375px width** -- verify stacked layout works
- [ ] **Step 3: Fix any issues found**
- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "polish: visual refinements and responsive fixes"
```

### Task 12: Deploy to GitHub Pages

- [ ] **Step 1: Create GitHub repo**

```bash
cd /Users/raleightognela/Documents/sing_data
git init
gh repo create baylor-sing-viz --public --source=. --push
```

- [ ] **Step 2: Configure GitHub Pages** -- Settings > Pages > Source: branch `main`, folder `/site`

- [ ] **Step 3: Verify deployment** -- check the live GitHub Pages URL

- [ ] **Step 4: Final commit with live URL**
