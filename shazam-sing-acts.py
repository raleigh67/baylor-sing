#!/usr/bin/env python3
"""
Shazam audio fingerprinting for Baylor Sing YouTube videos.
Downloads audio from YouTube, splits into segments, and identifies songs via Shazam.
"""

import asyncio
import csv
import json
import os
import sys
import tempfile
from pathlib import Path

import yt_dlp
from pydub import AudioSegment
from shazamio import Shazam

# Configuration
SEGMENT_DURATION_MS = 20_000  # 20 seconds per segment
OVERLAP_MS = 5_000  # 5 second overlap between segments
OUTPUT_DIR = Path("shazam_results")
AUDIO_DIR = Path("audio_downloads")


def download_audio(youtube_url: str, output_path: str) -> str | None:
    """Download audio from YouTube video as MP3."""
    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "outtmpl": output_path,
        "quiet": True,
        "no_warnings": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
        # yt-dlp adds the extension
        mp3_path = output_path + ".mp3"
        if os.path.exists(mp3_path):
            return mp3_path
        # Sometimes it doesn't add extension if already present
        if os.path.exists(output_path):
            return output_path
        return None
    except Exception as e:
        print(f"  ERROR downloading {youtube_url}: {e}")
        return None


def split_audio(audio_path: str, segment_ms: int = SEGMENT_DURATION_MS, overlap_ms: int = OVERLAP_MS) -> list[str]:
    """Split audio file into overlapping segments for better Shazam detection."""
    audio = AudioSegment.from_mp3(audio_path)
    segments = []
    step = segment_ms - overlap_ms

    for i, start in enumerate(range(0, len(audio), step)):
        end = min(start + segment_ms, len(audio))
        if end - start < 5000:  # Skip segments shorter than 5 seconds
            break
        segment = audio[start:end]
        seg_path = audio_path.replace(".mp3", f"_seg{i:03d}.mp3")
        segment.export(seg_path, format="mp3")
        segments.append(seg_path)

    return segments


async def shazam_segment(shazam: Shazam, segment_path: str) -> dict | None:
    """Run Shazam on a single audio segment."""
    try:
        result = await shazam.recognize(segment_path)
        if result and "track" in result:
            track = result["track"]
            return {
                "title": track.get("title", "Unknown"),
                "artist": track.get("subtitle", "Unknown"),
                "key": track.get("key", ""),
            }
    except Exception as e:
        # Silently skip failed segments
        pass
    return None


async def identify_songs(audio_path: str) -> list[dict]:
    """Split audio and run Shazam on each segment, deduplicating results."""
    shazam = Shazam()
    segments = split_audio(audio_path)
    print(f"  Split into {len(segments)} segments")

    songs = []
    seen_keys = set()
    seen_titles = set()

    for i, seg_path in enumerate(segments):
        result = await shazam_segment(shazam, seg_path)
        if result:
            # Deduplicate by Shazam key or title
            title_lower = result["title"].lower()
            if result["key"] not in seen_keys and title_lower not in seen_titles:
                seen_keys.add(result["key"])
                seen_titles.add(title_lower)
                songs.append(result)
                print(f"    Segment {i}: {result['title']} - {result['artist']}")

        # Clean up segment file
        try:
            os.remove(seg_path)
        except OSError:
            pass

    return songs


def read_csv(csv_path: str) -> list[dict]:
    """Read the Baylor Sing CSV."""
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


async def process_all(csv_path: str):
    """Process all YouTube links in the CSV."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    AUDIO_DIR.mkdir(exist_ok=True)

    rows = read_csv(csv_path)
    results = {}

    # Load existing results if any
    results_file = OUTPUT_DIR / "shazam_results.json"
    if results_file.exists():
        with open(results_file) as f:
            results = json.load(f)

    for row in rows:
        url = row.get("YouTube_Link", "").strip()
        if not url:
            continue

        year = row.get("Year", "unknown")
        group = row.get("Group", "unknown")
        key = f"{year}_{group}"

        # Skip if already processed
        if key in results:
            print(f"Skipping {key} (already processed)")
            continue

        print(f"\nProcessing: {year} - {group}")
        print(f"  URL: {url}")

        # Download audio
        safe_name = f"{year}_{group.replace(' ', '_').replace('&', 'and')}"
        audio_output = str(AUDIO_DIR / safe_name)
        audio_path = download_audio(url, audio_output)

        if not audio_path:
            print(f"  Failed to download audio")
            results[key] = {"error": "download_failed", "url": url}
            continue

        print(f"  Downloaded: {audio_path}")

        # Identify songs
        songs = await identify_songs(audio_path)

        results[key] = {
            "year": year,
            "group": group,
            "url": url,
            "songs": songs,
            "existing_songs": row.get("Songs", ""),
        }

        # Clean up audio file
        try:
            os.remove(audio_path)
        except OSError:
            pass

        # Save after each video
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"  Found {len(songs)} unique songs")

    # Print summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    for key, data in results.items():
        if "error" in data:
            print(f"  {key}: ERROR - {data['error']}")
        else:
            songs_str = "; ".join(f"{s['title']} ({s['artist']})" for s in data.get("songs", []))
            print(f"  {key}: {songs_str or 'No songs identified'}")

    return results


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "baylor-sing-all-acts (1).csv"
    asyncio.run(process_all(csv_path))
