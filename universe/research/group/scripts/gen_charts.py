#!/usr/bin/env python3
"""Generate professional charts for Agentic Execution Risk report."""
import json, math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
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
CHARTS.mkdir(exist_ok=True)

results = json.loads((BASE / "research/model_results.json").read_text())
meta = json.loads((BASE / "research/model_meta.json").read_text())

# ==== CHART 1: Agent growth (logistic curves) ====
fig, ax = plt.subplots(figsize=(10, 6))
colors = ['#c0392b', '#e74c3c', '#3498db', '#2ecc71', '#95a5a6']
labels = ['7d', '14d', '30d (realistisk)', '60d', '90d']
doings = [7, 14, 30, 60, 90]
K = 1e9

days = np.linspace(0, 365, 100)
for i, (d, label, color) in enumerate(zip(doings, labels, colors)):
    vals = []
    for t in days:
        exp = 20e6 * (2 ** (t / d))
        vals.append(exp / (1 + exp / K))
    ax.plot(days, np.array(vals)/1e6, label=label, color=color, linewidth=2.2,
            linestyle='-' if d == 30 else '--')
    # Annotate end value
    final = vals[-1] / 1e6
    if final > 1:
        ax.annotate(f'{final:.0f}M', xy=(365, final), fontsize=9, fontweight='bold',
                    color=color, va='center', ha='left', xytext=(5, 0),
                    textcoords='offset points')

ax.axhline(y=1000, color='grey', linestyle=':', alpha=0.5, linewidth=1)
ax.axhline(y=20, color='#f39c12', linestyle=':', alpha=0.5, linewidth=1)
ax.text(5, 1005, f'Metning: K = 1 000M', fontsize=9, color='grey')
ax.text(5, 25, f'Baseline: 20M (juli 2026)', fontsize=9, color='#f39c12')

ax.set_xlim(0, 365)
ax.set_ylabel('Antall autonome agenter (millioner)', fontweight='bold')
ax.set_xlabel('Dager fra juli 2026', fontweight='bold')
ax.set_title('Agent-populasjon under ulike doblingsscenarioer\n(Logistisk demping mot K=1B)', 
             fontweight='bold', fontsize=13, pad=15)
ax.legend(loc='upper left', frameon=True, facecolor='white', edgecolor='grey')
ax.set_ylim(0, 1100)

plt.tight_layout()
plt.savefig(CHARTS / "fig1_agent_growth.png", dpi=150, bbox_inches='tight')
print(f"✅ fig1_agent_growth.png")
plt.close()
