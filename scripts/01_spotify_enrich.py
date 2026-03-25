#!/usr/bin/env python3
"""Spotify enrichment pipeline for Baylor Sing data.

Parses songs from baylor-sing-all-acts-final.csv, fuzzy-matches them against
the Kaggle Spotify dataset (1.16M tracks), and optionally calls the Spotify API
for additional metadata (genre, popularity, release year).

Outputs data/spotify_features.csv with per-song audio features.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd

# Ensure the project root is on sys.path so scripts/ is importable.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.spotify_enrich_utils import (  # noqa: E402
    KAGGLE_FEATURE_COLS,
    fuzzy_match_kaggle,
    parse_songs,
)

# ── Paths ────────────────────────────────────────────────────────────

ACTS_CSV = PROJECT_ROOT / "baylor-sing-all-acts-final.csv"
KAGGLE_CSV = PROJECT_ROOT / "spotify_data.csv"
OUTPUT_CSV = PROJECT_ROOT / "data" / "spotify_features.csv"

# ── Spotify API (optional) ───────────────────────────────────────────


def get_spotify_client() -> Any | None:
    """Return a spotipy.Spotify client if credentials are set, else None."""
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None
    try:
        import spotipy
        from spotipy.oauth2 import SpotifyClientCredentials

        auth = SpotifyClientCredentials(
            client_id=client_id, client_secret=client_secret
        )
        return spotipy.Spotify(auth_manager=auth)
    except Exception as e:
        print(f"[WARN] Could not init Spotify client: {e}")
        return None


def spotify_lookup(
    sp: Any, title: str, artist: str
) -> dict[str, Any] | None:
    """Search Spotify API for a track and return metadata.

    Returns dict with genre, release_year, spotify_popularity, or None.
    """
    query = f"track:{title}"
    if artist:
        query += f" artist:{artist}"
    try:
        results = sp.search(q=query, type="track", limit=1)
        items = results.get("tracks", {}).get("items", [])
        if not items:
            return None
        track = items[0]
        album = track.get("album", {})
        artist_id = (
            track.get("artists", [{}])[0].get("id") if track.get("artists") else None
        )

        # Get genre from artist endpoint.
        genre = ""
        if artist_id:
            artist_info = sp.artist(artist_id)
            genres = artist_info.get("genres", [])
            genre = genres[0] if genres else ""

        release_date = album.get("release_date", "")
        release_year = int(release_date[:4]) if release_date else None

        return {
            "spotify_genre": genre,
            "spotify_release_year": release_year,
            "spotify_popularity": track.get("popularity", 0),
        }
    except Exception as e:
        print(f"  [API ERR] {title}: {e}")
        return None


# ── Main pipeline ────────────────────────────────────────────────────


def run(
    *,
    limit: int | None = None,
    skip_api: bool = False,
    verbose: bool = True,
) -> pd.DataFrame:
    """Run the full enrichment pipeline.

    Args:
        limit: process only this many acts (for testing). None = all.
        skip_api: skip Spotify API calls even if credentials are set.
        verbose: print progress.

    Returns:
        DataFrame with enriched song-level data.
    """
    # 1. Load acts.
    acts_df = pd.read_csv(ACTS_CSV)
    if verbose:
        print(f"Loaded {len(acts_df)} acts from {ACTS_CSV.name}")

    # 2. Load Kaggle dataset.
    if verbose:
        print(f"Loading Kaggle dataset from {KAGGLE_CSV.name}...")
    t0 = time.time()
    kaggle_df = pd.read_csv(KAGGLE_CSV)
    if verbose:
        print(f"  {len(kaggle_df):,} tracks loaded in {time.time() - t0:.1f}s")

    # 3. Optional Spotify API client.
    sp = None
    if not skip_api:
        sp = get_spotify_client()
        if sp and verbose:
            print("Spotify API client initialized")
        elif verbose:
            print("No Spotify credentials found, skipping API calls")

    # 4. Parse all songs and fuzzy-match.
    rows: list[dict[str, Any]] = []
    match_cache: dict[str, Any] = {}

    acts_to_process = acts_df if limit is None else acts_df.head(limit)
    total_acts = len(acts_to_process)
    matched_count = 0
    total_songs = 0

    for i, act in acts_to_process.iterrows():
        songs = parse_songs(act.get("Songs"))
        if not songs:
            continue

        year = act.get("Year", "")
        group = act.get("Group", "")
        theme = act.get("Theme", "")
        placement = act.get("Placement", "")

        for song in songs:
            total_songs += 1
            row: dict[str, Any] = {
                "year": year,
                "group": group,
                "theme": theme,
                "placement": placement,
                "song_title": song["title"],
                "song_artist": song["artist"],
            }

            # Fuzzy match against Kaggle.
            match = fuzzy_match_kaggle(
                song, kaggle_df, threshold=65, _cache=match_cache
            )
            if match:
                matched_count += 1
                for col in KAGGLE_FEATURE_COLS:
                    row[f"kaggle_{col}"] = match[col]
                row["match_score"] = match["match_score"]
            else:
                for col in KAGGLE_FEATURE_COLS:
                    row[f"kaggle_{col}"] = None
                row["match_score"] = None

            # Optional Spotify API enrichment.
            if sp and match:
                api_data = spotify_lookup(sp, song["title"], song["artist"])
                if api_data:
                    row.update(api_data)
                # Be polite to the API.
                time.sleep(0.1)

            rows.append(row)

        if verbose and (int(i) + 1) % 50 == 0:
            print(f"  Processed {int(i) + 1}/{total_acts} acts...")

    result_df = pd.DataFrame(rows)

    if verbose:
        print(f"\nDone! {total_songs} songs parsed, {matched_count} matched "
              f"({matched_count / total_songs * 100:.0f}% hit rate)" if total_songs else "")

    # 5. Save output.
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(OUTPUT_CSV, index=False)
    if verbose:
        print(f"Saved to {OUTPUT_CSV}")

    return result_df


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Spotify enrichment pipeline")
    parser.add_argument(
        "--limit", type=int, default=None, help="Limit to N acts (for testing)"
    )
    parser.add_argument(
        "--skip-api",
        action="store_true",
        help="Skip Spotify API calls",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress progress output"
    )
    args = parser.parse_args()

    run(limit=args.limit, skip_api=args.skip_api, verbose=not args.quiet)
