"""Utilities for parsing songs and fuzzy-matching against the Kaggle Spotify dataset."""

from __future__ import annotations

import math
import re
from typing import Any

import pandas as pd
from rapidfuzz import fuzz, process

# Audio feature columns we care about from the Kaggle dataset.
KAGGLE_FEATURE_COLS: list[str] = [
    "track_name",
    "artist_name",
    "genre",
    "danceability",
    "energy",
    "valence",
    "tempo",
    "acousticness",
    "loudness",
    "popularity",
    "year",
]


# ── Song parsing ─────────────────────────────────────────────────────


def parse_songs(raw: Any) -> list[dict[str, str]]:
    """Parse semicolon-delimited song string into list of {title, artist} dicts.

    Format: "Title (Artist); Title2 (Artist2)"
    Songs without an artist paren get artist="".
    Handles nested parens in titles like "(Don't Fear) The Reaper (Blue Oyster Cult)".
    """
    if raw is None:
        return []
    if isinstance(raw, float) and math.isnan(raw):
        return []
    if not isinstance(raw, str) or not raw.strip():
        return []

    songs: list[dict[str, str]] = []

    for chunk in raw.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue

        title, artist = _extract_title_artist(chunk)
        songs.append({"title": title.strip(), "artist": artist.strip()})

    return songs


def _extract_title_artist(text: str) -> tuple[str, str]:
    """Extract title and artist from a single song entry.

    Strategy: find the *last* top-level parenthesized group. If the text before
    it looks like a valid song title (non-empty), treat the paren content as
    the artist. Otherwise, the whole string is the title.

    This correctly handles:
    - "Jolene (Dolly Parton)" -> ("Jolene", "Dolly Parton")
    - "(Don't Fear) The Reaper (Blue Oyster Cult)" -> ("(Don't Fear) The Reaper", "Blue Oyster Cult")
    - "(I've Had) The Time of My Life" -> ("(I've Had) The Time of My Life", "")
    - "Hey Jude" -> ("Hey Jude", "")
    - "Mother Knows Best (Donna Murphy (Tangled soundtrack))" -> ("Mother Knows Best", "Donna Murphy (Tangled soundtrack)")
    """
    # Find all top-level paren groups and their positions.
    # We want the last one that sits at the end of the string.
    # Use a regex that matches a paren group at the end, allowing nested parens.
    # Pattern: match opening ( , then balanced content, then ) at end of string.
    match = re.search(r"\(([^()]*(?:\([^()]*\)[^()]*)*)\)\s*$", text)

    if match:
        artist = match.group(1).strip()
        title = text[: match.start()].strip()
        if title:
            return title, artist
        # If title is empty, the whole thing is a title with parens (unlikely but safe)
        return text, ""

    return text, ""


# ── Kaggle fuzzy matching ────────────────────────────────────────────


def build_match_index(
    kaggle_df: pd.DataFrame,
) -> tuple[list[str], list[str], pd.DataFrame]:
    """Pre-build match-key lists for fast fuzzy lookup.

    Returns (combined_choices, title_only_choices, cleaned kaggle_df).
    combined_choices: "track - artist" strings for when we have both.
    title_only_choices: just track names for when artist is unknown.
    """
    df = kaggle_df[KAGGLE_FEATURE_COLS].copy()
    df["_match_key"] = (
        df["track_name"].fillna("").str.lower()
        + " - "
        + df["artist_name"].fillna("").str.lower()
    )
    df["_title_key"] = df["track_name"].fillna("").str.lower()
    combined = df["_match_key"].tolist()
    titles = df["_title_key"].tolist()
    return combined, titles, df


def fuzzy_match_kaggle(
    song: dict[str, str],
    kaggle_df: pd.DataFrame,
    threshold: int = 70,
    *,
    _cache: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Fuzzy-match a single song dict against the Kaggle dataset.

    Uses rapidfuzz process.extractOne on a pre-built 'track - artist' key
    for O(n) matching.

    Args:
        song: dict with 'title' and 'artist' keys.
        kaggle_df: Kaggle Spotify DataFrame with standard columns.
        threshold: minimum fuzzy score (0-100) to accept a match.
        _cache: optional dict for caching the match index between calls.

    Returns:
        dict with audio features + match_score, or None if no match.
    """
    # Build or retrieve the match index.
    if _cache is not None and "_combined" in _cache:
        combined = _cache["_combined"]
        titles = _cache["_titles"]
        df = _cache["_df"]
    else:
        combined, titles, df = build_match_index(kaggle_df)
        if _cache is not None:
            _cache["_combined"] = combined
            _cache["_titles"] = titles
            _cache["_df"] = df

    # Build query and pick the right choice list.
    title = song.get("title", "").lower()
    artist = song.get("artist", "").lower()

    if artist:
        # Match against "track - artist" keys.
        query = f"{title} - {artist}"
        choices = combined
    else:
        # No artist: match title-only against title-only keys.
        query = title
        choices = titles

    # Use rapidfuzz extractOne for fast matching.
    result = process.extractOne(
        query,
        choices,
        scorer=fuzz.token_sort_ratio,
        score_cutoff=threshold,
    )

    if result is None:
        return None

    matched_str, score, idx = result
    row = df.iloc[idx]

    output: dict[str, Any] = {}
    for col in KAGGLE_FEATURE_COLS:
        output[col] = row[col]
    output["match_score"] = round(score, 1)

    return output
