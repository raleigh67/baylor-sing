# Video Script — Engineering & Data Aggregation

**Estimated runtime:** ~4:00 spoken
**Tone:** Direct, technical, but not stiff. Read it like you're walking another engineer through the project.
**Stage directions** are in *italics*.

---

## Open — the problem

> Baylor Sing is a sixty-year-old event with no real data infrastructure. There's a spreadsheet of acts. There are YouTube videos. There's a Spotify catalog that knows about most of the songs. But nobody had ever joined those three things. So that's what this project does — for 2022 through 2025, across sixty-seven acts.

*Cut to: terminal showing the repo tree.*

> The whole pipeline is six Python scripts and one JSON file. Let me walk through it.

---

## Data layer — three sources, one shape

> **Source one** is a hand-curated CSV. Two hundred and ninety rows. Year, group, theme, songs, placement, YouTube link. That's the spine.

> **Source two** is Spotify. For every named song in every act, we hit the API and pulled audio features — valence, energy, danceability, tempo — plus genre tags and release year. About four hundred and thirty songs got enriched.

> **Source three** is YouTube. For each act we wanted a video of the actual performance so we could pull frames and extract colors.

*Cut to: data/ directory listing.*

> All three feed into one file: `site/data/acts.json`. Sixty-seven act objects, every derived field pre-computed. The frontend does no math. That's deliberate — keeps the JavaScript focused on rendering, not on data wrangling.

---

## The hard part — finding the videos

> Finding YouTube links for sixty-seven specific Baylor Sing acts is harder than it sounds. The first version of this project was using Bing image search to get color data. Eighty-four percent of the images Bing returned were duplicate generic photos used across acts. So the colors weren't real — every act got the same wash of generic Baylor Sing brand colors.

> The fix was YouTube. There's a channel called *The Baylor Sing Archive* with five hundred and ninety-seven videos going back to 1970. We pulled the entire channel's metadata, parsed year and group out of each title with a regex, and matched them against the CSV. That got us a hundred and fifty solid matches.

> For 2022 through 2025 — which the archive doesn't cover — we ran per-act YouTube searches with carefully tuned queries. Group name, plus "Baylor Sing," plus the year. Scored each result on title-match, duration, year-in-title. Anything scoring seven or higher got auto-accepted.

> Two videos required a workaround. YouTube was blocking the default yt-dlp client for some uploads — the kind of bot-detection that just returns "video unavailable." Switching to `player_client=android` bypassed it. That recovered eleven videos we'd otherwise have lost.

*Cut to: terminal output of the YT audit run, showing the count climbing from 39 to 224 links.*

---

## Palette extraction — getting real colors

> For each act with a YouTube link, we pulled the video, sampled eight frames evenly across the runtime — skipping the first and last 5% to avoid intros — and ran K-means clustering on the pooled pixels. K equals ten colors.

*Cut to: a frame from an act + its palette swatch side-by-side.*

> Two filters before clustering. Drop near-black pixels — that's the audience and the dark stage floor. Drop deeply desaturated pixels — that's haze, smoke, stray light. What's left is mostly costume and set. The dominant color we surface is the most *vivid* one — highest saturation times brightness — out of the top six.

> One subtle thing: stage lighting tints everything. A white shirt under a magenta wash reads as mauve. The algorithm can't unbake that. So sometimes the dominant color is a tinted version of what was actually on stage, not the costume's pure color. We accept that — it reflects what the audience saw.

---

## The frontend stack

> The site is vanilla JavaScript. No React, no Vue, no D3, no build step. The reason is the entire thing is ten chart modules — each one a single function that takes a DOM node and a data array and renders SVG. That's small enough that a framework would have been ceremony for nothing.

*Cut to: VS Code showing `site/js/charts/` — ten short files.*

> Each chart module exports a `render` function and returns a small object with `highlight` and `reset` methods. That's the contract. The orchestrator in `main.js` keeps a registry of chart instances and broadcasts focus events.

> When you click any tile or dot, a `focus-act` custom event fires on `document`. Main.js listens, finds the matching act, and calls `highlight` on every chart with the same `matchFn` predicate. Each chart decides for itself what "highlighting an act" means. For the audio map, it dims everything except that dot. For the jukebox, it switches to that act's song list. For the genre chart, it switches to a single-act breakdown.

*Cut to: live demo of clicking a tile and watching every chart respond.*

---

## What it adds up to

> About eleven thousand lines of code across Python and JavaScript. Five build scripts. One JSON file. Ten chart modules. Two scenes of pure HTML/CSS theatrics. And the result is a sixty-seven-act archive you can navigate, focus, and read in any direction — by year, by placement, by hue, by sound, or by clicking one specific act and watching the whole site reframe around it.

> The whole thing runs as static files. No backend. You can deploy it to GitHub Pages, Netlify, or any folder a web server can point at.

*Cut to: pulling up the live site in the browser, scrolling through it once end-to-end.*

---

## Close

> The interesting engineering wasn't the charts. It was the data. Getting real per-act colors out of YouTube took most of the work. Once we had that, the visualization mostly wrote itself.
