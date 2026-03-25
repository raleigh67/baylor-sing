import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter
import re

df = pd.read_csv('/Users/raleightognela/Documents/sing_data/baylor-sing-all-acts-final.csv')

def count_songs(s):
    if pd.isna(s) or s.strip() == '':
        return 0
    return len(s.split(';'))

df['SongCount'] = df['Songs'].apply(count_songs)

plt.style.use('seaborn-v0_8-whitegrid')
fig_size = (12, 7)

# Only use 2022-2025 for song-based plots
song_years = df[(df['Year'] >= 2022) & (df['Year'] <= 2025)].copy()

# ============================================================
# PLOT 5: Histogram — "How Many Songs Do Acts Typically Perform in Their Medley?"
# Filtered to 2022-2025 only
# ============================================================
fig, ax = plt.subplots(figsize=fig_size)
songs_data = song_years[song_years['SongCount'] > 0]['SongCount']
ax.hist(songs_data, bins=range(songs_data.min(), songs_data.max() + 2), color='#7570b3',
        edgecolor='white', alpha=0.85, align='left')
ax.axvline(songs_data.mean(), color='red', linestyle='--', linewidth=2,
           label=f'Mean: {songs_data.mean():.1f} songs')
ax.axvline(songs_data.median(), color='orange', linestyle='--', linewidth=2,
           label=f'Median: {songs_data.median():.0f} songs')
ax.set_xlabel('Number of Songs in Medley', fontsize=12)
ax.set_ylabel('Number of Acts', fontsize=12)
ax.set_title('How Many Songs Do Acts Typically Perform in Their Medley? (2022-2025)',
             fontsize=14, fontweight='bold')
ax.legend(fontsize=11)
ax.xaxis.set_major_locator(plt.MultipleLocator(1))
plt.tight_layout()
plt.savefig('/Users/raleightognela/Documents/sing_data/plot_05_song_count_distribution.png', dpi=150)
plt.close()
print("Plot 5 updated: plot_05_song_count_distribution.png")

# ============================================================
# PLOT 7: Bar Chart — "Which Musical Artists Are Most Frequently Covered at Baylor Sing?"
# Filtered to 2022-2025 only
# ============================================================
fig, ax = plt.subplots(figsize=fig_size)
all_artists = []
for songs in song_years['Songs'].dropna():
    matches = re.findall(r'\(([^)]+)\)', songs)
    for m in matches:
        artist = m.strip()
        all_artists.append(artist)

# Clean up / normalize artist names
artist_counts = Counter(all_artists)
top_artists = pd.DataFrame(artist_counts.most_common(15), columns=['Artist', 'Count'])
colors = plt.cm.plasma(np.linspace(0.2, 0.85, len(top_artists)))
bars = ax.barh(top_artists['Artist'][::-1], top_artists['Count'][::-1], color=colors)
ax.set_xlabel('Number of Times Covered', fontsize=12)
ax.set_title('Which Musical Artists Are Most Frequently Covered at Baylor Sing? (2022-2025)',
             fontsize=14, fontweight='bold')
for bar, val in zip(bars, top_artists['Count'][::-1]):
    ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2, str(val),
            va='center', fontsize=10, fontweight='bold')
ax.set_xlim(0, top_artists['Count'].max() + 1.5)
plt.tight_layout()
plt.savefig('/Users/raleightognela/Documents/sing_data/plot_07_top_artists_covered.png', dpi=150)
plt.close()
print("Plot 7 updated: plot_07_top_artists_covered.png")
