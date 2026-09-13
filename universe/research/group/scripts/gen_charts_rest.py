#!/usr/bin/env python3
"""Generate remaining professional charts for the report."""
import json, math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 10,
    'axes.grid': True,
    'grid.alpha': 0.3,
    'axes.spines.top': False,
    'axes.spines.right': False,
})

BASE = Path("/home/njaal/agentic-execution-risk")
CHARTS = BASE / "research/charts"

results = json.loads((BASE / "research/model_results.json").read_text())
meta = json.loads((BASE / "research/model_meta.json").read_text())

# ==== CHART 2: Incidents heatmap (matrix) ====
fig, ax = plt.subplots(figsize=(12, 6))

doubings = [7, 14, 30, 60, 90]
horizons = [3, 6, 9, 12]
matrix = []

for r in results:
    row = []
    for d in doubings:
        key = f'd{d}_incidents'
        if key in r:
            row.append(r[key])
    matrix.append(row)

# Create heatmap
matrix_arr = np.array(matrix)
im = ax.imshow(matrix_arr, cmap='YlOrRd', aspect='auto', interpolation='nearest')

# Set ticks
ax.set_xticks(np.arange(len(doubings)))
ax.set_yticks(np.arange(len(horizons)))
ax.set_xticklabels([f'{d}d\ndobling' for d in doubings], fontsize=9)
ax.set_yticklabels([f'{h} mnd' for h in horizons], fontsize=9)
ax.set_xlabel('Doblingsperiode', fontweight='bold', fontsize=11)
ax.set_ylabel('Prognosehorisont', fontweight='bold', fontsize=11)

# Add text annotations
for i in range(len(horizons)):
    for j in range(len(doubings)):
        val = matrix_arr[i, j]
        if val < 1e6:
            text = ax.text(j, i, f'{val/1e3:.0f}K', 
                         ha="center", va="center", color="black", fontsize=8, fontweight='bold')
        else:
            text = ax.text(j, i, f'{val/1e6:.2f}M', 
                         ha="center", va="center", color="white", fontsize=8, fontweight='bold')

ax.set_title('Kritiske hendelser per kvartal\n(Matrix: doblingsperiode × horisont)', 
             fontweight='bold', fontsize=13, pad=15)

# Colorbar
cbar = plt.colorbar(im, ax=ax)
cbar.set_label('Hendelser/kvartal', rotation=270, labelpad=20, fontweight='bold')

plt.tight_layout()
plt.savefig(CHARTS / "fig2_incidents_heatmap.png", dpi=150, bbox_inches='tight')
print(f"✅ fig2_incidents_heatmap.png")
plt.close()

# ==== CHART 3: Error rates comparison (simple vs multi-agent) ====
fig, ax = plt.subplots(figsize=(10, 6))

categories = ['Enkle agenter\n(single-action)', 'Multi-agent\n(workflow)']
rates = [0.01, 0.30]
colors = ['#27ae60', '#c0392b']

bars = ax.bar(categories, rates, color=colors, width=0.6, edgecolor='white', linewidth=2)

# Add value labels on bars
for i, (bar, rate) in enumerate(zip(bars, rates)):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 0.008,
            f'{rate*100:.2f}%',
            ha='center', va='bottom', fontweight='bold', fontsize=14, color=colors[i])

# Add multiplier annotation
ax.annotate('30× høyere', 
            xy=(1, 0.30), xytext=(1, 0.22),
            fontsize=12, fontweight='bold', color='#c0392b',
            ha='center', va='center',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#fadbd8', edgecolor='#c0392b', linewidth=2),
            arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))

ax.set_ylabel('Kritisk hendelsesrate (%/kvartal)', fontweight='bold', fontsize=11)
ax.set_title('Differensierte feilrater: Enkel vs Multi-Agent', 
             fontweight='bold', fontsize=13, pad=15)
ax.set_ylim(0, 0.38)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig(CHARTS / "fig3_error_rates.png", dpi=150, bbox_inches='tight')
print(f"✅ fig3_error_rates.png")
plt.close()

# ==== CHART 4: Iceberg visualization ====
fig, ax = plt.subplots(figsize=(10, 8))

# Water fill
ax.fill_between([0, 10], [-2, -2], [0, 0], color='#3498db', alpha=0.3)

# Above water - iceberg top using polygon (9 top points + close at base)
iceberg_top_x = [2, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 8, 8, 2]
iceberg_top_y = [0, 0.5, 1.2, 1.8, 2.2, 2.5, 2.2, 1.8, 1.2, 0.5, 0, 0, 0]
ax.fill(iceberg_top_x, iceberg_top_y, color='#ecf0f1', edgecolor='#95a5a6', linewidth=2)
ax.text(5, 1.5, 'RAPPORTERT\n(AIID)\n\n1 571\nhendelser', 
        ha='center', va='center', fontweight='bold', fontsize=12, color='#34495e')

# Below water - iceberg bottom using polygon
iceberg_bottom_x = [1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 8.5, 1.5]
iceberg_bottom_y = [0, -0.5, -1.0, -1.5, -2.0, -2.2, -2.35, -2.4, -2.35, -2.2, -2.0, -1.5, -1.0, -0.5, 0, 0, 0, 0]
ax.fill(iceberg_bottom_x, iceberg_bottom_y, color='#7f8c8d', edgecolor='#566573', linewidth=2, alpha=0.7)
ax.text(5, -1.3, 'REELLE TALL\n(Estimert)\n\n10 000 - 100 000\nhendelser\n\n(Under-rapportering:\n10-100×)', 
        ha='center', va='center', fontweight='bold', fontsize=10.5, color='white')

# Water line
ax.plot([0, 10], [0, 0], 'b-', linewidth=3)
ax.text(0.5, 0.15, 'Vannlinje', fontsize=9, color='#3498db', fontweight='bold')

ax.set_xlim(0, 10)
ax.set_ylim(-2.6, 3)
ax.set_aspect('equal')
ax.axis('off')
ax.set_title('Isfjell-effekten: Rapportert vs Reelt totalskadeomfang', 
             fontweight='bold', fontsize=13, pad=20)

plt.tight_layout()
plt.savefig(CHARTS / "fig4_iceberg.png", dpi=150, bbox_inches='tight')
print(f"✅ fig4_iceberg.png")
plt.close()

# ==== CHART 5: Scenarios comparison (bar chart) ====
fig, ax = plt.subplots(figsize=(10, 6))

scenarios = ['Konservativ\n(90d dobling)', 'Realistisk\n(30d dobling)', 'Aggressiv\n(14d dobling)']
agents_12m = [242, 988, 1000]  # millions
incidents_12m = [0.306, 1.24, 1.26]  # millions
probabilities = [15, 60, 25]

x = np.arange(len(scenarios))
width = 0.35

bars1 = ax.bar(x - width/2, agents_12m, width, label='Agenter (M)', color='#3498db', 
               edgecolor='white', linewidth=2)
bars2 = ax.bar(x + width/2, incidents_12m, width, label='Hendelser (M)', color='#c0392b',
               edgecolor='white', linewidth=2)

# Add value labels
for bar in bars1:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 15,
            f'{height:.0f}M', ha='center', va='bottom', fontweight='bold', fontsize=10)

for bar in bars2:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 0.02,
            f'{height:.2f}M', ha='center', va='bottom', fontweight='bold', fontsize=10, color='#c0392b')

ax.set_ylabel('Antall (millioner)', fontweight='bold', fontsize=11)
ax.set_title('Tre scenarioer: 12-mnd prognose', fontweight='bold', fontsize=13, pad=15)
ax.set_xticks(x)
ax.set_xticklabels(scenarios, fontsize=9)
ax.legend(loc='upper left', frameon=True, fontsize=10)

# Add probability annotations
for i, prob in enumerate(probabilities):
    ax.text(i, max(agents_12m[i], incidents_12m[i]*10) + 80,
            f'{prob}% sannsynlighet', ha='center', va='bottom',
            fontweight='bold', fontsize=9, color='grey')

plt.tight_layout()
plt.savefig(CHARTS / "fig5_scenarios.png", dpi=150, bbox_inches='tight')
print(f"✅ fig5_scenarios.png")
plt.close()

# ==== CHART 6: Timeline of critical incidents (deaths, major经济损失) ====
fig, ax = plt.subplots(figsize=(12, 6))

years = ['2023', '2024', '2025', '2026 YTD']
deaths = [1, 3, 8, 3]  # Estimated counts
economic_loss_m = [25.6, 150, 450, 220]  # millions USD

x = np.arange(len(years))
width = 0.35

ax2 = ax.twinx()
bars1 = ax.bar(x - width/2, deaths, width, label='Dødsfall', color='#95a5a6', 
               edgecolor='white', linewidth=2)
bars2 = ax2.bar(x + width/2, economic_loss_m, width, label='Økonomisk tap ($M)', 
                color='#c0392b', edgecolor='white', linewidth=2, alpha=0.8)

ax.set_ylabel('Antall dødsfall', fontweight='bold', fontsize=11, color='#95a5a6')
ax2.set_ylabel('Økonomisk tap (millioner USD)', fontweight='bold', fontsize=11, color='#c0392b')

ax.set_xlabel('År', fontweight='bold', fontsize=11)
ax.set_title('Kritiske hendelser: Dødsfall og økonomisk tap (2023-2026)',
             fontweight='bold', fontsize=13, pad=15)
ax.set_xticks(x)
ax.set_xticklabels(years)

# Combine legends
lines1, labels1 = ax.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=10)

ax.spines['top'].set_visible(False)
ax2.spines['top'].set_visible(False)

plt.tight_layout()
plt.savefig(CHARTS / "fig6_critical_incidents_timeline.png", dpi=150, bbox_inches='tight')
print(f"✅ fig6_critical_incidents_timeline.png")
plt.close()

# ==== CHART 7: Sector risk distribution (pie chart) ====
fig, ax = plt.subplots(figsize=(8, 8))

sectors = ['Autonom transport', 'Finans', 'Helsevesen', 'Utdanning/Barn', 'Juridisk', 'Privacy']
percentages = [25, 22, 20, 15, 10, 8]
colors = ['#c0392b', '#e74c3c', '#f39c12', '#3498db', '#95a5a6', '#7f8c8d']

wedges, texts, autotexts = ax.pie(percentages, labels=sectors, autopct='%1.0f%%',
                                    colors=colors, startangle=90, textprops={'fontsize': 10})

for autotext in autotexts:
    autotext.set_color('white')
    autotext.set_fontweight('bold')
    autotext.set_fontsize(11)

ax.set_title('Fordeling av sektor-risiko (basert på hendelsestype)', 
             fontweight='bold', fontsize=13, pad=20)

plt.tight_layout()
plt.savefig(CHARTS / "fig7_sector_risk.png", dpi=150, bbox_inches='tight')
print(f"✅ fig7_sector_risk.png")
plt.close()

# ==== CHART 8: Multi-agent adoption over time ====
fig, ax = plt.subplots(figsize=(10, 6))

quarters = ['Q3 2026', 'Q4 2026', 'Q1 2027', 'Q2 2027', 'Q3 2027', 'Q4 2027']
multi_pct = [10, 20, 25, 30, 35, 40]

ax.plot(quarters, multi_pct, color='#c0392b', linewidth=3, marker='o', markersize=8)
ax.fill_between(quarters, multi_pct, alpha=0.3, color='#fadbd8')

for i, pct in enumerate(multi_pct):
    ax.text(i, pct + 1.5, f'{pct}%', ha='center', va='bottom',
            fontweight='bold', fontsize=11, color='#c0392b')

ax.set_ylabel('Andel multi-agent workflows (%)', fontweight='bold', fontsize=11)
ax.set_xlabel('Kvartal', fontweight='bold', fontsize=11)
ax.set_title('Økende andel multi-agent workflows over tid\n(Høyere feilrate: 0.30% vs 0.01% for enkle agenter)',
             fontweight='bold', fontsize=13, pad=15)
ax.set_ylim(0, 50)
ax.axhline(y=30, color='grey', linestyle='--', alpha=0.5)
ax.text(0.5, 31, 'Kritisk terskel: 30% multi-agent andel', fontsize=9, color='grey')

plt.tight_layout()
plt.savefig(CHARTS / "fig8_multi_agent_adoption.png", dpi=150, bbox_inches='tight')
print(f"✅ fig8_multi_agent_adoption.png")
plt.close()

print("\n✅ Alle 8 grafer generert i /research/charts/")
