"""Tests for spotify enrichment utilities."""

import pandas as pd
import pytest

from scripts.spotify_enrich_utils import fuzzy_match_kaggle, parse_songs


# ── parse_songs tests ────────────────────────────────────────────────


class TestParseSongs:
    def test_single_song_with_artist(self) -> None:
        result = parse_songs("Jolene (Dolly Parton)")
        assert result == [{"title": "Jolene", "artist": "Dolly Parton"}]

    def test_multiple_songs_semicolon_delimited(self) -> None:
        raw = "Jolene (Dolly Parton); Viva La Vida (Coldplay)"
        result = parse_songs(raw)
        assert result == [
            {"title": "Jolene", "artist": "Dolly Parton"},
            {"title": "Viva La Vida", "artist": "Coldplay"},
        ]

    def test_song_without_artist(self) -> None:
        result = parse_songs("Hey Jude")
        assert result == [{"title": "Hey Jude", "artist": ""}]

    def test_mixed_with_and_without_artist(self) -> None:
        raw = "Hey Now; Phineas and Ferb Theme; I Want Candy"
        result = parse_songs(raw)
        assert len(result) == 3
        assert all(s["artist"] == "" for s in result)

    def test_empty_string(self) -> None:
        assert parse_songs("") == []

    def test_nan_input(self) -> None:
        assert parse_songs(float("nan")) == []

    def test_none_input(self) -> None:
        assert parse_songs(None) == []

    def test_artist_with_special_chars(self) -> None:
        raw = "Boogie Wonderland (Earth, Wind, & Fire)"
        result = parse_songs(raw)
        assert result == [
            {"title": "Boogie Wonderland", "artist": "Earth, Wind, & Fire"}
        ]

    def test_nested_parens_in_title(self) -> None:
        """Songs like '(I've Had) The Time of My Life' have parens in the title."""
        raw = "(I've Had) The Time of My Life"
        result = parse_songs(raw)
        # No artist paren at end, so full string is title
        assert result == [{"title": "(I've Had) The Time of My Life", "artist": ""}]

    def test_complex_artist_with_parens(self) -> None:
        """Artist field itself may contain parens, e.g. soundtrack info."""
        raw = "Mother Knows Best (Donna Murphy (Tangled soundtrack))"
        result = parse_songs(raw)
        assert result[0]["title"] == "Mother Knows Best"
        # Should capture the full artist including nested parens
        assert "Donna Murphy" in result[0]["artist"]

    def test_artist_with_slash(self) -> None:
        raw = "Ave Maria (Renee Fleming / Franz Schubert)"
        result = parse_songs(raw)
        assert result == [
            {"title": "Ave Maria", "artist": "Renee Fleming / Franz Schubert"}
        ]

    def test_multiple_complex_songs(self) -> None:
        raw = (
            "The Chain (Fleetwood Mac); "
            "Boogie Wonderland (Earth, Wind, & Fire); "
            "I Wanna Dance With Somebody (Whitney Houston)"
        )
        result = parse_songs(raw)
        assert len(result) == 3
        assert result[0] == {"title": "The Chain", "artist": "Fleetwood Mac"}
        assert result[1] == {
            "title": "Boogie Wonderland",
            "artist": "Earth, Wind, & Fire",
        }
        assert result[2] == {
            "title": "I Wanna Dance With Somebody",
            "artist": "Whitney Houston",
        }

    def test_title_with_paren_prefix_and_artist(self) -> None:
        """e.g. '(Don't Fear) The Reaper (Blue Oyster Cult)'"""
        raw = "(Don't Fear) The Reaper (Blue Oyster Cult)"
        result = parse_songs(raw)
        assert result == [
            {"title": "(Don't Fear) The Reaper", "artist": "Blue Oyster Cult"}
        ]

    def test_song_with_disney_source(self) -> None:
        """e.g. 'Tarzan (Disney)' -- Disney is the artist/source."""
        raw = "Tarzan (Disney)"
        result = parse_songs(raw)
        assert result == [{"title": "Tarzan", "artist": "Disney"}]

    def test_whitespace_trimmed(self) -> None:
        raw = "  Jolene (Dolly Parton) ;  Hey Jude  "
        result = parse_songs(raw)
        assert result[0]["title"] == "Jolene"
        assert result[0]["artist"] == "Dolly Parton"
        assert result[1]["title"] == "Hey Jude"


# ── fuzzy_match_kaggle tests ────────────────────────────────────────


@pytest.fixture
def sample_kaggle_df() -> pd.DataFrame:
    """Small Kaggle-like DataFrame for testing fuzzy matching."""
    return pd.DataFrame(
        {
            "track_name": [
                "Jolene",
                "Viva La Vida",
                "Bohemian Rhapsody",
                "Hey Jude",
                "Thriller",
            ],
            "artist_name": [
                "Dolly Parton",
                "Coldplay",
                "Queen",
                "The Beatles",
                "Michael Jackson",
            ],
            "genre": ["country", "alt-rock", "rock", "rock", "pop"],
            "danceability": [0.58, 0.50, 0.40, 0.44, 0.70],
            "energy": [0.47, 0.62, 0.73, 0.59, 0.80],
            "valence": [0.64, 0.34, 0.22, 0.54, 0.60],
            "tempo": [110.0, 138.0, 143.0, 147.0, 117.0],
            "acousticness": [0.71, 0.01, 0.05, 0.25, 0.04],
            "loudness": [-10.2, -5.3, -4.8, -6.9, -5.5],
            "popularity": [75, 85, 90, 80, 95],
            "year": [1973, 2008, 1975, 1968, 1982],
        }
    )


class TestFuzzyMatchKaggle:
    def test_exact_match_title_and_artist(
        self, sample_kaggle_df: pd.DataFrame
    ) -> None:
        song = {"title": "Jolene", "artist": "Dolly Parton"}
        result = fuzzy_match_kaggle(song, sample_kaggle_df)
        assert result is not None
        assert result["track_name"] == "Jolene"
        assert result["artist_name"] == "Dolly Parton"
        assert result["danceability"] == 0.58

    def test_fuzzy_title_match(self, sample_kaggle_df: pd.DataFrame) -> None:
        song = {"title": "Viva la Vida", "artist": "Coldplay"}
        result = fuzzy_match_kaggle(song, sample_kaggle_df)
        assert result is not None
        assert result["track_name"] == "Viva La Vida"

    def test_no_match_below_threshold(
        self, sample_kaggle_df: pd.DataFrame
    ) -> None:
        song = {"title": "Completely Unknown Song", "artist": "Nobody"}
        result = fuzzy_match_kaggle(song, sample_kaggle_df, threshold=70)
        assert result is None

    def test_match_without_artist(self, sample_kaggle_df: pd.DataFrame) -> None:
        song = {"title": "Hey Jude", "artist": ""}
        result = fuzzy_match_kaggle(song, sample_kaggle_df)
        assert result is not None
        assert result["track_name"] == "Hey Jude"

    def test_returns_audio_features(
        self, sample_kaggle_df: pd.DataFrame
    ) -> None:
        song = {"title": "Thriller", "artist": "Michael Jackson"}
        result = fuzzy_match_kaggle(song, sample_kaggle_df)
        assert result is not None
        expected_keys = {
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
            "match_score",
        }
        assert expected_keys.issubset(set(result.keys()))

    def test_threshold_parameter(self, sample_kaggle_df: pd.DataFrame) -> None:
        """With a very high threshold, fuzzy matches should fail."""
        song = {"title": "Bohemien Rapsody", "artist": "Queen"}
        result_low = fuzzy_match_kaggle(song, sample_kaggle_df, threshold=50)
        result_high = fuzzy_match_kaggle(song, sample_kaggle_df, threshold=99)
        assert result_low is not None
        assert result_high is None

    def test_artist_boosts_correct_match(
        self, sample_kaggle_df: pd.DataFrame
    ) -> None:
        """When artist is provided, it should help disambiguate."""
        song = {"title": "Jolene", "artist": "Dolly Parton"}
        result = fuzzy_match_kaggle(song, sample_kaggle_df)
        assert result is not None
        assert result["artist_name"] == "Dolly Parton"
