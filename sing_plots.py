import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from collections import Counter
import re

# Load data
df = pd.read_csv('/Users/raleightognela/Documents/sing_data/baylor-sing-all-acts-final.csv')

# --- Data prep ---
# Standardize placement into categories
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
    elif '4th' in p or '5th' in p or '6th' in p:
        return 'Other Placement'
    elif 'Pigskin' in p:
        return 'Pigskin'
    elif p == 'Participated':
        return 'Participated'
    else:
        return 'Other Placement'

df['PlacementCategory'] = df['Placement'].apply(categorize_placement)

# Detect paired acts
df['IsPaired'] = df['Group'].str.contains('&', na=False)

# Count songs per act
def count_songs(s):
    if pd.isna(s) or s.strip() == '':
        return 0
    return len(s.split(';'))

df['SongCount'] = df['Songs'].apply(count_songs)

# Decade
df['Decade'] = (df['Year'] // 10) * 10

# Base group names (split paired acts)
def get_base_groups(group_name):
    parts = re.split(r'\s*&\s*', str(group_name))
    return [p.strip() for p in parts]

plt.style.use('seaborn-v0_8-whitegrid')
fig_size = (12, 7)

# ============================================================
# PLOT 1: Bar Chart — "Which Groups Have Won Baylor Sing the Most Times?"
# ============================================================
fig, ax = plt.subplots(figsize=fig_size)
winners = df[df['PlacementCategory'] == '1st Place'].copy()
# Expand paired acts so each group gets credit
win_groups = []
for _, row in winners.iterrows():
    for g in get_base_groups(row['Group']):
        win_groups.append(g)
win_counts = Counter(win_groups)
top_winners = pd.DataFrame(win_counts.most_common(12), columns=['Group', 'Wins'])
colors = plt.cm.viridis(np.linspace(0.2, 0.85, len(top_winners)))
bars = ax.barh(top_winners['Group'][::-1], top_winners['Wins'][::-1], color=colors)
ax.set_xlabel('Number of 1st Place Wins', fontsize=12)
ax.set_title('Which Groups Have Won Baylor Sing the Most Times?', fontsize=14, fontweight='bold')
for bar, val in zip(bars, top_winners['Wins'][::-1]):
    ax.text(bar.get_width() + 0.15, bar.get_y() + bar.get_height()/2, str(val),
            va='center', fontsize=11, fontweight='bold')
ax.set_xlim(0, top_winners['Wins'].max() + 2)
plt.tight_layout()
plt.savefig('/Users/raleightognela/Documents/sing_data/plot_01_top_winners.png', dpi=150)
plt.close()

# ============================================================
# PLOT 2: Line Chart — "How Has Participation in Baylor Sing Grown Over Time?"
# ============================================================
fig, ax = plt.subplots(figsize=fig_size)
acts_per_year = df.groupby('Year').size().reset_index(name='NumActs')
ax.plot(acts_per_year['Year'], acts_per_year['NumActs'], 'o-', color='#2c7bb6', linewidth=2, markersize=5)
ax.fill_between(acts_per_year['Year'], acts_per_year['NumActs'], alpha=0.15, color='#2c7bb6')
ax.set_xlabel('Year', fontsize=12)
ax.set_ylabel('Number of Acts', fontsize=12)
ax.set_title('How Has Participation in Baylor Sing Grown Over Time?', fontsize=14, fontweight='bold')
# Annotate key moments
ax.annotate('First Sing\n(3 acts)', xy=(1953, 3), xytext=(1960, 5),
            arrowprops=dict(arrowstyle='->', color='gray'), fontsize=9, ha='center')
ax.annotate('COVID\ncancellation', xy=(2021, 0), xytext=(2021, 8),
            arrowprops=dict(arrowstyle='->', color='red'), fontsize=9, ha='center', color='red')
# Add a point for 2021 (no data = COVID)
ax.scatter([2021], [0], color='red', zorder=5, s=60, marker='x')
plt.tight_layout()
plt.savefig('/Users/raleightognela/Documents/sing_data/plot_02_participation_over_time.png', dpi=150)
plt.close()

# ============================================================
# PLOT 3: Pie Chart — "What Proportion of Acts Win vs. Just Participate?"
# ============================================================
fig, ax = plt.subplots(figsize=(10, 7))
placement_counts = df['PlacementCategory'].value_counts()
order = ['1st Place', '2nd Place', '3rd Place', 'Pigskin', 'Participated', 'Other Placement', 'Unknown']
placement_counts = placement_counts.reindex([o for o in order if o in placement_counts.index])
pie_colors = ['#gold', '#silver', '#cd7f32', '#2ca02c', '#9ecae1', '#d9d9d9', '#f0f0f0']
pie_colors = ['#FFD700', '#C0C0C0', '#CD7F32', '#2ca02c', '#9ecae1', '#d9d9d9']
explode = [0.05] * len(placement_counts)
wedges, texts, autotexts = ax.pie(placement_counts, labels=placement_counts.index, autopct='%1.1f%%',
                                   colors=pie_colors[:len(placement_counts)], explode=explode[:len(placement_counts)],
                                   textprops={'fontsize': 11}, startangle=90)
for t in autotexts:
    t.set_fontweight('bold')
ax.set_title('What Proportion of Acts Win vs. Just Participate?', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig('/Users/raleightognela/Documents/sing_data/plot_03_placement_distribution.png', dpi=150)
plt.close()

# ============================================================
# PLOT 4: Stacked Bar — "Has the Rise of Paired Acts Changed Competition Dynamics?"
# ============================================================
fig, ax = plt.subplots(figsize=fig_size)
paired_by_year = df.groupby(['Year', 'IsPaired']).size().unstack(fill_value=0)
paired_by_year.columns = ['Solo Acts', 'Paired Acts']
# Only show years with decent data (2002+)
paired_recent = paired_by_year[paired_by_year.index >= 2002]
paired_recent.plot(kind='bar', stacked=True, ax=ax, color=['#4292c6', '#fd8d3c'], width=0.8)
ax.set_xlabel('Year', fontsize=12)
ax.set_ylabel('Number of Acts', fontsize=12)
ax.set_title('Has the Rise of Paired Acts Changed Competition Dynamics?', fontsize=14, fontweight='bold')
ax.legend(fontsize=11)
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('/Users/raleightognela/Documents/sing_data/plot_04_paired_vs_solo.png', dpi=150)
plt.close()

# ============================================================
# PLOT 5: Histogram — "How Many Songs Do Acts Typically Perform in Their Medley?"
# ============================================================
fig, ax = plt.subplots(figsize=fig_size)
songs_data = df[df['SongCount'] > 0]['SongCount']
ax.hist(songs_data, bins=range(1, songs_data.max() + 2), color='#7570b3', edgecolor='white', alpha=0.85, align='left')
ax.axvline(songs_data.mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {songs_data.mean():.1f} songs')
ax.axvline(songs_data.median(), color='orange', linestyle='--', linewidth=2, label=f'Median: {songs_data.median():.0f} songs')
ax.set_xlabel('Number of Songs in Medley', fontsize=12)
ax.set_ylabel('Number of Acts', fontsize=12)
ax.set_title('How Many Songs Do Acts Typically Perform in Their Medley?', fontsize=14, fontweight='bold')
ax.legend(fontsize=11)
plt.tight_layout()
plt.savefig('/Users/raleightognela/Documents/sing_data/plot_05_song_count_distribution.png', dpi=150)
plt.close()

# ============================================================
# PLOT 6: Scatter/Timeline — "When Did Each Dominant Group Peak in Baylor Sing?"
# ============================================================
fig, ax = plt.subplots(figsize=(14, 7))
focus_groups = ['Kappa Omega Tau', 'Chi Omega', 'Phi Gamma Delta', 'Delta Delta Delta',
                'Phi Kappa Chi', 'Pi Beta Phi', 'Kappa Kappa Gamma', 'Kappa Sigma',
                'Zeta Tau Alpha', 'Sigma Chi']
placement_map = {'1st Place': 1, '2nd Place': 2, '3rd Place': 3, 'Pigskin': 4, 'Participated': 5}

# For each focus group, find entries (including as part of paired acts)
group_colors = plt.cm.tab10(np.linspace(0, 1, len(focus_groups)))
for i, group in enumerate(focus_groups):
    mask = df['Group'].str.contains(re.escape(group), na=False)
    group_data = df[mask].copy()
    group_data['PlacementNum'] = group_data['PlacementCategory'].map(placement_map)
    group_data = group_data.dropna(subset=['PlacementNum'])
    ax.scatter(group_data['Year'], group_data['PlacementNum'], label=group, s=50, alpha=0.8, color=group_colors[i])

ax.set_yticks([1, 2, 3, 4, 5])
ax.set_yticklabels(['1st Place', '2nd Place', '3rd Place', 'Pigskin', 'Participated'])
ax.invert_yaxis()
ax.set_xlabel('Year', fontsize=12)
ax.set_title('When Did Each Dominant Group Peak in Baylor Sing?', fontsize=14, fontweight='bold')
ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=9, ncol=1)
plt.tight_layout()
plt.savefig('/Users/raleightognela/Documents/sing_data/plot_06_group_performance_timeline.png', dpi=150, bbox_inches='tight')
plt.close()

# ============================================================
# PLOT 7: Bar Chart — "Which Musical Artists Are Most Frequently Covered at Baylor Sing?"
# ============================================================
fig, ax = plt.subplots(figsize=fig_size)
# Parse artist names from the Songs column (format: "Song Title (Artist Name)")
all_artists = []
for songs in df['Songs'].dropna():
    # Find all (Artist) patterns
    matches = re.findall(r'\(([^)]+)\)', songs)
    for m in matches:
        # Clean up
        artist = m.strip()
        # Skip things that are clearly not artist names
        if any(skip in artist.lower() for skip in ['high school musical', 'from ', 'glee cast', 'greatest showman', 'cast of']):
            # Still count some of these as the show/movie
            pass
        all_artists.append(artist)

artist_counts = Counter(all_artists)
# Clean up duplicates
cleaned = Counter()
for artist, count in artist_counts.items():
    # Normalize
    a = artist.strip()
    cleaned[a] += count

top_artists = pd.DataFrame(cleaned.most_common(15), columns=['Artist', 'Count'])
colors = plt.cm.plasma(np.linspace(0.2, 0.85, len(top_artists)))
bars = ax.barh(top_artists['Artist'][::-1], top_artists['Count'][::-1], color=colors)
ax.set_xlabel('Number of Times Covered', fontsize=12)
ax.set_title('Which Musical Artists Are Most Frequently Covered at Baylor Sing?', fontsize=14, fontweight='bold')
for bar, val in zip(bars, top_artists['Count'][::-1]):
    ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2, str(val),
            va='center', fontsize=10, fontweight='bold')
ax.set_xlim(0, top_artists['Count'].max() + 1.5)
plt.tight_layout()
plt.savefig('/Users/raleightognela/Documents/sing_data/plot_07_top_artists_covered.png', dpi=150)
plt.close()

# ============================================================
# PLOT 8: Grouped Bar — "Do Paired Acts Outperform Solo Acts?"
# ============================================================
fig, ax = plt.subplots(figsize=fig_size)
# Compare placement distributions
top3 = ['1st Place', '2nd Place', '3rd Place']
solo_df = df[~df['IsPaired']]
paired_df = df[df['IsPaired']]

categories = ['1st Place', '2nd Place', '3rd Place', 'Pigskin', 'Participated']
solo_pcts = []
paired_pcts = []
for cat in categories:
    solo_pcts.append((solo_df['PlacementCategory'] == cat).sum() / len(solo_df) * 100)
    paired_pcts.append((paired_df['PlacementCategory'] == cat).sum() / len(paired_df) * 100 if len(paired_df) > 0 else 0)

x = np.arange(len(categories))
width = 0.35
bars1 = ax.bar(x - width/2, solo_pcts, width, label=f'Solo Acts (n={len(solo_df)})', color='#4292c6')
bars2 = ax.bar(x + width/2, paired_pcts, width, label=f'Paired Acts (n={len(paired_df)})', color='#fd8d3c')
ax.set_ylabel('Percentage of Acts (%)', fontsize=12)
ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=11)
ax.set_title('Do Paired Acts Outperform Solo Acts?', fontsize=14, fontweight='bold')
ax.legend(fontsize=11)
# Add percentage labels
for bars in [bars1, bars2]:
    for bar in bars:
        h = bar.get_height()
        if h > 0.5:
            ax.text(bar.get_x() + bar.get_width()/2, h + 0.5, f'{h:.1f}%', ha='center', fontsize=9)
plt.tight_layout()
plt.savefig('/Users/raleightognela/Documents/sing_data/plot_08_paired_vs_solo_performance.png', dpi=150)
plt.close()

# ============================================================
# PLOT 9: Heatmap — "Which Groups Have the Most Consistent Participation Over the Decades?"
# ============================================================
fig, ax = plt.subplots(figsize=(14, 8))
# Count appearances per group per decade (expand paired acts)
group_decade = []
for _, row in df.iterrows():
    for g in get_base_groups(row['Group']):
        group_decade.append({'Group': g, 'Decade': row['Decade']})
gd_df = pd.DataFrame(group_decade)
gd_counts = gd_df.groupby(['Group', 'Decade']).size().unstack(fill_value=0)

# Keep only groups with >= 8 total appearances
gd_counts = gd_counts[gd_counts.sum(axis=1) >= 8]
gd_counts = gd_counts.sort_values(by=list(gd_counts.columns), ascending=False)

im = ax.imshow(gd_counts.values, cmap='YlOrRd', aspect='auto')
ax.set_xticks(range(len(gd_counts.columns)))
ax.set_xticklabels([f"{d}s" for d in gd_counts.columns], fontsize=11)
ax.set_yticks(range(len(gd_counts.index)))
ax.set_yticklabels(gd_counts.index, fontsize=10)
# Add text annotations
for i in range(len(gd_counts.index)):
    for j in range(len(gd_counts.columns)):
        val = gd_counts.values[i, j]
        if val > 0:
            color = 'white' if val > gd_counts.values.max() * 0.6 else 'black'
            ax.text(j, i, str(val), ha='center', va='center', fontsize=10, color=color, fontweight='bold')
plt.colorbar(im, ax=ax, label='Number of Appearances')
ax.set_title('Which Groups Have the Most Consistent Participation Over the Decades?', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig('/Users/raleightognela/Documents/sing_data/plot_09_group_participation_heatmap.png', dpi=150)
plt.close()

# ============================================================
# PLOT 10: Bar Chart — "How Has the Diversity of Winners Changed Across Eras?"
# ============================================================
fig, ax = plt.subplots(figsize=fig_size)
# Group winners by era and count unique winners
eras = {
    '1953-1979': (1953, 1979),
    '1980-1989': (1980, 1989),
    '1990-1999': (1990, 1999),
    '2000-2009': (2000, 2009),
    '2010-2019': (2010, 2019),
    '2020-2026': (2020, 2026),
}
era_labels = []
unique_winners_count = []
total_wins_count = []
for era_name, (start, end) in eras.items():
    era_winners = winners[(winners['Year'] >= start) & (winners['Year'] <= end)]
    era_groups = []
    for _, row in era_winners.iterrows():
        for g in get_base_groups(row['Group']):
            era_groups.append(g)
    era_labels.append(era_name)
    unique_winners_count.append(len(set(era_groups)))
    total_wins_count.append(len(era_groups))

x = np.arange(len(era_labels))
width = 0.35
ax.bar(x - width/2, total_wins_count, width, label='Total 1st Place Finishes', color='#4292c6')
ax.bar(x + width/2, unique_winners_count, width, label='Unique Winning Groups', color='#e6550d')
ax.set_xticks(x)
ax.set_xticklabels(era_labels, fontsize=11)
ax.set_ylabel('Count', fontsize=12)
ax.set_title('How Has the Diversity of Winners Changed Across Eras?', fontsize=14, fontweight='bold')
ax.legend(fontsize=11)
# Add value labels
for i, (tw, uw) in enumerate(zip(total_wins_count, unique_winners_count)):
    ax.text(i - width/2, tw + 0.2, str(tw), ha='center', fontsize=10, fontweight='bold')
    ax.text(i + width/2, uw + 0.2, str(uw), ha='center', fontsize=10, fontweight='bold')
plt.tight_layout()
plt.savefig('/Users/raleightognela/Documents/sing_data/plot_10_winner_diversity_by_era.png', dpi=150)
plt.close()

print("All 10 plots saved successfully!")
print("\nPlot files:")
for i in range(1, 11):
    print(f"  plot_{i:02d}_*.png")
