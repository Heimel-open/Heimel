"""Plot swarm coherence over time: chaos vs. Phi-Law filter."""

import matplotlib
matplotlib.use('Agg')
import json
import os
import matplotlib.pyplot as plt
import numpy as np

RESULTS_DIR = "results"
OUTPUT_FILE = os.path.join(RESULTS_DIR, "coherence_comparison.png")


def load(label: str) -> tuple:
    path = os.path.join(RESULTS_DIR, f"coherence_{label}.json")
    with open(path) as f:
        data = json.load(f)
    steps = [d["step"] for d in data]
    values = [d["coherence"] for d in data]
    return steps, values


def main():
    fig, ax = plt.subplots(figsize=(10, 5))

    for label, color, name in [
        ("chaos", "#e74c3c", "Ingen filter (kaos)"),
        ("phi_filter", "#2ecc71", "Phi-Lov filter (Lovgiveren)"),
    ]:
        steps, values = load(label)
        smooth = np.convolve(values, np.ones(20) / 20, mode="valid")
        ax.plot(steps, values, alpha=0.25, color=color)
        ax.plot(range(len(smooth)), smooth, color=color, linewidth=2, label=name)

    ax.set_xlabel("Tidssteg", fontsize=12)
    ax.set_ylabel("Koherens-avvik (MAD) — lavere er bedre", fontsize=12)
    ax.set_title("Swarm-koherens: Kaos vs. Phi-Lov Filter", fontsize=14)
    ax.legend(fontsize=11)
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_FILE, dpi=150)
    print(f"Saved: {OUTPUT_FILE}")
    plt.show()


if __name__ == "__main__":
    main()
