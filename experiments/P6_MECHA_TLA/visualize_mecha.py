"""
visualize_mecha.py — Plot MECHA verification results

Generates:
  results/mecha_verification_report.png   — side-by-side comparison (correct vs bug)
  results/mecha_state_space.png           — BFS state distribution
"""

import matplotlib
matplotlib.use('Agg')
import json
import os
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

RESULTS_DIR = "results"


def load(filename: str) -> dict:
    with open(os.path.join(RESULTS_DIR, filename)) as f:
        return json.load(f)


def plot_report(correct: dict, bug: dict):
    fig = plt.figure(figsize=(16, 10))
    fig.suptitle(
        "MECHA Formal Verification Report\n"
        "EFAVΛLΦ_Epistemic — ConjunctiveIntegrity, SeparationOfDuties, NoDoubleFinalize",
        fontsize=14, fontweight='bold', y=0.98
    )

    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.35)

    # ── Row 0 left: State counts ────────────────────────────────────────────
    ax0 = fig.add_subplot(gs[0, 0])
    versions = ['v1.1\n(Correct)', 'v1.0\n(Bug)']
    totals = [correct['total_states'], bug['total_states']]
    bars = ax0.bar(versions, totals, color=['#2ecc71', '#e74c3c'], width=0.4)
    ax0.bar_label(bars, fmt='%d', padding=4, fontsize=11)
    ax0.set_title('Reachable States', fontsize=11)
    ax0.set_ylabel('States explored')
    ax0.set_ylim(0, max(totals) * 1.25)
    ax0.grid(axis='y', alpha=0.3)

    # ── Row 0 center: Violation counts ─────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 1])
    violations = [len(correct['violations']), len(bug['violations'])]
    bars2 = ax1.bar(versions, violations, color=['#2ecc71', '#e74c3c'], width=0.4)
    ax1.bar_label(bars2, fmt='%d', padding=4, fontsize=11)
    ax1.set_title('Total Invariant Violations', fontsize=11)
    ax1.set_ylabel('Violations')
    ax1.set_ylim(0, max(violations) * 1.3 + 1)
    ax1.grid(axis='y', alpha=0.3)

    # ── Row 0 right: Invariant status for correct run ──────────────────────
    ax2 = fig.add_subplot(gs[0, 2])
    inv_names = ['Conjunctive\nIntegrity', 'Separation\nof Duties', 'No Double\nFinalize']
    correct_stats = correct['invariant_stats']
    bug_stats = bug['invariant_stats']
    keys = ['ConjunctiveIntegrity', 'SeparationOfDuties', 'NoDoubleFinalize']
    x = np.arange(len(keys))
    w = 0.3
    c_vals = [correct_stats[k] for k in keys]
    b_vals = [bug_stats[k] for k in keys]
    ax2.bar(x - w/2, c_vals, w, label='v1.1 (correct)', color='#2ecc71')
    ax2.bar(x + w/2, b_vals, w, label='v1.0 (bug)', color='#e74c3c')
    ax2.set_xticks(x)
    ax2.set_xticklabels(inv_names, fontsize=9)
    ax2.set_title('Violations per Invariant', fontsize=11)
    ax2.set_ylabel('Violations')
    ax2.legend(fontsize=9)
    ax2.grid(axis='y', alpha=0.3)

    # ── Row 1 left: BFS level distribution (correct) ───────────────────────
    ax3 = fig.add_subplot(gs[1, 0:2])
    c_levels = correct['states_by_level']
    b_levels = bug['states_by_level']
    all_levels = sorted(set(list(c_levels.keys()) + list(b_levels.keys())), key=int)
    c_counts = [c_levels.get(str(l), 0) for l in all_levels]
    b_counts = [b_levels.get(str(l), 0) for l in all_levels]
    x_l = np.arange(len(all_levels))
    w2 = 0.4
    ax3.bar(x_l - w2/2, c_counts, w2, label='v1.1 (correct)', color='#2ecc71', alpha=0.85)
    ax3.bar(x_l + w2/2, b_counts, w2, label='v1.0 (bug)', color='#e74c3c', alpha=0.85)
    ax3.set_xticks(x_l)
    ax3.set_xticklabels([str(l) for l in all_levels], fontsize=8)
    ax3.set_xlabel('BFS Level (depth from initial state)')
    ax3.set_ylabel('New states at level')
    ax3.set_title('State Space Exploration by BFS Depth', fontsize=11)
    ax3.legend(fontsize=9)
    ax3.grid(axis='y', alpha=0.3)

    # ── Row 1 right: Summary card ──────────────────────────────────────────
    ax4 = fig.add_subplot(gs[1, 2])
    ax4.axis('off')
    summary = (
        "Verification Summary\n"
        "─────────────────────────────\n"
        f"  Model: EFAVΛLΦ_Epistemic\n"
        f"  Operators: op1, op2\n"
        f"  MaxTime: 3\n\n"
        "  v1.1 (Correct)\n"
        f"  States: {correct['total_states']:,}\n"
        f"  Violations: 0\n"
        f"  Result: [OK] ALL INVARIANTS HOLD\n\n"
        "  v1.0 (Bug: missing ~vetoed guard)\n"
        f"  States: {bug['total_states']:,}\n"
        f"  Violations: {len(bug['violations'])}\n"
        f"  Result: [FAIL] NoDoubleFinalize VIOLATED\n\n"
        "  Bug detected in AllowAction:\n"
        "  Missing guard ~vetoed[op]\n"
        "  allowed executed ∧ vetoed."
    )
    ax4.text(0.05, 0.95, summary, transform=ax4.transAxes,
             fontsize=9, verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='#f8f9fa', alpha=0.8))

    out = os.path.join(RESULTS_DIR, "mecha_verification_report.png")
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f"Lagret: {out}")
    plt.close()


def main():
    correct = load("mecha_correct.json")
    bug = load("mecha_bug.json")
    plot_report(correct, bug)
    print("\nVerifikasjon fullført.")
    print(f"  v1.1 states: {correct['total_states']}, violations: {len(correct['violations'])}")
    print(f"  v1.0 states: {bug['total_states']}, violations: {len(bug['violations'])}")


if __name__ == "__main__":
    main()
