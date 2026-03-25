# The Sound & Color of Sing — Design Spec

## Overview

An interactive scrollytelling project analyzing 73 years of Baylor Sing competition data through two lenses: **sound** (music choices and audio characteristics) and **color** (visual aesthetics extracted from performance images). Built as a Python-generated static site with Scrollama.js for scroll-driven narrative and Plotly for interactive charts. Final project for a data visualization class.

## Goals

- Showcase analytical depth: turning a messy, incomplete historical dataset into rich insights
- Demonstrate creative data enrichment: Spotify API, Instagram scraping, image-based color extraction
- Tell a compelling visual story that stands out in a class setting
- Build a portfolio-worthy piece

## Dataset

**Source:** `baylor-sing-all-acts-final.csv` — 290 acts, 1953-2026

**Current columns:** Year, Group, Theme, Placement, Songs, YouTube_Link

**Known gaps:**
- 1954-1969: no data (17 missing years)
- Pre-2022 song data is spotty (often only 1 song per act identified)
- Only ~39 YouTube links
- No image/visual data currently
- 2022-2025 song data is comprehensive (~445 songs across ~65 acts)

## Data Enrichment Pipeline

Three Python scripts that produce a master enriched dataset.

### 01_spotify_enrich.py

**Input:** Song titles + artist names from CSV (primarily 2022-2025 data)

**Process (two data sources):**

1. **Kaggle dataset for audio features** — Spotify deprecated the `/audio-features` endpoint in Nov 2024 (returns 403). Instead, download a pre-scraped Kaggle dataset (e.g., [Spotify 1M Tracks](https://www.kaggle.com/datasets/amitanshjoshi/spotify-1million-tracks)) that contains tempo, energy, valence, danceability, acousticness, loudness. Fuzzy-match our ~445 songs against this dataset by track name + artist name.

2. **Spotify API for metadata still available** — Use `spotipy` to search each song and pull: genre (via artist endpoint), release year, album, popularity. These endpoints still work.

- Merge both sources: Kaggle provides the numeric audio features, Spotify API provides genre + release year + popularity
- Handle edge cases: covers vs. originals, fuzzy matching thresholds, multiple matches, failed lookups

**Output:** `data/spotify_features.csv` — one row per song with all audio features + metadata joined to act Year + Group

**Expected coverage:** ~90%+ match rate (songs are mostly well-known pop/rock hits likely present in the Kaggle dataset)

### 02_image_collect.py

**Input:** Act names + years from CSV

**Process (3 sources, in priority order):**
1. **@tomatbaylor Instagram** — use `instaloader` to scrape posts from this Sing-focused account. Match posts to acts via caption/hashtag parsing (group names, year references). This is the richest source for historical Sing imagery.
2. **Google/YouTube image search** — query `"[Group Name] Baylor Sing [Year]"` for each act. Use SerpAPI or `google-images-search`. Download top 3-5 results per act.
3. **YouTube frame extraction** — for the ~39 acts with YouTube links, use `yt-dlp` to download and `ffmpeg` to sample frames every 10-15 seconds.

**Output:** `data/images/` directory organized as `{year}_{group_name}/` with collected images per act. Metadata CSV tracking source, URL, and match confidence per image.

**Expected coverage:** Likely 60-80% of acts from 2000-2025. Earlier decades will be sparser.

### 03_color_extract.py

**Input:** Collected images from `data/images/`

**Process:**
- Load each image with Pillow
- Run k-means clustering (k=6) on pixel colors to find dominant palette
- Compute per-act aggregate: top 5-6 colors weighted by frequency
- Derive HSV statistics: average brightness, saturation, hue distribution
- For acts with multiple images, merge palettes with weighted averaging

**Output:** `data/color_palettes.csv` — one row per act with hex color codes, HSV stats, and source image count. Also `data/palette_swatches/` with rendered palette PNGs per act.

**Libraries:** scikit-learn (KMeans), Pillow, colorgram.py (alternative/validation)

### Master Dataset

A final merge script combines all three outputs with the original CSV into `data/sing_enriched.parquet` (and `.csv` for portability). This is the single source of truth for all visualizations.

## Scrollytelling Narrative Structure

Static HTML page using Scrollama.js for scroll-triggered transitions. Python generates all chart specs as Plotly JSON files that the HTML page loads.

### INTRO: "13 People in Waco Hall"

**Hook:** "In 1953, 13 people watched 8 clubs sing three songs each. 73 years later, it's Baylor's biggest tradition."

**Viz:** Animated number ticker (13 -> thousands). Historical photo if available from image collection.

**Purpose:** Establish context for non-Baylor viewers. Explain what Sing is: themed medleys, costumes, competition, tradition.

### ACT I: THE SOUND

#### Sound 1: "What Does Winning Sound Like?"

**Analysis:** Compare Spotify audio features (energy, tempo, valence, danceability) between winning/top-placing acts and the rest of the field.

**Viz:** Violin plots or beeswarm charts — winners vs. non-winners across each audio feature. Annotations calling out significant differences.

**Insight goal:** Do winners pick happier, higher-energy, more danceable songs? Or is there no clear audio "formula"?

#### Sound 2: "The Sing Jukebox"

**Analysis:** Most covered artists across all years. Distribution of "song age" (performance year minus song release year). Which artists tend to appear together in the same medley?

**Viz:** Bubble chart of top 15-20 most covered artists (size = count). Histogram of song age at time of performance. Optional: network graph of artist co-occurrences within medleys.

**Insight goal:** Is Sing getting more current or more nostalgic? Who are the go-to artists?

#### Sound 3: "Genre DNA of a Medley"

**Analysis:** Each act's medley represented as a genre composition. Genre diversity of winners vs. non-winners. Year-over-year genre trends.

**Viz:** Stacked bar per act (genre proportions). Streamgraph of genre share evolution across years.

**Insight goal:** Are winning medleys more genre-diverse? Is Sing getting more pop-dominated over time?

### ACT II: THE COLOR

#### Color 1: "The Palette of Performance"

**Analysis:** Each act rendered as its extracted 5-6 color palette. Trends in brightness, saturation across decades. Do winners use more saturated or brighter palettes?

**Viz:** Timeline of color swatches per act (scrollable grid). Scatter plot of brightness/saturation by placement. All-acts grid view where patterns emerge at scale.

**Insight goal:** Can you see visual trends in how Sing "looks" over time? Is there a color advantage?

#### Color 2: "Sound Meets Color"

**Analysis:** The "Sing Genome" — correlating audio features with color features. Do high-energy medleys pair with warm, bright colors? Do moodier palettes go with slower tempos?

**Viz:** Composite "genome cards" per act showing palette + audio radar chart + placement. Correlation heatmap of audio features vs. color features (brightness, saturation, hue warmth).

**Insight goal:** The payoff of combining both data dimensions. Even if correlations are weak, the visualization itself is novel and the null result is interesting.

### EXPLORE: "Your Turn"

**Interactive dashboard section** embedded at the end of the scroll page. Filter by year range, group, placement tier. Click any act to expand its genome card (palette, songs, audio profile, photo). Compare two acts side-by-side. Search by song title or artist name.

**Implementation:** This section uses heavier Plotly interactivity — dropdowns, sliders, click callbacks — all generated from Python and embedded as Plotly JSON.

### APPENDIX: "The Data Behind the Data"

**Optional closing section.** How the dataset was assembled: the ineligible songs list, Shazam attempts, Instagram mining, the 1954-1969 gap, the 2009 mystery year.

**Viz:** Data completeness heatmap (year x data field) showing where we have full vs. partial vs. no data. Pipeline diagram showing enrichment flow.

**Purpose:** Demonstrates to the professor that real data engineering work happened, not just chart-making.

## Tech Stack

### Python (data layer)
- **pandas** — data wrangling, merging, aggregation
- **spotipy** — Spotify Web API wrapper
- **instaloader** — Instagram post scraping
- **google-images-search** or **SerpAPI** — Google image search
- **yt-dlp** + **ffmpeg** — YouTube video frame extraction
- **Pillow** — image loading/processing
- **scikit-learn** — k-means clustering for color extraction
- **colorgram.py** — alternative color extraction (validation)
- **plotly** — all chart generation, exported as JSON specs

### HTML/CSS/JS (presentation layer)
- **Scrollama.js** — scroll-triggered narrative transitions
- **Plotly.js** — renders Python-generated chart JSON in browser
- **Custom CSS** — dark theme, typography, responsive layout
- Minimal JS: scroll triggers, chart loading, dashboard filter logic

### Hosting
- **GitHub Pages** — free, static site hosting. Single repo with both Python source and built HTML output.

## File Structure

```
sing_data/
  baylor-sing-all-acts-final.csv    # original dataset
  data/
    spotify_features.csv             # Spotify enrichment output
    images/                          # scraped images by act
    color_palettes.csv               # extracted palettes
    palette_swatches/                # rendered palette PNGs
    sing_enriched.parquet            # master merged dataset
  scripts/
    01_spotify_enrich.py
    02_image_collect.py
    03_color_extract.py
    04_merge_dataset.py
    05_generate_charts.py            # produces Plotly JSON specs
    06_build_site.py                 # assembles final HTML from templates
  site/
    index.html                       # main scrollytelling page
    css/
      style.css
    js/
      scroll.js                      # Scrollama setup + chart loading
      dashboard.js                   # interactive explorer logic
    charts/                          # Plotly JSON specs
    assets/                          # images, palette swatches for site
  docs/
    superpowers/specs/               # this spec
```

## Design Decisions

- **Python-first:** All analysis, enrichment, and chart generation in Python. JS is only for presentation plumbing (scroll triggers, chart rendering, filter UI).
- **Static site:** No server needed. Python builds everything ahead of time. The HTML page just loads pre-generated JSON chart specs. Simplifies hosting and makes it easy to submit as a class project.
- **Kaggle + Spotify API hybrid:** Spotify deprecated audio features in Nov 2024. We use a pre-scraped Kaggle dataset (~1M tracks) for tempo/energy/valence/danceability, and the live Spotify API for genre/release year/popularity. This gets us the full feature set without paying for alternative APIs.
- **2022-2025 scope for sound analysis:** Song data before 2022 is too incomplete for reliable audio analysis. Sound sections focus on the reliable window. Color analysis can span all years where images are found.
- **Dark theme:** Matches the theatrical/performance aesthetic of Sing. Color palettes pop on dark backgrounds.
- **Honest about gaps:** The appendix section treats data incompleteness as a feature, not a bug. Shows data literacy and intellectual honesty.
