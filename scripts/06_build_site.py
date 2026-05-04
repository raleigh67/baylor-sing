"""Build script: runs the full pipeline and assembles the site/ directory for deployment."""
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SITE_DIR = BASE_DIR / "site"
ASSETS_DIR = SITE_DIR / "assets"
SWATCH_DIR = BASE_DIR / "data" / "palette_swatches"


def run_step(label: str, cmd: list[str]) -> bool:
    print(f"\n--- {label} ---")
    result = subprocess.run(cmd, cwd=str(BASE_DIR))
    if result.returncode != 0:
        print(f"  FAILED (exit {result.returncode})")
        return False
    return True


def main():
    print("=== Building The Sound & Color of Sing ===\n")

    # Step 1: Copy palette swatches to site assets
    swatch_dest = ASSETS_DIR / "swatches"
    if SWATCH_DIR.exists():
        if swatch_dest.exists():
            shutil.rmtree(swatch_dest)
        swatch_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(SWATCH_DIR, swatch_dest)
        count = len(list(swatch_dest.glob("*.png")))
        print(f"Copied {count} palette swatches to {swatch_dest.relative_to(BASE_DIR)}")
    else:
        print("No palette swatches found — skipping asset copy")

    # Step 2: Regenerate charts
    run_step(
        "Generating chart specs",
        [sys.executable, str(BASE_DIR / "scripts" / "05_generate_charts.py")],
    )

    # Step 3: Verify site completeness
    required = [
        SITE_DIR / "index.html",
        SITE_DIR / "css" / "style.css",
        SITE_DIR / "js" / "scroll.js",
        SITE_DIR / "js" / "dashboard.js",
    ]
    charts = list((SITE_DIR / "charts").glob("*.json"))

    print("\n=== Site Status ===")
    all_ok = True
    for f in required:
        exists = f.exists()
        status = "OK" if exists else "MISSING"
        if not exists:
            all_ok = False
        print(f"  {f.relative_to(SITE_DIR)}: {status}")
    print(f"  charts/: {len(charts)} JSON specs")

    if all_ok:
        print(f"\n  Site is ready!")
        print(f"  Serve locally: python3 scripts/serve_site.py --port 8080")
        print(f"  Then open: http://localhost:8080")
    else:
        print(f"\n  Site has missing files — check above")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
