"""
Color Palette Assignment: Genre DNA of a Medley
Produces two versions of the stacked area chart:
  1. Color-blind friendly (digital viewing)
  2. Greyscale (print-friendly)
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from pathlib import Path

# ---------------------------------------------------------------------------
# Data prep
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
sp = pd.read_csv(ROOT / "data" / "spotify_features.csv")
sp = sp[sp["year"] >= 2022].copy()

# Explode genres
genre_rows = []
for _, row in sp.dropna(subset=["kaggle_genre"]).iterrows():
    for g in str(row["kaggle_genre"]).split(";"):
        g = g.strip()
        if g:
            genre_rows.append({"year": int(row["year"]), "genre": g})
gdf = pd.DataFrame(genre_rows)

# Top 10 genres
top10 = gdf["genre"].value_counts().head(10).index.tolist()
gdf = gdf[gdf["genre"].isin(top10)]

# Pivot: year x genre proportions
pivot = gdf.groupby(["year", "genre"]).size().unstack(fill_value=0)
pivot = pivot.div(pivot.sum(axis=1), axis=0)
# Ensure consistent column order (most common first)
pivot = pivot[top10]

years = pivot.index.values

# ---------------------------------------------------------------------------
# Palette 1: Color-blind friendly (Okabe-Ito + adapted)
#
# Based on the Okabe-Ito palette, which was specifically designed for
# universal color-blind accessibility. Extended to 10 colors by adding
# carefully tested variants that maintain distinguishability under all
# three common forms of color vision deficiency (protanopia, deuteranopia,
# tritanopia).
#
# This is a NOMINAL (categorical/qualitative) palette — each color
# represents a distinct music genre with no inherent ordering.
# ---------------------------------------------------------------------------
# Okabe-Ito core (8 colors) + 2 extensions
okabe_ito_10 = [
    "#E69F00",  # orange        — pop
    "#56B4E9",  # sky blue      — dance
    "#009E73",  # bluish green  — disco
    "#F0E442",  # yellow        — country
    "#0072B2",  # blue          — blues
    "#D55E00",  # vermillion    — funk
    "#CC79A7",  # reddish purple— rock
    "#999999",  # grey          — hard-rock
    "#882255",  # wine          — alt-rock
    "#44AA99",  # teal          — rock-n-roll
]

# ---------------------------------------------------------------------------
# Palette 2: Greyscale (print-friendly)
#
# Uses evenly-spaced luminance values from dark to light, plus hatching
# patterns to further differentiate adjacent areas in the stack.
# This ensures each genre remains distinguishable on a B&W printer.
# ---------------------------------------------------------------------------
grey_10 = [
    "#1a1a1a",  # near-black   — pop
    "#e0e0e0",  # very light   — dance
    "#4d4d4d",  # dark grey    — disco
    "#b3b3b3",  # light grey   — country
    "#333333",  # charcoal     — blues
    "#cccccc",  # silver       — funk
    "#666666",  # medium dark  — rock
    "#f2f2f2",  # near-white   — hard-rock
    "#808080",  # medium       — alt-rock
    "#999999",  # medium light — rock-n-roll
]

# Hatching patterns for greyscale differentiation
hatch_patterns = [
    "",      # pop        — solid
    "///",   # dance      — diagonal
    "...",   # disco      — dots
    "\\\\\\",  # country — backslash
    "xxx",   # blues      — cross
    "---",   # funk       — horizontal
    "|||",   # rock       — vertical
    "ooo",   # hard-rock  — circles
    "++",    # alt-rock   — plus
    "OO",    # rock-n-roll— big circles
]


def make_stacked_area(ax, pivot, colors, title, hatches=None, dark_bg=True):
    """Draw a stacked area chart on the given axes."""
    y_stack = np.vstack([pivot[col].values for col in pivot.columns])
    y_cumsum = np.cumsum(y_stack, axis=0)

    for i, col in enumerate(pivot.columns):
        bottom = y_cumsum[i - 1] if i > 0 else np.zeros(len(years))
        top = y_cumsum[i]

        ax.fill_between(
            years, bottom, top,
            color=colors[i],
            label=col.replace("-", " ").title(),
            hatch=hatches[i] if hatches else None,
            edgecolor="#333" if dark_bg else "#aaa",
            linewidth=0.5,
        )

    ax.set_xlim(years[0], years[-1])
    ax.set_ylim(0, 1)
    ax.set_xlabel("Year", fontsize=12)
    ax.set_ylabel("Proportion of Genre Tags", fontsize=12)
    ax.set_title(title, fontsize=16, fontweight="bold", pad=15)
    ax.xaxis.set_major_locator(mticker.FixedLocator(years))
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))

    # Legend outside
    ax.legend(
        loc="upper left", bbox_to_anchor=(1.02, 1),
        fontsize=9, framealpha=0.9,
        title="Genre", title_fontsize=10,
    )


# ---------------------------------------------------------------------------
# Figure 1: Color-blind friendly (digital)
# ---------------------------------------------------------------------------
fig1, ax1 = plt.subplots(figsize=(12, 6))
fig1.patch.set_facecolor("#0a0a0f")
ax1.set_facecolor("#0a0a0f")

make_stacked_area(ax1, pivot, okabe_ito_10,
                  "Genre DNA of a Sing Medley (2022-2026)",
                  dark_bg=True)

# Style for dark background
ax1.tick_params(colors="#aaa")
ax1.xaxis.label.set_color("#aaa")
ax1.yaxis.label.set_color("#aaa")
ax1.title.set_color("#eee")
for spine in ax1.spines.values():
    spine.set_color("#333")
ax1.legend(
    loc="upper left", bbox_to_anchor=(1.02, 1),
    fontsize=9, facecolor="#111118", edgecolor="#333",
    labelcolor="#ccc", title="Genre", title_fontsize=10,
)
ax1.legend_.get_title().set_color("#eee")

fig1.tight_layout()
out1 = ROOT / "genre_dna_colorblind_friendly.png"
fig1.savefig(out1, dpi=200, bbox_inches="tight", facecolor=fig1.get_facecolor())
print(f"Saved: {out1}")

# ---------------------------------------------------------------------------
# Figure 2: Greyscale (print-friendly)
# ---------------------------------------------------------------------------
fig2, ax2 = plt.subplots(figsize=(12, 6))
fig2.patch.set_facecolor("white")
ax2.set_facecolor("white")

make_stacked_area(ax2, pivot, grey_10,
                  "Genre DNA of a Sing Medley (2022-2026)",
                  hatches=hatch_patterns, dark_bg=False)

# Style for light background
ax2.tick_params(colors="#333")
ax2.xaxis.label.set_color("#333")
ax2.yaxis.label.set_color("#333")
ax2.title.set_color("#111")
for spine in ax2.spines.values():
    spine.set_color("#ccc")

fig2.tight_layout()
out2 = ROOT / "genre_dna_greyscale.png"
fig2.savefig(out2, dpi=200, bbox_inches="tight", facecolor="white")
print(f"Saved: {out2}")

plt.close("all")
print("\nDone! Two versions generated.")
