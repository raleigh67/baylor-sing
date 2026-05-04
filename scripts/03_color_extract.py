#!/usr/bin/env python3
"""
03_color_extract.py -- Extract dominant color palettes from Baylor Sing performance images.

For each act directory in data/images/, extracts individual image palettes,
merges them via re-clustering, computes HSV stats, and renders swatch PNGs.

Outputs:
  data/color_palettes.csv
  data/palette_swatches/{year}_{group_safe}.png

Usage:
  python3 scripts/03_color_extract.py
  python3 scripts/03_color_extract.py --n-colors 8  # custom palette size
"""

from __future__ import annotations

import argparse
import csv
import warnings
from pathlib import Path

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans

from color_extract_utils import (
    compute_hsv_stats,
    extract_act_palette,
    extract_palette,
    render_swatch,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
IMAGE_DIR = BASE_DIR / "data" / "images"
OUTPUT_CSV = BASE_DIR / "data" / "color_palettes.csv"
SWATCH_DIR = BASE_DIR / "data" / "palette_swatches"

SKIP_SUBDIRS = {"instagram"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

CSV_FIELDNAMES = [
    "year",
    "group_dir",
    "palette_hex",
    "palette_proportions",
    "n_images",
    "image_source",
    "avg_hue",
    "avg_saturation",
    "avg_brightness",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_images(act_dir: Path) -> tuple[list[Image.Image], str]:
    """Load images from an act directory, preferring YT frames if any exist.

    Bing image search returns generic Baylor Sing photos that are reused
    across many acts (~84% of bing files are duplicates), so they pollute
    the palette. YouTube frames are act-specific and far more reliable.

    Returns (images, source_label) where source_label is 'youtube',
    'bing', or 'mixed'.
    """
    yt_imgs: list[Image.Image] = []
    bing_imgs: list[Image.Image] = []
    for f in sorted(act_dir.iterdir()):
        if not f.is_file():
            continue
        if f.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        try:
            img = Image.open(f)
            img.load()
        except Exception as e:
            print(f"  [WARN] Skipping {f.name}: {e}")
            continue
        if f.name.startswith("yt_"):
            yt_imgs.append(img)
        elif f.name.startswith("bing_"):
            bing_imgs.append(img)
        else:
            bing_imgs.append(img)

    if yt_imgs:
        return yt_imgs, "youtube"
    return bing_imgs, "bing"


def merge_palettes(
    palettes: list[list[dict]],
    n_colors: int,
) -> list[dict]:
    """Merge multiple palettes by re-clustering their color centers.

    Each center is weighted by its proportion. We expand centers into
    weighted pseudo-pixels and run KMeans again.

    Args:
        palettes: List of palette lists from individual images.
        n_colors: Number of colors in the merged palette.

    Returns:
        Merged palette sorted by proportion descending.
    """
    if not palettes:
        return []

    # Build weighted color array: repeat each center proportional to weight
    # Use 1000 pseudo-pixels total for a reasonable balance of speed and accuracy
    total_images = len(palettes)
    pseudo_n = 1000

    all_colors: list[np.ndarray] = []
    for palette in palettes:
        img_weight = 1.0 / total_images  # each image has equal weight
        for entry in palette:
            # Number of pseudo-pixels for this color
            count = max(1, int(round(entry["proportion"] * img_weight * pseudo_n)))
            color = np.array(entry["rgb"], dtype=np.float64)
            all_colors.extend([color] * count)

    if not all_colors:
        return []

    pixel_array = np.array(all_colors)

    # Suppress convergence warnings for small/uniform datasets
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        kmeans = KMeans(n_clusters=n_colors, n_init=10, random_state=42)
        kmeans.fit(pixel_array)

    labels = kmeans.labels_
    counts = np.bincount(labels, minlength=n_colors)
    proportions = counts / counts.sum()

    centers = kmeans.cluster_centers_
    palette: list[dict] = []
    for i in range(n_colors):
        r = max(0, min(255, int(round(centers[i][0]))))
        g = max(0, min(255, int(round(centers[i][1]))))
        b = max(0, min(255, int(round(centers[i][2]))))
        palette.append({
            "hex": f"#{r:02X}{g:02X}{b:02X}",
            "rgb": (r, g, b),
            "proportion": float(proportions[i]),
        })

    palette.sort(key=lambda x: x["proportion"], reverse=True)
    return palette


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def process_act(act_dir: Path, n_colors: int) -> dict | None:
    """Process a single act directory and return a CSV row dict, or None on skip."""
    dir_name = act_dir.name

    # Parse year from directory name (format: {year}_{group_safe})
    parts = dir_name.split("_", 1)
    if len(parts) < 2:
        print(f"  [WARN] Skipping {dir_name}: unexpected directory name format")
        return None

    year_str, group_dir = parts[0], dir_name

    try:
        year = int(year_str)
    except ValueError:
        print(f"  [WARN] Skipping {dir_name}: cannot parse year from '{year_str}'")
        return None

    # Load images (prefers YT frames over polluting bing images)
    images, source = load_images(act_dir)
    if not images:
        print(f"  [SKIP] {dir_name}: no valid images found")
        return None

    print(f"  {dir_name}: {len(images)} images ({source})")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            merged = extract_act_palette(images, n_colors=n_colors)
    except Exception as e:
        print(f"  [SKIP] {dir_name}: palette extraction failed: {e}")
        return None

    if not merged:
        return None

    hsv = compute_hsv_stats(merged)
    swatch_path = SWATCH_DIR / f"{group_dir}.png"
    render_swatch(merged, swatch_path)

    return {
        "year": year,
        "group_dir": group_dir,
        "palette_hex": ";".join(entry["hex"] for entry in merged),
        "palette_proportions": ";".join(f"{entry['proportion']:.4f}" for entry in merged),
        "n_images": len(images),
        "image_source": source,
        "avg_hue": f"{hsv['avg_hue']:.4f}",
        "avg_saturation": f"{hsv['avg_saturation']:.4f}",
        "avg_brightness": f"{hsv['avg_brightness']:.4f}",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract color palettes from Baylor Sing performance images"
    )
    parser.add_argument(
        "--n-colors",
        type=int,
        default=10,
        help="Number of colors per palette (default: 10)",
    )
    args = parser.parse_args()

    if not IMAGE_DIR.exists():
        print(f"ERROR: Image directory not found: {IMAGE_DIR}")
        return

    # Gather act directories
    act_dirs = sorted(
        d
        for d in IMAGE_DIR.iterdir()
        if d.is_dir() and d.name not in SKIP_SUBDIRS
    )

    print(f"Color Palette Extraction")
    print(f"{'=' * 60}")
    print(f"Image directory: {IMAGE_DIR}")
    print(f"Act directories: {len(act_dirs)}")
    print(f"Colors per palette: {args.n_colors}")
    print(f"{'=' * 60}\n")

    # Ensure output dirs exist
    SWATCH_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    for act_dir in act_dirs:
        row = process_act(act_dir, n_colors=args.n_colors)
        if row is not None:
            rows.append(row)

    # Write CSV
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n{'=' * 60}")
    print(f"Done! Processed {len(rows)} acts.")
    print(f"CSV: {OUTPUT_CSV.relative_to(BASE_DIR)}")
    print(f"Swatches: {SWATCH_DIR.relative_to(BASE_DIR)}/")


if __name__ == "__main__":
    main()
