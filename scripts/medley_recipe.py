"""
Medley Recipe: Per-act genre composition strips.
Each act is a horizontal bar divided by genre proportion.
Produces:
  1. Color-blind friendly version (digital)
  2. Greyscale version (print)
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sp = pd.read_csv(ROOT / "data" / "spotify_features.csv")
sp = sp[sp["year"] >= 2022].copy()

# Explode genres per song
rows = []
for _, r in sp.dropna(subset=["kaggle_genre"]).iterrows():
    for g in str(r["kaggle_genre"]).split(";"):
        g = g.strip()
        if g:
            rows.append({
                "year": int(r["year"]),
                "group": r["group"],
                "genre": g,
            })
gdf = pd.DataFrame(rows)

# Top 10 genres
top10 = gdf["genre"].value_counts().head(10).index.tolist()
gdf["genre_clean"] = gdf["genre"].where(gdf["genre"].isin(top10), "other")

# Compute proportions per act
act_genre = gdf.groupby(["year", "group", "genre_clean"]).size().reset_index(name="count")
act_totals = act_genre.groupby(["year", "group"])["count"].transform("sum")
act_genre["prop"] = act_genre["count"] / act_totals

# Pivot to wide format
pivot = act_genre.pivot_table(
    index=["year", "group"], columns="genre_clean", values="prop", fill_value=0
).reset_index()

# Sort by year then group
pivot = pivot.sort_values(["year", "group"], ascending=[True, True]).reset_index(drop=True)

# Get all genre columns (excluding year, group)
genre_cols = [c for c in pivot.columns if c not in ("year", "group")]
# Reorder: top10 first, then "other" at the end
ordered_genres = [g for g in top10 if g in genre_cols]
if "other" in genre_cols:
    ordered_genres.append("other")
genre_cols = ordered_genres

# Act labels
act_labels = [f"{int(row.year)} {row.group}" for _, row in pivot.iterrows()]

# ---------------------------------------------------------------------------
# Okabe-Ito palette (same as genre stream for consistency) + grey for "other"
# ---------------------------------------------------------------------------
okabe_ito = {
    "pop": "#E69F00",
    "dance": "#56B4E9",
    "disco": "#009E73",
    "country": "#F0E442",
    "blues": "#0072B2",
    "funk": "#D55E00",
    "rock": "#CC79A7",
    "hard-rock": "#999999",
    "alt-rock": "#882255",
    "rock-n-roll": "#44AA99",
    "other": "#444444",
}

grey_palette = {
    "pop": "#1a1a1a",
    "dance": "#e0e0e0",
    "disco": "#4d4d4d",
    "country": "#b3b3b3",
    "blues": "#333333",
    "funk": "#cccccc",
    "rock": "#666666",
    "hard-rock": "#f2f2f2",
    "alt-rock": "#808080",
    "rock-n-roll": "#999999",
    "other": "#444444",
}

hatch_map = {
    "pop": "",
    "dance": "///",
    "disco": "...",
    "country": "\\\\\\",
    "blues": "xxx",
    "funk": "---",
    "rock": "|||",
    "hard-rock": "ooo",
    "alt-rock": "++",
    "rock-n-roll": "OO",
    "other": "**",
}


def draw_recipe(ax, pivot, genre_cols, palette, title, dark=True, hatches=None):
    """Draw horizontal stacked bars for each act."""
    n_acts = len(pivot)
    y_positions = np.arange(n_acts)

    for i, genre in enumerate(genre_cols):
        if genre not in pivot.columns:
            continue
        lefts = pivot[genre_cols[:i]].sum(axis=1).values if i > 0 else np.zeros(n_acts)
        widths = pivot[genre].values

        ax.barh(
            y_positions, widths, left=lefts, height=0.8,
            color=palette.get(genre, "#444"),
            edgecolor="#222" if dark else "#ccc",
            linewidth=0.3,
            hatch=hatches.get(genre, "") if hatches else None,
            label=genre.replace("-", " ").title() if i < 15 else None,
        )

    ax.set_yticks(y_positions)
    ax.set_yticklabels(act_labels, fontsize=6)
    ax.set_xlim(0, 1)
    ax.set_xlabel("Genre Proportion", fontsize=11)
    ax.set_title(title, fontsize=15, fontweight="bold", pad=12)
    ax.invert_yaxis()

    # Legend
    ax.legend(
        loc="upper left", bbox_to_anchor=(1.02, 1),
        fontsize=8, title="Genre", title_fontsize=9,
        framealpha=0.9,
    )


# ---------------------------------------------------------------------------
# Figure 1: Color-blind friendly (digital)
# ---------------------------------------------------------------------------
fig1, ax1 = plt.subplots(figsize=(14, max(8, len(pivot) * 0.22)))
fig1.patch.set_facecolor("#0a0a0f")
ax1.set_facecolor("#0a0a0f")

draw_recipe(ax1, pivot, genre_cols, okabe_ito,
            "Medley Recipe: Genre Composition per Act (2022-2026)", dark=True)

ax1.tick_params(colors="#aaa")
ax1.xaxis.label.set_color("#aaa")
ax1.title.set_color("#eee")
for spine in ax1.spines.values():
    spine.set_color("#333")
ax1.legend(
    loc="upper left", bbox_to_anchor=(1.02, 1),
    fontsize=8, facecolor="#111118", edgecolor="#333",
    labelcolor="#ccc", title="Genre", title_fontsize=9,
)
ax1.legend_.get_title().set_color("#eee")

fig1.tight_layout()
out1 = ROOT / "medley_recipe_colorblind.png"
fig1.savefig(out1, dpi=200, bbox_inches="tight", facecolor=fig1.get_facecolor())
print(f"Saved: {out1}")


# ---------------------------------------------------------------------------
# Figure 2: Greyscale (print)
# ---------------------------------------------------------------------------
fig2, ax2 = plt.subplots(figsize=(14, max(8, len(pivot) * 0.22)))
fig2.patch.set_facecolor("white")
ax2.set_facecolor("white")

draw_recipe(ax2, pivot, genre_cols, grey_palette,
            "Medley Recipe: Genre Composition per Act (2022-2026)",
            dark=False, hatches=hatch_map)

ax2.tick_params(colors="#333")
ax2.xaxis.label.set_color("#333")
ax2.title.set_color("#111")
for spine in ax2.spines.values():
    spine.set_color("#ccc")

fig2.tight_layout()
out2 = ROOT / "medley_recipe_greyscale.png"
fig2.savefig(out2, dpi=200, bbox_inches="tight", facecolor="white")
print(f"Saved: {out2}")

plt.close("all")
print("\nDone!")
