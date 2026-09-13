"""
swarm_sim.py - P5: Swarm Coherence under Φ-loven

Simulerer N agenter som hver følger LIM-prinsippet individuelt.
De deler ingen sentral kontroll. De deler kun loven (Φ).
Resonans oppstår når flere agenter samtidig er i koherens-sonen [1888, 4766].
"""

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except ImportError:
    matplotlib = None
    plt = None
import numpy as np
from tqdm import tqdm
import os
import json

DEFAULT_SEED = 449527


class Agent:
    def __init__(self, agent_id, initial_tau=4000.0):
        self.id = agent_id
        self.tau = initial_tau
        self.C_0 = 4495.27
        self.alpha = 0.42
        self.tau_min = 1888.0
        self.tau_max = 4766.0
        self.energy = 1.0
        self.coherent_steps = 0

    def step(self, noise_level=0.1, rng=None):
        if rng is None:
            rng = np.random.default_rng(DEFAULT_SEED + self.id)
        delta_h = rng.normal(0, noise_level * 10)
        self.tau += abs(delta_h)

        if self.tau < self.tau_min:
            self.tau += (self.tau_min - self.tau) * 0.1
        elif self.tau > self.tau_max:
            self.tau += (self.tau_max - self.tau) * 0.1

        is_coherent = self.tau_min <= self.tau <= self.tau_max

        if is_coherent:
            self.coherent_steps += 1
            self.energy = min(1.0, self.energy + 0.01)
        else:
            self.coherent_steps = 0
            self.energy = max(0.0, self.energy - 0.05)

        return is_coherent, self.tau


def run_swarm_simulation(n_agents=100, n_steps=200, with_phi_law=True, seed=DEFAULT_SEED):
    rng = np.random.default_rng(seed + (0 if with_phi_law else 1))
    agents = [Agent(i) for i in range(n_agents)]

    history = {
        'tau_matrix': np.zeros((n_steps, n_agents)),
        'coherence_count': np.zeros(n_steps),
        'resonance_events': []
    }

    label = "Med Φ-lov" if with_phi_law else "Uten Φ-lov"
    print(f"\n Starter P5-simulering: {n_agents} agenter, {n_steps} steg — {label}")

    for t in tqdm(range(n_steps)):
        coherent_at_step = 0

        for i, agent in enumerate(agents):
            if not with_phi_law:
                delta_h = rng.normal(0, 50)
                agent.tau += abs(delta_h)
                is_coherent = agent.tau_min <= agent.tau <= agent.tau_max
                history['tau_matrix'][t, i] = agent.tau
            else:
                is_coherent, current_tau = agent.step(noise_level=0.1, rng=rng)
                history['tau_matrix'][t, i] = current_tau

            if is_coherent:
                coherent_at_step += 1

        history['coherence_count'][t] = coherent_at_step

        if coherent_at_step / n_agents > 0.8:
            history['resonance_events'].append(t)

    return history


def plot_swarm_results(history_with, history_without, n_agents):
    fig, axs = plt.subplots(3, 1, figsize=(14, 12))
    steps = range(len(history_with['coherence_count']))

    ax1 = axs[0]
    ax1.plot(steps, history_with['coherence_count'], label='Med Φ-lov (LIM)', color='#2ecc71', linewidth=2)
    ax1.plot(steps, history_without['coherence_count'], label='Uten Φ-lov (Kaos)', color='#e74c3c', linestyle='--', linewidth=2)
    ax1.axhline(y=n_agents * 0.8, color='blue', linestyle=':', label='Resonans-terskel (80%)')
    ax1.set_title('Antall Agenter i Koherens-sonen over Tid')
    ax1.set_ylabel('Antall Agenter')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2 = axs[1]
    avg_tau_with = np.mean(history_with['tau_matrix'], axis=1)
    avg_tau_without = np.mean(history_without['tau_matrix'], axis=1)
    ax2.plot(steps, avg_tau_with, label='Gj.snitt Tau (Med Φ)', color='#2ecc71')
    ax2.plot(steps, avg_tau_without, label='Gj.snitt Tau (Uten Φ)', color='#e74c3c')
    ax2.axhline(y=4495.27, color='blue', linestyle=':', label='C₀')
    ax2.set_title('Gjennomsnittlig Tau (Svermens Puls)')
    ax2.set_ylabel('Tau-verdi')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    ax3 = axs[2]
    resonance_times = history_with['resonance_events']
    if resonance_times:
        ax3.scatter(resonance_times, [1] * len(resonance_times),
                    color='#f1c40f', s=100, zorder=5, label='Resonans-hendelse')
    ax3.set_title('Resonans-hendelser (>80% i koherens samtidig)')
    ax3.set_xlabel('Tid (Steg)')
    ax3.set_yticks([])
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    os.makedirs('results', exist_ok=True)
    plt.savefig('results/p5_swarm_results.png', dpi=300)
    print("Graf lagret: results/p5_swarm_results.png")
    plt.show()


def export_json_for_visualization(hist_with, hist_without):
    """Export per-step MAD as JSON for visualization.py."""
    os.makedirs('results', exist_ok=True)
    for label, hist in [("phi_filter", hist_with), ("chaos", hist_without)]:
        records = []
        for t in range(hist['tau_matrix'].shape[0]):
            tau_row = hist['tau_matrix'][t]
            mad = float(np.mean(np.abs(tau_row - np.median(tau_row))))
            records.append({"step": t, "coherence": mad})
        path = os.path.join('results', f'coherence_{label}.json')
        with open(path, 'w') as f:
            json.dump(records, f)
        print(f"JSON eksportert: {path}")


if __name__ == "__main__":
    os.makedirs('results', exist_ok=True)

    hist_with = run_swarm_simulation(n_agents=100, n_steps=200, with_phi_law=True)
    hist_without = run_swarm_simulation(n_agents=100, n_steps=200, with_phi_law=False)

    plot_swarm_results(hist_with, hist_without, n_agents=100)
    export_json_for_visualization(hist_with, hist_without)

    print("\n--- RESULTAT ---")
    print(f"Resonans-hendelser (Med Φ): {len(hist_with['resonance_events'])}")
    print(f"Resonans-hendelser (Uten Φ): {len(hist_without['resonance_events'])}")

    if hist_with['resonance_events']:
        print("Svermen fant harmoni. Tofoo. Φ")
    else:
        print("Ingen resonans oppnådd.")
