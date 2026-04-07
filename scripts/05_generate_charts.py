"""
05_generate_charts.py

Generates Plotly JSON chart specs from the enriched Sing dataset.
Output goes to site/charts/ for use by the scrollytelling front end.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CHARTS_DIR = ROOT / "site" / "charts"
ENRICHED_CSV = DATA_DIR / "sing_enriched.csv"
SPOTIFY_CSV = DATA_DIR / "spotify_features.csv"

CHARTS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Dark theme defaults
# ---------------------------------------------------------------------------
DARK_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="#0a0a0f",
    plot_bgcolor="#0a0a0f",
    font=dict(color="#aaa"),
    title_font=dict(size=20, color="#eee"),
    margin=dict(l=60, r=40, t=60, b=60),
)


def _strip_bdata(obj):
    """Recursively convert Plotly bdata dicts to plain lists."""
    import base64, struct
    if isinstance(obj, dict):
        if "bdata" in obj and "dtype" in obj:
            dtype = obj["dtype"]
            raw = base64.b64decode(obj["bdata"])
            fmt = {"f8": "d", "f4": "f", "i4": "i", "i2": "h", "u1": "B", "i1": "b"}
            c = fmt.get(dtype, "d")
            n = len(raw) // struct.calcsize(c)
            return list(struct.unpack(f"<{n}{c}", raw))
        return {k: _strip_bdata(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_strip_bdata(item) for item in obj]
    return obj


def save_chart(fig: go.Figure, name: str) -> None:
    """Write a Plotly figure to JSON with plain arrays (no base64 bdata)."""
    import json as _json
    path = CHARTS_DIR / name
    spec = json.loads(fig.to_json())
    spec = _strip_bdata(spec)
    path.write_text(_json.dumps(spec, default=str))
    print(f"  -> {path}")


# ===================================================================
# SOUND SECTION
# ===================================================================


def _is_winner(placement: str) -> bool:
    """Return True if the placement string means 1st place."""
    if pd.isna(placement):
        return False
    p = str(placement).strip().lower()
    return p in ("1st", "1st (tie)")


def sound1_violin(df: pd.DataFrame, col: str, filename: str, title: str) -> None:
    """Violin plot: winners vs. field for a given audio feature."""
    subset = df.dropna(subset=[col])
    if len(subset) < 10:
        print(f"  SKIP {filename}: not enough data for {col}")
        return

    subset = subset.copy()
    subset["is_winner"] = subset["Placement"].apply(_is_winner)

    winners = subset.loc[subset["is_winner"], col]
    field = subset.loc[~subset["is_winner"], col]

    fig = go.Figure()
    fig.add_trace(go.Violin(
        y=field,
        name="Field",
        side="negative",
        line_color="#555",
        fillcolor="rgba(85,85,85,0.4)",
        meanline_visible=True,
        points="all",
        jitter=0.05,
        pointpos=-0.6,
        marker=dict(size=3, color="#555"),
    ))
    fig.add_trace(go.Violin(
        y=winners,
        name="Winners (1st)",
        side="positive",
        line_color="#e94560",
        fillcolor="rgba(233,69,96,0.4)",
        meanline_visible=True,
        points="all",
        jitter=0.05,
        pointpos=0.6,
        marker=dict(size=3, color="#e94560"),
    ))
    fig.update_layout(
        title=title,
        yaxis_title=col.capitalize(),
        violinmode="overlay",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        **DARK_LAYOUT,
    )
    save_chart(fig, filename)


def sound2_top_artists(sp: pd.DataFrame) -> None:
    """Horizontal bar chart of top 20 most covered artists."""
    # Prefer song_artist (original), fall back to kaggle_artist_name
    artists = sp["song_artist"].fillna(sp["kaggle_artist_name"])
    artists = artists.dropna()
    if len(artists) < 5:
        print("  SKIP sound2_top_artists.json: not enough artist data")
        return

    counts = artists.value_counts().head(20).sort_values()

    fig = go.Figure(go.Bar(
        x=counts.values,
        y=counts.index,
        orientation="h",
        marker_color="#e94560",
    ))
    fig.update_layout(
        title="Top 20 Most Covered Artists",
        xaxis_title="Number of Performances",
        yaxis_title="",
        **DARK_LAYOUT,
    )
    # Extra bottom margin for long names
    fig.update_layout(margin=dict(l=160, r=40, t=60, b=60))
    save_chart(fig, "sound2_top_artists.json")


def sound2_song_age(sp: pd.DataFrame) -> None:
    """Histogram of (performance year - song release year)."""
    subset = sp.dropna(subset=["year", "kaggle_year"]).copy()
    if len(subset) < 10:
        print("  SKIP sound2_song_age.json: not enough year data")
        return

    subset["age"] = subset["year"] - subset["kaggle_year"]

    fig = go.Figure(go.Histogram(
        x=subset["age"],
        nbinsx=40,
        marker_color="#e94560",
        opacity=0.85,
    ))
    fig.update_layout(
        title="Song Age at Performance",
        xaxis_title="Years Since Release",
        yaxis_title="Count",
        **DARK_LAYOUT,
    )
    save_chart(fig, "sound2_song_age.json")


def sound3_genre_stream(sp: pd.DataFrame) -> None:
    """Stacked area chart of top 10 genres over time."""
    subset = sp.dropna(subset=["kaggle_genre", "year"]).copy()
    if len(subset) < 10:
        print("  SKIP sound3_genre_stream.json: not enough genre data")
        return

    # Explode semicolon-separated genres
    genre_rows = []
    for _, row in subset.iterrows():
        for g in str(row["kaggle_genre"]).split(";"):
            g = g.strip()
            if g:
                genre_rows.append({"year": int(row["year"]), "genre": g})
    gdf = pd.DataFrame(genre_rows)

    # Find top 10 genres overall
    top10 = gdf["genre"].value_counts().head(10).index.tolist()
    gdf = gdf[gdf["genre"].isin(top10)]

    # Pivot: year x genre counts, then normalize to proportions per year
    pivot = gdf.groupby(["year", "genre"]).size().unstack(fill_value=0)
    pivot = pivot.div(pivot.sum(axis=1), axis=0)

    colors = [
        "#e94560", "#0f3460", "#16213e", "#53d8fb", "#f0c27f",
        "#4b7bec", "#a55eea", "#26de81", "#fd9644", "#fc5c65",
    ]

    fig = go.Figure()
    for i, genre in enumerate(top10):
        if genre not in pivot.columns:
            continue
        fig.add_trace(go.Scatter(
            x=pivot.index,
            y=pivot[genre],
            name=genre,
            mode="lines",
            stackgroup="one",
            line=dict(width=0.5, color=colors[i % len(colors)]),
        ))

    fig.update_layout(
        title="Genre Proportions Over Time (Top 10)",
        xaxis_title="Year",
        yaxis_title="Proportion",
        yaxis=dict(range=[0, 1]),
        **DARK_LAYOUT,
    )
    save_chart(fig, "sound3_genre_stream.json")


# ===================================================================
# COLOR SECTION
# ===================================================================


def _is_top3(placement: str) -> bool:
    """Return True if placement is top 3."""
    if pd.isna(placement):
        return False
    p = str(placement).strip().lower()
    return p in ("1st", "1st (tie)", "2nd", "3rd", "3rd (tie)")


def color1_brightness_scatter(df: pd.DataFrame) -> None:
    """Scatter: avg_saturation vs avg_brightness, colored by top-3."""
    subset = df.dropna(subset=["avg_saturation", "avg_brightness"]).copy()
    if len(subset) < 5:
        print("  SKIP color1_brightness_scatter.json: not enough color data")
        return

    subset["top3"] = subset["Placement"].apply(_is_top3)

    top = subset[subset["top3"]]
    rest = subset[~subset["top3"]]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=rest["avg_saturation"],
        y=rest["avg_brightness"],
        mode="markers",
        name="Other",
        marker=dict(color="#555", size=6, opacity=0.6),
        customdata=rest[["Year", "Group", "Placement"]].values,
        hovertemplate=(
            "<b>%{customdata[1]}</b> (%{customdata[0]})<br>"
            "Placement: %{customdata[2]}<br>"
            "Saturation: %{x:.2f}<br>"
            "Brightness: %{y:.2f}<extra></extra>"
        ),
    ))
    fig.add_trace(go.Scatter(
        x=top["avg_saturation"],
        y=top["avg_brightness"],
        mode="markers",
        name="Top 3",
        marker=dict(color="#e94560", size=8, opacity=0.9),
        customdata=top[["Year", "Group", "Placement"]].values,
        hovertemplate=(
            "<b>%{customdata[1]}</b> (%{customdata[0]})<br>"
            "Placement: %{customdata[2]}<br>"
            "Saturation: %{x:.2f}<br>"
            "Brightness: %{y:.2f}<extra></extra>"
        ),
    ))

    fig.update_layout(
        title="Costume Color: Saturation vs Brightness",
        xaxis_title="Average Saturation",
        yaxis_title="Average Brightness",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        **DARK_LAYOUT,
    )
    save_chart(fig, "color1_brightness_scatter.json")


def color2_correlation(df: pd.DataFrame) -> None:
    """Heatmap: correlation between audio and color features."""
    audio_cols = ["energy", "valence", "danceability"]
    color_cols = ["avg_brightness", "avg_saturation", "avg_hue"]
    all_cols = audio_cols + color_cols

    subset = df.dropna(subset=all_cols)
    if len(subset) < 5:
        print("  SKIP color2_correlation.json: not enough combined data")
        return

    corr = subset[all_cols].corr()

    fig = go.Figure(go.Heatmap(
        z=corr.values,
        x=corr.columns.tolist(),
        y=corr.index.tolist(),
        colorscale="RdBu_r",
        zmid=0,
        text=np.round(corr.values, 2),
        texttemplate="%{text}",
        textfont=dict(size=12),
    ))
    fig.update_layout(
        title="Audio vs Color Feature Correlations",
        xaxis=dict(tickangle=-45),
        **DARK_LAYOUT,
    )
    save_chart(fig, "color2_correlation.json")


# ===================================================================
# APPENDIX
# ===================================================================


def appendix_completeness(df: pd.DataFrame) -> None:
    """Heatmap: data completeness by year and field."""
    fields = ["Theme", "Songs", "YouTube_Link", "energy", "palette_hex"]
    present = [f for f in fields if f in df.columns]
    if not present:
        print("  SKIP appendix_completeness.json: none of the expected fields exist")
        return

    years = sorted(df["Year"].unique())
    matrix = []
    for field in present:
        row = []
        for yr in years:
            yr_data = df[df["Year"] == yr]
            total = len(yr_data)
            if total == 0:
                row.append(0.0)
            else:
                non_null = yr_data[field].notna().sum()
                row.append(non_null / total)
        matrix.append(row)

    fig = go.Figure(go.Heatmap(
        z=matrix,
        x=[str(y) for y in years],
        y=present,
        colorscale="Viridis",
        zmin=0,
        zmax=1,
        text=np.round(matrix, 2),
        texttemplate="%{text}",
        textfont=dict(size=10),
    ))
    fig.update_layout(
        title="Data Completeness by Year",
        xaxis_title="Year",
        xaxis=dict(tickangle=-45, dtick=5),
        **DARK_LAYOUT,
    )
    save_chart(fig, "appendix_completeness.json")


# ===================================================================
# DASHBOARD
# ===================================================================


def dashboard_data(df: pd.DataFrame) -> None:
    """Export full enriched dataset as JSON array for the dashboard explorer."""
    cols = [
        "Year", "Group", "Theme", "Placement", "Songs",
        "palette_hex", "avg_brightness", "avg_saturation",
        "energy", "valence", "danceability", "tempo", "genres",
    ]
    present = [c for c in cols if c in df.columns]
    out = df[present].copy()

    # Replace NaN with empty string
    out = out.fillna("")

    path = CHARTS_DIR / "dashboard_data.json"
    path.write_text(json.dumps(out.to_dict(orient="records"), default=str))
    print(f"  -> {path}")


# ===================================================================
# MAIN
# ===================================================================


MIN_YEAR = 2022  # Only use data from 2022+ where coverage is comprehensive


def main() -> None:
    print("Loading enriched dataset...")
    df_all = pd.read_csv(ENRICHED_CSV)
    print(f"  {len(df_all)} rows total")

    # Filter to 2022+ for all charts except appendix
    df = df_all[df_all["Year"] >= MIN_YEAR].copy()
    print(f"  {len(df)} rows after filtering to {MIN_YEAR}+")

    print("Loading spotify features...")
    sp_all = pd.read_csv(SPOTIFY_CSV)
    sp = sp_all[sp_all["year"] >= MIN_YEAR].copy()
    print(f"  {len(sp)} rows after filtering to {MIN_YEAR}+")

    print("\n--- Sound Section ---")
    sound1_violin(df, "energy", "sound1_energy.json", "Energy: Winners vs Field")
    sound1_violin(df, "valence", "sound1_valence.json", "Valence: Winners vs Field")
    sound1_violin(df, "danceability", "sound1_danceability.json", "Danceability: Winners vs Field")
    sound2_top_artists(sp)
    sound2_song_age(sp)
    sound3_genre_stream(sp)

    print("\n--- Color Section ---")
    color1_brightness_scatter(df)
    color2_correlation(df)

    print("\n--- Appendix ---")
    appendix_completeness(df_all)  # use ALL years to show full data story

    print("\n--- Dashboard ---")
    dashboard_data(df)

    print("\nDone!")


if __name__ == "__main__":
    main()
