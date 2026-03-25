import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter
import re

df = pd.read_csv('/Users/raleightognela/Documents/sing_data/baylor-sing-all-acts-final.csv')

# --- Data prep ---
def categorize_placement(p):
    if pd.isna(p):
        return 'Unknown'
    p = str(p).strip()
    if p.startswith('1st'):
        return '1st Place'
    elif p.startswith('2nd'):
        return '2nd Place'
    elif p.startswith('3rd'):
        return '3rd Place'
    elif 'Pigskin' in p:
        return 'Pigskin'
    elif p == 'Participated':
        return 'Participated'
    else:
        return 'Other'

df['PlacementCategory'] = df['Placement'].apply(categorize_placement)

def count_songs(s):
    if pd.isna(s) or s.strip() == '':
        return 0
    return len(s.split(';'))

df['SongCount'] = df['Songs'].apply(count_songs)

def get_base_groups(group_name):
    parts = re.split(r'\s*&\s*', str(group_name))
    return [p.strip() for p in parts]

plt.style.use('seaborn-v0_8-whitegrid')
fig_size = (12, 7)

# ============================================================
# REPLACEMENT FOR PLOT 2: "Do Groups That Use More Songs Place Higher?"
# Uses 2022-2025 data where song lists are most complete
# Scatter plot with box overlay
# ============================================================
fig, ax = plt.subplots(figsize=fig_size)

# Filter to years with reliable complete song data
song_df = df[(df['Year'] >= 2022) & (df['Year'] <= 2025) & (df['SongCount'] > 0)].copy()

placement_map = {'1st Place': 1, '2nd Place': 2, '3rd Place': 3, 'Pigskin': 4, 'Participated': 5}
song_df['PlacementNum'] = song_df['PlacementCategory'].map(placement_map)
song_df = song_df.dropna(subset=['PlacementNum'])

# Jitter for visibility
np.random.seed(42)
jitter_y = song_df['PlacementNum'] + np.random.uniform(-0.15, 0.15, len(song_df))

# Color by placement
colors_map = {'1st Place': '#FFD700', '2nd Place': '#C0C0C0', '3rd Place': '#CD7F32',
              'Pigskin': '#2ca02c', 'Participated': '#9ecae1'}
colors = [colors_map[p] for p in song_df['PlacementCategory']]

ax.scatter(song_df['SongCount'], jitter_y, c=colors, s=80, alpha=0.7, edgecolors='gray', linewidth=0.5)

# Add mean line per placement
for placement_num in [1, 2, 3, 4, 5]:
    subset = song_df[song_df['PlacementNum'] == placement_num]
    if len(subset) > 0:
        mean_songs = subset['SongCount'].mean()
        ax.plot(mean_songs, placement_num, 'D', color='red', markersize=10, zorder=5)
        ax.annotate(f'avg: {mean_songs:.1f}', xy=(mean_songs, placement_num),
                   xytext=(mean_songs + 0.3, placement_num - 0.25), fontsize=9, color='red', fontweight='bold')

ax.set_yticks([1, 2, 3, 4, 5])
ax.set_yticklabels(['1st Place', '2nd Place', '3rd Place', 'Pigskin', 'Participated'], fontsize=11)
ax.invert_yaxis()
ax.set_xlabel('Number of Songs in Medley', fontsize=12)
ax.set_title('Do Groups That Use More Songs Place Higher? (2022-2025)', fontsize=14, fontweight='bold')

# Add legend manually
from matplotlib.lines import Line2D
legend_elements = [Line2D([0], [0], marker='o', color='w', markerfacecolor=c, markersize=10, label=l)
                   for l, c in colors_map.items()]
legend_elements.append(Line2D([0], [0], marker='D', color='w', markerfacecolor='red', markersize=10, label='Mean'))
ax.legend(handles=legend_elements, loc='lower right', fontsize=10)
plt.tight_layout()
plt.savefig('/Users/raleightognela/Documents/sing_data/plot_02_songs_vs_placement.png', dpi=150)
plt.close()
print("Plot 2 replacement saved: plot_02_songs_vs_placement.png")

# ============================================================
# REPLACEMENT FOR PLOT 6: "Which Groups Have the Best Win Rate Among Frequent Competitors?"
# Only groups with 5+ appearances -- avoids incomplete historical data bias
# ============================================================
fig, ax = plt.subplots(figsize=(13, 7))

# Expand paired acts and count appearances + top-3 finishes
group_stats = {}
for _, row in df.iterrows():
    for g in get_base_groups(row['Group']):
        if g not in group_stats:
            group_stats[g] = {'appearances': 0, 'wins': 0, 'top3': 0, 'pigskin': 0}
        group_stats[g]['appearances'] += 1
        if row['PlacementCategory'] == '1st Place':
            group_stats[g]['wins'] += 1
            group_stats[g]['top3'] += 1
        elif row['PlacementCategory'] in ['2nd Place', '3rd Place']:
            group_stats[g]['top3'] += 1
        elif row['PlacementCategory'] == 'Pigskin':
            group_stats[g]['pigskin'] += 1

# Filter to groups with 5+ appearances
stats_df = pd.DataFrame(group_stats).T
stats_df = stats_df[stats_df['appearances'] >= 5].copy()
stats_df['win_rate'] = stats_df['wins'] / stats_df['appearances'] * 100
stats_df['top3_rate'] = stats_df['top3'] / stats_df['appearances'] * 100
stats_df['pigskin_rate'] = stats_df['pigskin'] / stats_df['appearances'] * 100
stats_df = stats_df.sort_values('top3_rate', ascending=True)

y = np.arange(len(stats_df))
bar_height = 0.6

# Stacked horizontal bars: win rate + (top3 - win) rate + pigskin rate
remaining_top3 = stats_df['top3_rate'] - stats_df['win_rate']
bars1 = ax.barh(y, stats_df['win_rate'], bar_height, label='1st Place %', color='#FFD700')
bars2 = ax.barh(y, remaining_top3, bar_height, left=stats_df['win_rate'], label='2nd/3rd Place %', color='#C0C0C0')
bars3 = ax.barh(y, stats_df['pigskin_rate'], bar_height, left=stats_df['top3_rate'], label='Pigskin %', color='#2ca02c', alpha=0.7)

ax.set_yticks(y)
ax.set_yticklabels([f"{name} (n={int(stats_df.loc[name, 'appearances'])})" for name in stats_df.index], fontsize=10)
ax.set_xlabel('Percentage of Appearances (%)', fontsize=12)
ax.set_title('Which Groups Have the Best Win Rate Among Frequent Competitors?', fontsize=14, fontweight='bold')
ax.legend(loc='lower right', fontsize=11)
ax.set_xlim(0, 105)

# Add total success rate labels
for i, (idx, row) in enumerate(stats_df.iterrows()):
    total = row['top3_rate'] + row['pigskin_rate']
    ax.text(total + 1, i, f"{total:.0f}%", va='center', fontsize=9, fontweight='bold', color='#333')

plt.tight_layout()
plt.savefig('/Users/raleightognela/Documents/sing_data/plot_06_win_rates.png', dpi=150)
plt.close()
print("Plot 6 replacement saved: plot_06_win_rates.png")
