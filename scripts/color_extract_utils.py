"""Utilities for color palette extraction and HSV statistics."""

from __future__ import annotations

import colorsys
from pathlib import Path

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans


def _rgb_to_hsv_array(rgb: np.ndarray) -> np.ndarray:
    """Vectorized RGB->HSV. Input shape (N, 3) in [0, 255]. Output in [0, 1]."""
    rgb = rgb / 255.0
    r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]
    mx = rgb.max(axis=1)
    mn = rgb.min(axis=1)
    diff = mx - mn

    h = np.zeros_like(mx)
    mask = diff > 0
    rmask = mask & (mx == r)
    gmask = mask & (mx == g)
    bmask = mask & (mx == b)
    h[rmask] = ((g[rmask] - b[rmask]) / diff[rmask]) % 6
    h[gmask] = ((b[gmask] - r[gmask]) / diff[gmask]) + 2
    h[bmask] = ((r[bmask] - g[bmask]) / diff[bmask]) + 4
    h = h / 6.0

    s = np.zeros_like(mx)
    s[mx > 0] = diff[mx > 0] / mx[mx > 0]
    return np.stack([h, s, mx], axis=1)


def extract_act_palette(
    images: list[Image.Image],
    n_colors: int = 10,
    v_min: float = 0.20,
    s_min: float = 0.15,
    resize: int = 250,
) -> list[dict]:
    """Pool pixels from all act frames, mask background+desat, KMeans once.

    This gives much better costume-color recovery than per-frame palette →
    re-cluster: it keeps the full pixel signal and drops the dark stage
    background + heavily-desaturated wash that dominates raw clustering.
    """
    pixel_chunks = []
    for img in images:
        small = img.resize((resize, resize)).convert("RGB")
        pixel_chunks.append(np.array(small).reshape(-1, 3))
    pixels = np.concatenate(pixel_chunks).astype(np.float64)

    hsv = _rgb_to_hsv_array(pixels)
    mask = (hsv[:, 2] >= v_min) & (hsv[:, 1] >= s_min)
    masked = pixels[mask]

    # If too aggressive, relax to just the brightness floor
    if len(masked) < n_colors * 20:
        mask = hsv[:, 2] >= v_min
        masked = pixels[mask]
    if len(masked) < n_colors * 5:
        masked = pixels  # last-resort fallback

    km = KMeans(n_clusters=n_colors, n_init=10, random_state=42)
    km.fit(masked)
    counts = np.bincount(km.labels_, minlength=n_colors)
    proportions = counts / counts.sum()

    palette = []
    for i in range(n_colors):
        r, g, b = (max(0, min(255, int(round(c)))) for c in km.cluster_centers_[i])
        palette.append({
            "hex": f"#{r:02X}{g:02X}{b:02X}",
            "rgb": (r, g, b),
            "proportion": float(proportions[i]),
        })
    palette.sort(key=lambda x: x["proportion"], reverse=True)
    return palette


def extract_palette(img: Image.Image, n_colors: int = 6) -> list[dict]:
    """Extract dominant colors from an image using k-means clustering.

    Args:
        img: PIL Image to analyze.
        n_colors: Number of dominant colors to extract.

    Returns:
        List of dicts with keys: hex, rgb, proportion.
        Sorted by proportion (most dominant first).
    """
    # Resize for speed and convert to RGB
    img_resized = img.resize((200, 200)).convert("RGB")
    pixels = np.array(img_resized).reshape(-1, 3).astype(np.float64)

    kmeans = KMeans(n_clusters=n_colors, n_init=10, random_state=42)
    kmeans.fit(pixels)

    # Count pixels per cluster
    labels = kmeans.labels_
    counts = np.bincount(labels, minlength=n_colors)
    proportions = counts / counts.sum()

    # Build palette entries
    centers = kmeans.cluster_centers_
    palette: list[dict] = []
    for i in range(n_colors):
        r, g, b = int(round(centers[i][0])), int(round(centers[i][1])), int(round(centers[i][2]))
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        palette.append({
            "hex": f"#{r:02X}{g:02X}{b:02X}",
            "rgb": (r, g, b),
            "proportion": float(proportions[i]),
        })

    # Sort by proportion descending
    palette.sort(key=lambda x: x["proportion"], reverse=True)
    return palette


def compute_hsv_stats(palette: list[dict]) -> dict:
    """Compute weighted-average HSV values from a palette.

    Uses proportion as weight. All values returned in 0-1 range.

    Args:
        palette: List of palette dicts (must have 'rgb' and 'proportion' keys).

    Returns:
        Dict with avg_hue, avg_saturation, avg_brightness.
    """
    total_weight = sum(entry["proportion"] for entry in palette)
    if total_weight == 0:
        return {"avg_hue": 0.0, "avg_saturation": 0.0, "avg_brightness": 0.0}

    # Convert to HSV using circular mean for hue (to handle wrap-around)
    hue_sin_sum = 0.0
    hue_cos_sum = 0.0
    sat_sum = 0.0
    val_sum = 0.0

    for entry in palette:
        r, g, b = entry["rgb"]
        h, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        w = entry["proportion"]

        # Circular mean for hue
        angle = h * 2 * np.pi
        hue_sin_sum += w * np.sin(angle)
        hue_cos_sum += w * np.cos(angle)

        sat_sum += w * s
        val_sum += w * v

    avg_angle = np.arctan2(hue_sin_sum / total_weight, hue_cos_sum / total_weight)
    avg_hue = (avg_angle / (2 * np.pi)) % 1.0

    return {
        "avg_hue": float(avg_hue),
        "avg_saturation": float(sat_sum / total_weight),
        "avg_brightness": float(val_sum / total_weight),
    }


def render_swatch(
    palette: list[dict],
    path: Path,
    width: int = 300,
    height: int = 60,
) -> None:
    """Render a palette as a horizontal color bar PNG.

    Each color gets a proportional slice of the total width.

    Args:
        palette: List of palette dicts (must have 'rgb' and 'proportion' keys).
        path: Output PNG file path.
        width: Image width in pixels.
        height: Image height in pixels.
    """
    img = Image.new("RGB", (width, height))
    pixels = img.load()
    assert pixels is not None

    x_cursor = 0
    for i, entry in enumerate(palette):
        if i == len(palette) - 1:
            # Last color fills remaining pixels to avoid rounding gaps
            color_width = width - x_cursor
        else:
            color_width = int(round(entry["proportion"] * width))

        for x in range(x_cursor, min(x_cursor + color_width, width)):
            for y in range(height):
                pixels[x, y] = entry["rgb"]

        x_cursor += color_width

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(path), "PNG")
