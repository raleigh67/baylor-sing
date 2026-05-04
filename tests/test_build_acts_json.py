import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "07_build_acts_json.py"
OUT = ROOT / "site" / "data" / "acts.json"


def test_build_produces_expected_shape():
    result = subprocess.run([sys.executable, str(SCRIPT)],
                            capture_output=True, text=True, cwd=str(ROOT))
    assert result.returncode == 0, f"build failed: {result.stderr}"
    assert OUT.exists()

    data = json.loads(OUT.read_text())
    assert isinstance(data, list)
    assert 60 < len(data) < 80, f"expected 60-80 acts, got {len(data)}"

    required = {
        "year", "group", "theme", "placement", "songs",
        "valence", "energy", "danceability", "tempo", "popularity",
        "genres", "song_count",
        "palette", "props", "dominant",
        "avg_hue", "avg_sat", "avg_val",
        "palette_source", "n_images",
    }
    for a in data:
        missing = required - set(a.keys())
        assert not missing, f"act {a.get('group')} missing fields: {missing}"

    assert all(2022 <= a["year"] <= 2025 for a in data)
    for a in data:
        assert a["dominant"] in a["palette"], \
            f"{a['year']} {a['group']}: dominant {a['dominant']} not in palette"
    assert all(a["palette_source"] in ("youtube", "bing") for a in data)


def test_dominant_picks_most_vivid_in_top6():
    import colorsys
    data = json.loads(OUT.read_text())
    for a in data:
        candidates = list(zip(a["palette"][:6], a["props"][:6]))
        scores = []
        for h, p in candidates:
            r = int(h[1:3], 16) / 255
            g = int(h[3:5], 16) / 255
            b = int(h[5:7], 16) / 255
            _, s, v = colorsys.rgb_to_hsv(r, g, b)
            scores.append((s * v * (1 + 0.3 * p), h))
        expected = max(scores)[1]
        assert a["dominant"] == expected, \
            f"{a['year']} {a['group']}: dominant {a['dominant']}, expected {expected}"
