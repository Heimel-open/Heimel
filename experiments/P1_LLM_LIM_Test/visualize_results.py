"""
visualize_results.py - Visualiserer resultater fra P1-eksperimentet

Laster loggfiler eller bruker data fra experiment.py til å generere:
1. Tau-konvergens mot C_0
2. Entropi-stabilitet
3. Status-fordeling (Koherens vs. Kaos/Stasis)
"""

import matplotlib.pyplot as plt
import numpy as np
import json
import os

def plot_tau_convergence(tau_history_with, tau_history_without, save_path='results/tau_convergence.png'):
    """Plotter hvordan Tau utvikler seg over tid med og uten filter."""

    plt.figure(figsize=(12, 6))

    steps_with = list(range(len(tau_history_with)))
    steps_without = list(range(len(tau_history_without)))

    plt.plot(steps_with, tau_history_with, label='Med LIM-Filter (Φ-loven)', color='#2ecc71', linewidth=2.5)
    plt.plot(steps_without, tau_history_without, label='Uten Filter (Kontroll)', color='#e74c3c', linestyle='--', linewidth=2.5)

    C_0 = 4495.27
    tau_min = 1888.0
    tau_max = 4766.0

    plt.axhline(y=C_0, color='#3498db', linestyle=':', linewidth=2, label=f'C₀ = {C_0}')
    plt.axhspan(tau_min, tau_max, color='#f1c40f', alpha=0.1, label='Koherens-sone [1888, 4766]')

    plt.title('Tau (Akkumulert Friksjon) over Tid', fontsize=14, fontweight='bold')
    plt.xlabel('Genereringssteg', fontsize=12)
    plt.ylabel('Tau-verdi (bits)', fontsize=12)
    plt.legend(loc='upper right')
    plt.grid(True, alpha=0.3)

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Graf lagret: {save_path}")
    plt.show()

def plot_status_distribution(status_history_with, status_history_without, save_path='results/status_dist.png'):
    """Plotter fordelingen av systemtilstander."""

    fig, ax = plt.subplots(1, 2, figsize=(14, 6))

    status_colors = {
        'COHERENT': '#2ecc71',
        'KAOS_DETECTED': '#e74c3c',
        'STASIS_DETECTED': '#9b59b6',
        'UNFILTERED': '#95a5a6'
    }

    def count_statuses(history):
        counts = {}
        for s in history:
            counts[s] = counts.get(s, 0) + 1
        return counts

    counts_with = count_statuses(status_history_with)
    counts_without = count_statuses(status_history_without)

    labels_with = list(counts_with.keys())
    values_with = list(counts_with.values())
    colors_with = [status_colors.get(l, '#000') for l in labels_with]

    ax[0].bar(labels_with, values_with, color=colors_with)
    ax[0].set_title('Med LIM-Filter', fontsize=12, fontweight='bold')
    ax[0].set_ylabel('Antall Steg')
    ax[0].tick_params(axis='x', rotation=45)

    labels_without = list(counts_without.keys())
    values_without = list(counts_without.values())
    colors_without = [status_colors.get(l, '#000') for l in labels_without]

    ax[1].bar(labels_without, values_without, color=colors_without)
    ax[1].set_title('Uten Filter (Kontroll)', fontsize=12, fontweight='bold')
    ax[1].set_ylabel('Antall Steg')
    ax[1].tick_params(axis='x', rotation=45)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"Graf lagret: {save_path}")
    plt.show()

if __name__ == "__main__":
    print("Visualiseringsverktøy for Φ-loven P1")
    print("For å bruke dette, kjør først experiment.py og lagre historikken.")

    dummy_tau_with = [2000 + i * 50 for i in range(50)]
    dummy_tau_without = [2000 + np.random.normal(0, 500) for _ in range(50)]

    dummy_status_with = ['COHERENT'] * 40 + ['KAOS_DETECTED'] * 10
    dummy_status_without = ['UNFILTERED'] * 20 + ['KAOS_DETECTED'] * 30

    plot_tau_convergence(dummy_tau_with, dummy_tau_without)
    plot_status_distribution(dummy_status_with, dummy_status_without)
