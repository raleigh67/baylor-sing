"""Tests for color palette extraction utilities."""

from pathlib import Path

import pytest
from PIL import Image

from scripts.color_extract_utils import compute_hsv_stats, extract_palette, render_swatch


# ── extract_palette tests ────────────────────────────────────────────


class TestExtractPalette:
    def test_two_color_image(self) -> None:
        """Half-red, half-blue synthetic image should yield 2 dominant colors."""
        img = Image.new("RGB", (200, 200))
        pixels = img.load()
        assert pixels is not None
        for x in range(200):
            for y in range(200):
                pixels[x, y] = (255, 0, 0) if x < 100 else (0, 0, 255)

        palette = extract_palette(img, n_colors=2)

        assert len(palette) == 2
        # Both colors should have hex codes
        hex_codes = {entry["hex"] for entry in palette}
        assert all(h.startswith("#") and len(h) == 7 for h in hex_codes)
        # Should contain red and blue (order depends on proportion -- they're ~equal)
        rgb_values = {entry["rgb"] for entry in palette}
        assert (255, 0, 0) in rgb_values
        assert (0, 0, 255) in rgb_values

    def test_proportions_sum_to_one(self) -> None:
        """Proportions across the palette should sum to ~1.0."""
        img = Image.new("RGB", (100, 100), color=(128, 64, 32))
        palette = extract_palette(img, n_colors=3)
        total = sum(entry["proportion"] for entry in palette)
        assert abs(total - 1.0) < 1e-6

    def test_sorted_by_proportion_descending(self) -> None:
        """Palette entries should be sorted most-dominant first."""
        # 3/4 green, 1/4 white
        img = Image.new("RGB", (200, 200), color=(0, 255, 0))
        pixels = img.load()
        assert pixels is not None
        for x in range(50):
            for y in range(200):
                pixels[x, y] = (255, 255, 255)

        palette = extract_palette(img, n_colors=2)
        proportions = [entry["proportion"] for entry in palette]
        assert proportions == sorted(proportions, reverse=True)

    def test_default_n_colors(self) -> None:
        """Default n_colors=6 should return 6 entries."""
        img = Image.new("RGB", (100, 100), color=(100, 100, 100))
        palette = extract_palette(img)
        assert len(palette) == 6

    def test_hex_format(self) -> None:
        """Hex should be uppercase and match the RGB tuple."""
        img = Image.new("RGB", (100, 100), color=(255, 128, 0))
        palette = extract_palette(img, n_colors=1)
        entry = palette[0]
        r, g, b = entry["rgb"]
        expected_hex = f"#{r:02X}{g:02X}{b:02X}"
        assert entry["hex"] == expected_hex


# ── compute_hsv_stats tests ──────────────────────────────────────────


class TestComputeHsvStats:
    def test_pure_red(self) -> None:
        """Pure red: hue ~0, saturation 1, brightness 1."""
        palette = [{"hex": "#FF0000", "rgb": (255, 0, 0), "proportion": 1.0}]
        stats = compute_hsv_stats(palette)
        assert abs(stats["avg_hue"] - 0.0) < 0.01
        assert abs(stats["avg_saturation"] - 1.0) < 0.01
        assert abs(stats["avg_brightness"] - 1.0) < 0.01

    def test_values_in_range(self) -> None:
        """All HSV stats should be in [0, 1]."""
        palette = [
            {"hex": "#FF0000", "rgb": (255, 0, 0), "proportion": 0.5},
            {"hex": "#00FF00", "rgb": (0, 255, 0), "proportion": 0.3},
            {"hex": "#0000FF", "rgb": (0, 0, 255), "proportion": 0.2},
        ]
        stats = compute_hsv_stats(palette)
        for key in ("avg_hue", "avg_saturation", "avg_brightness"):
            assert 0.0 <= stats[key] <= 1.0, f"{key}={stats[key]} out of range"

    def test_weighted_by_proportion(self) -> None:
        """With 100% weight on one color, result should match that color's HSV."""
        palette = [
            {"hex": "#00FF00", "rgb": (0, 255, 0), "proportion": 1.0},
            {"hex": "#FF0000", "rgb": (255, 0, 0), "proportion": 0.0},
        ]
        stats = compute_hsv_stats(palette)
        # Pure green: hue ~0.333, sat 1.0, brightness 1.0
        assert abs(stats["avg_hue"] - 1 / 3) < 0.02
        assert abs(stats["avg_saturation"] - 1.0) < 0.01
        assert abs(stats["avg_brightness"] - 1.0) < 0.01

    def test_returns_expected_keys(self) -> None:
        palette = [{"hex": "#808080", "rgb": (128, 128, 128), "proportion": 1.0}]
        stats = compute_hsv_stats(palette)
        assert set(stats.keys()) == {"avg_hue", "avg_saturation", "avg_brightness"}


# ── render_swatch tests ──────────────────────────────────────────────


class TestRenderSwatch:
    def test_creates_file(self, tmp_path: Path) -> None:
        """render_swatch should create a PNG file at the given path."""
        palette = [
            {"hex": "#FF0000", "rgb": (255, 0, 0), "proportion": 0.6},
            {"hex": "#0000FF", "rgb": (0, 0, 255), "proportion": 0.4},
        ]
        out_path = tmp_path / "swatch.png"
        render_swatch(palette, out_path)
        assert out_path.exists()
        # Verify it's a valid image
        img = Image.open(out_path)
        assert img.size == (300, 60)

    def test_custom_dimensions(self, tmp_path: Path) -> None:
        palette = [{"hex": "#00FF00", "rgb": (0, 255, 0), "proportion": 1.0}]
        out_path = tmp_path / "swatch_wide.png"
        render_swatch(palette, out_path, width=600, height=100)
        img = Image.open(out_path)
        assert img.size == (600, 100)
