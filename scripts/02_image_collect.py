#!/usr/bin/env python3
"""
02_image_collect.py -- Collect performance images for Baylor Sing acts.

Two sources:
  1. Bing Image Search (scraped, free, no API key) for acts 2000-2026
  2. YouTube frame extraction via yt-dlp + ffmpeg for acts with YouTube links

Usage:
  python3 scripts/02_image_collect.py              # both sources
  python3 scripts/02_image_collect.py --search-only # Bing images only
  python3 scripts/02_image_collect.py --youtube-only # YouTube frames only
  python3 scripts/02_image_collect.py --limit 5     # process only first N eligible acts
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "baylor-sing-all-acts-final.csv"
IMAGE_DIR = BASE_DIR / "data" / "images"
METADATA_CSV = BASE_DIR / "data" / "image_metadata.csv"

BING_MAX_RESULTS = 5         # download top 5 from Bing
SEARCH_DELAY = 2.0           # seconds between Bing requests
MIN_IMAGE_SIZE = 5 * 1024    # 5 KB -- skip tiny/placeholder images
YOUTUBE_FRAMES = 8           # frames to extract per video
REQUEST_TIMEOUT = 15         # seconds for HTTP requests

SEARCH_YEAR_MIN = 2000
SEARCH_YEAR_MAX = 2026

HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_name(group: str) -> str:
    """Turn group name into a filesystem-safe directory component."""
    name = group.strip()
    name = name.replace("&", "and")
    name = re.sub(r"[^A-Za-z0-9 _-]", "", name)
    name = re.sub(r"\s+", "_", name)
    return name


def act_dir(year: int | str, group: str) -> Path:
    """Return the output directory for an act."""
    return IMAGE_DIR / f"{year}_{safe_name(group)}"


def load_csv() -> list[dict[str, str]]:
    """Load the master CSV and return list of row dicts."""
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_existing_metadata() -> list[dict[str, str]]:
    """Load existing metadata CSV if it exists."""
    if not METADATA_CSV.exists():
        return []
    with open(METADATA_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_metadata(rows: list[dict[str, str]]) -> None:
    """Write metadata CSV (year, group, source, path)."""
    METADATA_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["year", "group", "source", "path"]
    with open(METADATA_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def already_has_images(year: int | str, group: str, source: str) -> bool:
    """Check if an act already has images from a given source (for resumability)."""
    d = act_dir(year, group)
    if not d.exists():
        return False
    prefix = "bing_" if source == "bing" else "yt_"
    return any(f.name.startswith(prefix) for f in d.iterdir() if f.is_file())


def download_image(url: str, dest: Path) -> bool:
    """Download a single image, skipping SVGs and tiny files. Returns True on success."""
    try:
        # Skip SVGs by URL
        if url.lower().split("?")[0].endswith(".svg"):
            return False

        resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers=HTTP_HEADERS)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        if "svg" in content_type.lower():
            return False
        # Skip non-image content
        if content_type and "image" not in content_type.lower() and "octet" not in content_type.lower():
            return False

        data = resp.content
        if len(data) < MIN_IMAGE_SIZE:
            return False

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return True
    except Exception as e:
        print(f"    [WARN] Failed to download {url[:80]}... -- {e}")
        return False


def guess_extension(url: str, default: str = ".jpg") -> str:
    """Guess file extension from URL."""
    lower = url.lower().split("?")[0]
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        if lower.endswith(ext):
            return ext
    return default


# ---------------------------------------------------------------------------
# Bing Image Search (scraping)
# ---------------------------------------------------------------------------

def bing_image_search(query: str, max_results: int = 5) -> list[str]:
    """Scrape Bing Images for full-res image URLs. Returns list of image URLs."""
    url = f"https://www.bing.com/images/search?q={quote_plus(query)}&first=1"
    try:
        resp = requests.get(url, headers=HTTP_HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        print(f"    [WARN] Bing request failed: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # Bing stores full-res URLs in the 'm' attribute of <a class="iusc"> tags
    image_urls: list[str] = []
    for a_tag in soup.find_all("a", class_="iusc"):
        m_attr = a_tag.get("m")
        if not m_attr:
            continue
        try:
            data = json.loads(m_attr)
            img_url = data.get("murl", "")
            if img_url and img_url.startswith("http"):
                image_urls.append(img_url)
        except (json.JSONDecodeError, TypeError):
            continue

        if len(image_urls) >= max_results:
            break

    return image_urls


def search_images_for_act(year: int, group: str) -> int:
    """Search Bing for act performance photos, download top results. Returns count saved."""
    d = act_dir(year, group)
    query = f"{group} Baylor Sing {year}"

    print(f"  [BING] Searching: {query}")
    image_urls = bing_image_search(query, max_results=BING_MAX_RESULTS)

    if not image_urls:
        print(f"    No results found.")
        return 0

    saved = 0
    for i, img_url in enumerate(image_urls):
        ext = guess_extension(img_url)
        dest = d / f"bing_{i:02d}{ext}"
        if dest.exists():
            saved += 1
            continue
        if download_image(img_url, dest):
            saved += 1

    print(f"    Saved {saved}/{len(image_urls)} images to {d.relative_to(BASE_DIR)}")
    return saved


def run_search_collection(acts: list[dict[str, str]], limit: int | None = None) -> list[dict[str, str]]:
    """Run Bing image search for eligible acts. Returns metadata rows."""
    eligible = [
        a for a in acts
        if SEARCH_YEAR_MIN <= int(a["Year"]) <= SEARCH_YEAR_MAX
    ]
    print(f"\n{'='*60}")
    print(f"Bing Image Search: {len(eligible)} acts eligible (years {SEARCH_YEAR_MIN}-{SEARCH_YEAR_MAX})")
    print(f"{'='*60}\n")

    if limit:
        eligible = eligible[:limit]
        print(f"  (limited to first {limit} acts)\n")

    metadata: list[dict[str, str]] = []
    skipped = 0
    searched = 0

    for act in eligible:
        year, group = act["Year"], act["Group"]
        if already_has_images(year, group, "bing"):
            skipped += 1
            continue

        search_images_for_act(int(year), group)
        searched += 1

        # Record metadata for saved images
        d = act_dir(year, group)
        if d.exists():
            for f in sorted(d.iterdir()):
                if f.is_file() and f.name.startswith("bing_"):
                    metadata.append({
                        "year": year,
                        "group": group,
                        "source": "bing",
                        "path": str(f.relative_to(BASE_DIR)),
                    })

        # Rate limit between searches
        time.sleep(SEARCH_DELAY)

    if skipped:
        print(f"\n  Skipped {skipped} acts (already had Bing images)")
    print(f"  Searched {searched} acts")

    return metadata


# ---------------------------------------------------------------------------
# YouTube Frame Extraction
# ---------------------------------------------------------------------------

def extract_youtube_frames(year: str, group: str, url: str) -> int:
    """Use yt-dlp + ffmpeg to extract frames from a YouTube video. Returns count saved."""
    d = act_dir(year, group)
    d.mkdir(parents=True, exist_ok=True)

    print(f"  [YT] Extracting frames: {group} ({year})")
    print(f"        URL: {url}")

    try:
        # Get video duration
        result = subprocess.run(
            ["yt-dlp", "--print", "duration", "--no-download", "--no-warnings", url],
            capture_output=True,
            text=True,
            timeout=30,
        )
        duration_str = result.stdout.strip()
        if not duration_str:
            print(f"    [WARN] Could not get video duration for {url}")
            return 0
        duration = float(duration_str)

        if duration < 10:
            print(f"    [WARN] Video too short ({duration:.0f}s), skipping")
            return 0

        # Evenly-spaced timestamps, skip first/last 5% (intros/outros)
        start = duration * 0.05
        end = duration * 0.95
        interval = (end - start) / (YOUTUBE_FRAMES - 1)
        timestamps = [start + i * interval for i in range(YOUTUBE_FRAMES)]

        # Get stream URL for direct ffmpeg seeking
        stream_result = subprocess.run(
            ["yt-dlp", "-f", "best[height<=720]/best", "--get-url", "--no-warnings", url],
            capture_output=True,
            text=True,
            timeout=30,
        )
        stream_url = stream_result.stdout.strip().split("\n")[0]
        if not stream_url:
            print(f"    [WARN] Could not get stream URL for {url}")
            return 0

        saved = 0
        for i, ts in enumerate(timestamps):
            out_path = d / f"yt_frame_{i:02d}.jpg"
            if out_path.exists() and out_path.stat().st_size >= MIN_IMAGE_SIZE:
                saved += 1
                continue

            try:
                subprocess.run(
                    [
                        "ffmpeg",
                        "-ss", f"{ts:.2f}",
                        "-i", stream_url,
                        "-frames:v", "1",
                        "-q:v", "2",
                        "-y",
                        str(out_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if out_path.exists() and out_path.stat().st_size >= MIN_IMAGE_SIZE:
                    saved += 1
                elif out_path.exists():
                    out_path.unlink()
            except subprocess.TimeoutExpired:
                print(f"    [WARN] ffmpeg timeout for frame {i} at {ts:.1f}s")
                if out_path.exists():
                    out_path.unlink()
            except Exception as e:
                print(f"    [WARN] ffmpeg error for frame {i}: {e}")

        print(f"    Saved {saved}/{YOUTUBE_FRAMES} frames to {d.relative_to(BASE_DIR)}")
        return saved

    except subprocess.TimeoutExpired:
        print(f"    [WARN] yt-dlp timeout for {url}")
        return 0
    except Exception as e:
        print(f"    [WARN] YouTube extraction failed: {e}")
        return 0


def run_youtube_collection(acts: list[dict[str, str]], limit: int | None = None) -> list[dict[str, str]]:
    """Extract frames from YouTube videos for all acts with links. Returns metadata rows."""
    eligible = [a for a in acts if a.get("YouTube_Link", "").strip()]
    print(f"\n{'='*60}")
    print(f"YouTube Frame Extraction: {len(eligible)} acts with video links")
    print(f"{'='*60}\n")

    if limit:
        eligible = eligible[:limit]
        print(f"  (limited to first {limit} acts)\n")

    metadata: list[dict[str, str]] = []
    skipped = 0

    for act in eligible:
        year, group = act["Year"], act["Group"]
        url = act["YouTube_Link"].strip()

        if already_has_images(year, group, "youtube"):
            skipped += 1
            continue

        extract_youtube_frames(year, group, url)

        # Record metadata for saved frames
        d = act_dir(year, group)
        if d.exists():
            for f in sorted(d.iterdir()):
                if f.is_file() and f.name.startswith("yt_"):
                    metadata.append({
                        "year": year,
                        "group": group,
                        "source": "youtube",
                        "path": str(f.relative_to(BASE_DIR)),
                    })

    if skipped:
        print(f"\n  Skipped {skipped} acts (already had YouTube frames)")

    return metadata


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect performance images for Baylor Sing acts"
    )
    parser.add_argument(
        "--search-only", action="store_true",
        help="Only run Bing image search (no YouTube)"
    )
    parser.add_argument(
        "--youtube-only", action="store_true",
        help="Only run YouTube frame extraction (no Bing)"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Limit to first N eligible acts per source"
    )
    args = parser.parse_args()

    acts = load_csv()
    print(f"Loaded {len(acts)} acts from CSV")

    # Load any existing metadata for merging
    existing_meta = load_existing_metadata()

    all_new_meta: list[dict[str, str]] = []

    if not args.youtube_only:
        search_meta = run_search_collection(acts, limit=args.limit)
        all_new_meta.extend(search_meta)

    if not args.search_only:
        yt_meta = run_youtube_collection(acts, limit=args.limit)
        all_new_meta.extend(yt_meta)

    # Merge: keep existing rows whose files still exist, add new ones
    merged: list[dict[str, str]] = []
    seen_paths: set[str] = set()

    for row in existing_meta:
        p = BASE_DIR / row["path"]
        if p.exists() and row["path"] not in seen_paths:
            merged.append(row)
            seen_paths.add(row["path"])

    for row in all_new_meta:
        if row["path"] not in seen_paths:
            merged.append(row)
            seen_paths.add(row["path"])

    save_metadata(merged)
    print(f"\nMetadata saved: {len(merged)} total entries in {METADATA_CSV.relative_to(BASE_DIR)}")
    print("Done.")


if __name__ == "__main__":
    main()
