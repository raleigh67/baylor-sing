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
OUT = BASE_DIR / "site" / "data" / "acts.json"


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
