"""
Color Palette Assignment #2: Song Era Matrix
Heatmap of release decade vs. performance year.
Produces:
  1. Color-blind friendly version (digital) — sequential palette
  2. Greyscale version (print)
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sp = pd.read_csv(ROOT / "data" / "spotify_features.csv")
sp = sp[sp["year"] >= 2022].copy()

# Compute song era (decade of release)
sp = sp.dropna(subset=["kaggle_year"]).copy()
sp["release_decade"] = (sp["kaggle_year"] // 10) * 10
sp["release_decade_label"] = sp["release_decade"].astype(int).astype(str) + "s"
sp["perf_year"] = sp["year"].astype(int)

# Build matrix: performance year x release decade
decades = sorted(sp["release_decade"].unique())
perf_years = sorted(sp["perf_year"].unique())

matrix = np.zeros((len(decades), len(perf_years)))
for i, dec in enumerate(decades):
    for j, yr in enumerate(perf_years):
        matrix[i, j] = len(sp[(sp["release_decade"] == dec) & (sp["perf_year"] == yr)])

decade_labels = [f"{int(d)}s" for d in decades]
year_labels = [str(int(y)) for y in perf_years]

# ---------------------------------------------------------------------------
# Version 1: Color-blind friendly (digital) — Sequential "viridis" palette
#
# Viridis is a perceptually uniform sequential colormap designed to be:
# - Readable by all forms of color blindness
# - Monotonically increasing in luminance (prints well in greyscale too)
# - Perceptually uniform (equal steps in data = equal steps in color)
#
# This is a QUANTITATIVE (sequential) palette — darker = more songs.
# ---------------------------------------------------------------------------
fig1, ax1 = plt.subplots(figsize=(10, 7))
fig1.patch.set_facecolor("#0a0a0f")
ax1.set_facecolor("#0a0a0f")

im1 = ax1.imshow(matrix, cmap="viridis", aspect="auto", origin="lower")

# Annotate cells with counts
for i in range(len(decades)):
    for j in range(len(perf_years)):
        val = int(matrix[i, j])
        if val > 0:
            text_color = "white" if val < matrix.max() * 0.6 else "black"
            ax1.text(j, i, str(val), ha="center", va="center",
                     fontsize=12, fontweight="bold", color=text_color)

ax1.set_xticks(range(len(perf_years)))
ax1.set_xticklabels(year_labels, fontsize=11, color="#aaa")
ax1.set_yticks(range(len(decades)))
ax1.set_yticklabels(decade_labels, fontsize=11, color="#aaa")
ax1.set_xlabel("Sing Performance Year", fontsize=13, color="#aaa")
ax1.set_ylabel("Song Release Decade", fontsize=13, color="#aaa")
ax1.set_title("When Were Sing Songs Originally Released?", fontsize=16,
              fontweight="bold", color="#eee", pad=15)

cbar1 = fig1.colorbar(im1, ax=ax1, shrink=0.8, pad=0.02)
cbar1.set_label("Number of Songs", fontsize=11, color="#aaa")
cbar1.ax.tick_params(colors="#aaa")

ax1.tick_params(colors="#aaa")
for spine in ax1.spines.values():
    spine.set_color("#333")

fig1.tight_layout()
out1 = ROOT / "song_era_matrix_colorblind.png"
fig1.savefig(out1, dpi=200, bbox_inches="tight", facecolor=fig1.get_facecolor())
print(f"Saved: {out1}")


# ---------------------------------------------------------------------------
# Version 2: Greyscale (print) — sequential grey with annotations
# ---------------------------------------------------------------------------
fig2, ax2 = plt.subplots(figsize=(10, 7))
fig2.patch.set_facecolor("white")
ax2.set_facecolor("white")

im2 = ax2.imshow(matrix, cmap="Greys", aspect="auto", origin="lower")

for i in range(len(decades)):
    for j in range(len(perf_years)):
        val = int(matrix[i, j])
        if val > 0:
            text_color = "white" if val > matrix.max() * 0.5 else "black"
            ax2.text(j, i, str(val), ha="center", va="center",
                     fontsize=12, fontweight="bold", color=text_color)

ax2.set_xticks(range(len(perf_years)))
ax2.set_xticklabels(year_labels, fontsize=11, color="#333")
ax2.set_yticks(range(len(decades)))
ax2.set_yticklabels(decade_labels, fontsize=11, color="#333")
ax2.set_xlabel("Sing Performance Year", fontsize=13, color="#333")
ax2.set_ylabel("Song Release Decade", fontsize=13, color="#333")
ax2.set_title("When Were Sing Songs Originally Released?", fontsize=16,
              fontweight="bold", color="#111", pad=15)

cbar2 = fig2.colorbar(im2, ax=ax2, shrink=0.8, pad=0.02)
cbar2.set_label("Number of Songs", fontsize=11, color="#333")
cbar2.ax.tick_params(colors="#333")

for spine in ax2.spines.values():
    spine.set_color("#ccc")

fig2.tight_layout()
out2 = ROOT / "song_era_matrix_greyscale.png"
fig2.savefig(out2, dpi=200, bbox_inches="tight", facecolor="white")
print(f"Saved: {out2}")

plt.close("all")
print("\nDone!")
