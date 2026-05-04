# Sing site — handoff for new context window

**Last updated:** 2026-05-04 (Auto mode session)
**Current branch:** `feat/site-redesign` — 19 commits ahead of `master`
**Local server:** `python3 -m http.server 8000 --directory site`

This doc tells a fresh Claude session everything it needs to push to GitHub, deploy as a website, and finish the loose ends. Read it top to bottom before doing anything irreversible.

---

## 1. Where things stand

### What's done
The redesigned site is fully built and tested at `site/`. 19 unmerged commits on `feat/site-redesign`. Old site preserved at `site_legacy/` for reference.

### Architecture (one-pager)
- `scripts/07_build_acts_json.py` reads `data/sing_enriched.parquet` + `data/color_palettes.csv` + `data/spotify_features.csv` → writes `site/data/acts.json` (67 acts, 2022–2025, all derived fields baked in).
- `site/index.html` — single-page scrollytelling, 7 scenes (Curtain → Cast → Sound → Color → Verdict → Behind the Curtain → Encore).
- `site/js/main.js` — orchestrator. Loads acts.json, renders all charts, wires per-act focus.
- `site/js/charts/*.js` — one ES module per chart. Each exports `render(root, acts)` returning `{ highlight, reset }` for focus integration.
- `site/css/{tokens,theatrical,editorial,charts}.css` — design system.

### Reference docs (in repo)
- Spec: `docs/superpowers/specs/2026-05-04-sing-redesign-design.md`
- Plan: `docs/superpowers/plans/2026-05-04-sing-redesign.md`
- This file: `docs/HANDOFF.md`

---

## 2. Loose ends before push

### A. Repo hygiene (160 untracked files in working tree)
The repo root is cluttered with notes/screenshots/scratch files. Decide:

**Option 1: Add to .gitignore + leave on disk.** Edit `.gitignore` to ignore:
```
# Working files / scratch
*.DS_Store
303451.png
download.jpeg
genre_dna_*.png
medley_recipe_*.png
plot_*.png
song_era_matrix_*.png
comic.txt

# Legacy palette swatches (already preserved in site_legacy/, don't dual-track)
data/palette_swatches/

# Build cache
__pycache__/
*.pyc
```

**Option 2: Move scratch out of repo.** Move them to `~/Documents/sing_data_scratch/` if they're personal notes.

**Option 3: Commit deliberately.** Some of those PNGs (`plot_*`, `medley_recipe_*`) might be intentional artifacts from earlier scripts. Verify before deciding.

**Recommended:** start with Option 1 — fastest path to a clean push.

### B. Tasks to verify (browser walkthrough)
Hard-refresh `http://localhost:8000/` (Cmd+Shift+R) and walk all 7 scenes. Specifically test:
- [ ] Curtain rises, gold "Sing" fades in, scope-note paragraph appears
- [ ] All 67 cast tiles render; sort buttons reorder; click tile → scrolls to Sound + focus bar appears at top
- [ ] Audio map: 65 dots, year filter works, medal dots have gold rings + labels, dimming when act focused
- [ ] Sing Jukebox: 20 bars (default), switches to single-act song list when focused
- [ ] Song Age: real age histogram (0-4 / 5-9 / 10-14 / 15-19 / 20-29 / 30-49 / 50+), single-act mode shows that act's songs only
- [ ] Genre proportions: 4 stacked year bars, single-act mode shows that act's genre tag breakdown
- [ ] Years in Color: 4 stacked palette strips, hover shows custom tooltip
- [ ] Color wheel: dots painted in their own colors, zoom buttons (All/Warm/Cool/Purple/Green) work
- [ ] Sat × Brightness: zoom buttons (All/Vivid+Bright/Vivid+Dark/Muted+Bright/Muted+Dark) work
- [ ] Extremes: 4 cards (Most Vivid, Most Muted, Brightest, Darkest)
- [ ] Verdict: 33 Pigskin tiles + 4 first-place spotlights, click any to focus
- [ ] Behind the Curtain: 2 method paragraphs side-by-side
- [ ] Encore: 10 fun-fact cards (hero + 9), Fin removed
- [ ] "× show all" button clears focus on all charts

### C. Known accepted compromises
- 5 acts (out of 67) fall back to bing-scraped palettes — visibly dimmer in cast grid, excluded from aggregate color charts.
- 2 acts have no Spotify audio features — listed as "Not on map" footnote under Audio Map.
- The data covers 2022–2025 only. Pre-2022 acts exist in `baylor-sing-all-acts-final.csv` but aren't surfaced.

---

## 3. Push to GitHub

The repo has no remote configured yet. Set it up:

### Create the GitHub repo
On github.com (already-logged-in user): create a new repo, suggested name `sing-data` or `baylor-sing`. **Do not** initialize with README/license — repo already has both.

### Wire the remote and push
```bash
cd /Users/raleightognela/Documents/sing_data

# Add the remote (replace with the actual URL GitHub gives you)
git remote add origin https://github.com/<USER>/<REPO>.git

# First push: master
git checkout master
git push -u origin master

# Then push the feature branch
git checkout feat/site-redesign
git push -u origin feat/site-redesign
```

### Choose how to merge
- **Path A: Squash + merge in GitHub.** Open a PR `feat/site-redesign → master`, review the 19 commits, squash-merge into master. Cleaner history.
- **Path B: Fast-forward merge locally then push.** Skip the PR ceremony — `git checkout master && git merge feat/site-redesign --ff-only && git push`. Faster but no review trail.

**Recommended:** Path A — opens the door to GitHub Pages deploying from `master` automatically and gives you a PR URL to share.

---

## 4. Deploy as a website (GitHub Pages)

The site is pure static HTML/CSS/JS — perfect for GitHub Pages. No build step.

### Option A: Pages from `/site` subfolder of master (simplest)
1. In the GitHub repo, **Settings → Pages**.
2. Source: **Deploy from a branch**.
3. Branch: `master`, folder: `/site`.
4. Save. URL will be `https://<USER>.github.io/<REPO>/`.

GitHub Pages requires the source folder to live at repo root or `/docs`. **`/site` is supported as a custom path** in newer Pages settings; if not visible, fall back to Option B.

### Option B: Pages from a dedicated `gh-pages` branch
If `/site` isn't selectable, create a deploy branch that contains only the site folder's contents:
```bash
git worktree add /tmp/sing-pages gh-pages 2>/dev/null || \
  git checkout --orphan gh-pages

# Copy site/ contents to root of gh-pages
git rm -rf . 2>/dev/null
cp -r site/* .
git add .
git commit -m "deploy: initial Pages snapshot"
git push -u origin gh-pages
```

Then in **Settings → Pages**, choose `gh-pages` branch, root folder.

### Option C: A different host
Netlify, Vercel, Cloudflare Pages all auto-deploy a static folder on push. Point them at the `site/` directory. Cloudflare Pages is free + fast.

### After deploy: verify
Open the public URL. Check that `data/acts.json` loads (browser devtools Network tab) — the JSON file is 57 KB and must be in the deployed folder, not gitignored.

### Optional: custom domain
If a domain like `singdata.com` exists, in **Settings → Pages → Custom domain**, add it. Add a CNAME file at the root of the deploy folder with the domain string. DNS: CNAME record pointing to `<USER>.github.io`.

---

## 5. Future-state TODOs (out of scope for this push, worth tracking)

### Data
- Re-run Spotify enrichment if/when the Kaggle dataset gets newer release-year data (current cutoff ~2019 — 2020+ songs show as 0-yr age).
- Consider adding the 2026 acts once Sing 2026 happens and YT videos appear.
- 5 bing-fallback acts: try the android-fallback yt-dlp again periodically — 2 of them might come back as YT-derived if videos get unprivated.

### UX polish
- Keyboard navigation (arrow keys to move between cast tiles).
- Share-link feature: `?act=2024-Kappa+Omega+Tau` deep-links to a focused act on load.
- Lazy-load chart modules per scene as scrollama enters them (negligible perf gain at current size).

### Accessibility
- Add `aria-pressed` to sort buttons, `aria-label` on chart-zoom buttons.
- Add alt text or `role="img"` for the SVG charts.
- Wrap the seven scenes in a `<main>` landmark.

### Color extraction quality
- Some bright stage lighting still washes out costume color. Could try foreground segmentation (rembg or MediaPipe) in `scripts/03_color_extract.py` for acts where the painted backdrop dominates.
- Track which acts the user flagged as "wrong palette" — none surfaced beyond 2022 ATO so far, but the audit grid in `.superpowers/brainstorm/.../content/audit-grid.html` was the tool used to find them.

---

## 6. Quick reference

### Rebuild data + restart server
```bash
cd /Users/raleightognela/Documents/sing_data
python3 scripts/07_build_acts_json.py
python3 -m pytest tests/test_build_acts_json.py -v
pkill -f "http.server 8000" 2>/dev/null
python3 -m http.server 8000 --directory site --bind 127.0.0.1 > /tmp/sing-server.log 2>&1 &
open http://localhost:8000/
```

### Bump cache version after editing chart JS
Edit `site/index.html`: `<script type="module" src="js/main.js?v=N">`. Increment N. Tells browsers to re-fetch the entry script and (when paired with hard-refresh) the imports.

### Files most likely to need future edits
- `site/js/main.js` — encore facts, focus wiring
- `site/js/charts/*.js` — chart-specific
- `site/css/charts.css` — chart styling (huge file)
- `scripts/07_build_acts_json.py` — adds derived fields to acts.json
