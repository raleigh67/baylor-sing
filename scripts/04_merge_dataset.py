"""
04_merge_dataset.py

Merges all enrichment outputs into a single master dataset:
  - Base: baylor-sing-all-acts-final.csv (290 acts)
  - Spotify features: data/spotify_features.csv (507 song rows -> aggregated per act)
  - Color palettes: data/color_palettes.csv (89 act rows)

Outputs:
  - data/sing_enriched.csv
  - data/sing_enriched.parquet
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# --- Column rename map (kaggle_ prefix -> clean names) ---
KAGGLE_RENAME = {
    "kaggle_danceability": "danceability",
    "kaggle_energy": "energy",
    "kaggle_valence": "valence",
    "kaggle_tempo": "tempo",
    "kaggle_acousticness": "acousticness",
    "kaggle_loudness": "loudness",
    "kaggle_genre": "genres",
    "kaggle_popularity": "popularity",
}

NUMERIC_AUDIO_COLS = [
    "kaggle_danceability",
    "kaggle_energy",
    "kaggle_valence",
    "kaggle_tempo",
    "kaggle_acousticness",
    "kaggle_loudness",
    "kaggle_popularity",
]


def load_base() -> pd.DataFrame:
    """Load the base act dataset."""
    path = ROOT / "baylor-sing-all-acts-final.csv"
    df = pd.read_csv(path)
    print(f"[base] Loaded {len(df)} acts from {path.name}")
    return df


def load_and_aggregate_spotify() -> pd.DataFrame | None:
    """Load spotify features, aggregate per act (year + group)."""
    path = DATA / "spotify_features.csv"
    if not path.exists():
        print(f"[spotify] {path.name} not found, skipping")
        return None

    df = pd.read_csv(path)
    print(f"[spotify] Loaded {len(df)} song rows from {path.name}")

    # Aggregate numeric columns: mean per (year, group)
    agg_numeric = (
        df.groupby(["year", "group"])[NUMERIC_AUDIO_COLS]
        .mean()
        .reset_index()
    )

    # Aggregate genres: concatenate unique, semicolon-separated
    def unique_genres(series: pd.Series) -> str:
        genres: list[str] = []
        for val in series.dropna():
            for g in str(val).split(";"):
                g = g.strip()
                if g and g not in genres:
                    genres.append(g)
        return ";".join(genres) if genres else ""

    agg_genre = (
        df.groupby(["year", "group"])["kaggle_genre"]
        .apply(unique_genres)
        .reset_index()
    )

    # Song count per act
    agg_count = (
        df.groupby(["year", "group"])
        .size()
        .reset_index(name="song_count")
    )

    # Merge aggregations together
    agg = agg_numeric.merge(agg_genre, on=["year", "group"]).merge(
        agg_count, on=["year", "group"]
    )

    # Rename columns
    agg = agg.rename(columns=KAGGLE_RENAME)
    # Rename merge keys to match base
    agg = agg.rename(columns={"year": "Year", "group": "Group"})

    print(f"[spotify] Aggregated to {len(agg)} act-level rows")
    return agg


def group_dir_to_name(group_dir: str) -> str:
    """Convert a group_dir like '2025_Alpha_Chi_Omega' back to group name.

    Strips the leading year prefix and converts underscores to spaces,
    except '_and_' which becomes ' & '.
    """
    # Remove year prefix: "2025_Alpha_Chi_Omega" -> "Alpha_Chi_Omega"
    parts = group_dir.split("_", 1)
    if len(parts) == 2 and parts[0].isdigit():
        name_part = parts[1]
    else:
        name_part = group_dir

    # Replace _and_ with & (before general underscore replacement)
    name_part = name_part.replace("_and_", " & ")
    # Replace remaining underscores with spaces
    name_part = name_part.replace("_", " ")
    return name_part


def normalize_group(name: str) -> str:
    """Normalize group name for matching: lowercase, strip non-alpha, collapse spaces."""
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9 &]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


def load_color_palettes(base_df: pd.DataFrame) -> pd.DataFrame | None:
    """Load color palettes and match back to base acts."""
    path = DATA / "color_palettes.csv"
    if not path.exists():
        print(f"[colors] {path.name} not found, skipping")
        return None

    df = pd.read_csv(path)
    print(f"[colors] Loaded {len(df)} rows from {path.name}")

    # Reverse group_dir to group name
    df["_group_name"] = df["group_dir"].apply(group_dir_to_name)
    df["_norm_name"] = df["_group_name"].apply(normalize_group)

    # Build lookup from base: normalized group name -> original group name per year
    base_lookup: dict[tuple[int, str], str] = {}
    for _, row in base_df.iterrows():
        yr = int(row["Year"])
        grp = str(row["Group"])
        key = (yr, normalize_group(grp))
        base_lookup[key] = grp

    # Match color rows to base group names
    matched_groups: list[str | None] = []
    for _, row in df.iterrows():
        yr = int(row["year"])
        norm = row["_norm_name"]
        key = (yr, norm)
        if key in base_lookup:
            matched_groups.append(base_lookup[key])
        else:
            # Fallback: use the reversed name directly
            matched_groups.append(row["_group_name"])
            print(f"  [colors] WARN: no exact match for {row['group_dir']}, using reversed name '{row['_group_name']}'")

    df["Group"] = matched_groups
    df = df.rename(columns={"year": "Year"})

    # Keep only the columns we want
    color_cols = [
        "Year",
        "Group",
        "palette_hex",
        "palette_proportions",
        "n_images",
        "avg_hue",
        "avg_saturation",
        "avg_brightness",
    ]
    df = df[color_cols]

    print(f"[colors] Matched {len(df)} act-level color rows")
    return df


def print_coverage(df: pd.DataFrame) -> None:
    """Print coverage statistics: for each column, show non-null counts."""
    total = len(df)
    print(f"\n{'=' * 60}")
    print(f"COVERAGE STATISTICS ({total} total acts)")
    print(f"{'=' * 60}")
    print(f"{'Column':<25} {'Non-null':>10} {'Coverage':>10}")
    print(f"{'-' * 25} {'-' * 10} {'-' * 10}")
    for col in df.columns:
        non_null = df[col].notna().sum()
        # Also exclude empty strings
        if df[col].dtype == object:
            non_null = (df[col].notna() & (df[col] != "")).sum()
        pct = non_null / total * 100
        print(f"{col:<25} {non_null:>10} {pct:>9.1f}%")
    print(f"{'=' * 60}\n")


def main() -> None:
    # 1. Load base
    base = load_base()

    # 2. Spotify merge
    spotify_agg = load_and_aggregate_spotify()
    if spotify_agg is not None:
        base = base.merge(spotify_agg, on=["Year", "Group"], how="left")
        print(f"[merge] After Spotify merge: {len(base)} rows")

    # 3. Color palette merge
    colors = load_color_palettes(base)
    if colors is not None:
        base = base.merge(colors, on=["Year", "Group"], how="left")
        print(f"[merge] After color merge: {len(base)} rows")

    # 4. Sanity check: should still be 289 acts (290 lines - 1 header)
    print(f"\n[result] Final dataset: {len(base)} rows x {len(base.columns)} columns")

    # 5. Save
    DATA.mkdir(exist_ok=True)
    csv_path = DATA / "sing_enriched.csv"
    parquet_path = DATA / "sing_enriched.parquet"

    base.to_csv(csv_path, index=False)
    base.to_parquet(parquet_path, index=False, engine="pyarrow")
    print(f"[save] Wrote {csv_path}")
    print(f"[save] Wrote {parquet_path}")

    # 6. Coverage stats
    print_coverage(base)


if __name__ == "__main__":
    main()
