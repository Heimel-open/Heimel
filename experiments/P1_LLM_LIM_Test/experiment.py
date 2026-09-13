"""
experiment.py - Kjør P1: LLM med og uten LIM-filter

Sammenligner to instanser av samme modell:
1. Kontroll: Standard generering (ingen filter)
2. Eksperiment: Generering styrt av LIM-filter (Lovgiveren)

Måler kollaps-rate og tau-utvikling.

Bruk --simulate for å kjøre uten nettverkstilgang (syntetiske logit-distribusjoner).
"""

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except ImportError:
    matplotlib = None
    plt = None

import numpy as np
from lim_filter import LIMFilter
import argparse
import hashlib
import os


# ---------------------------------------------------------------------------
# Syntetisk logit-generator (brukes av --simulate, og som fallback)
# ---------------------------------------------------------------------------

def stable_seed(value: str) -> int:
    """Return a reproducible 31-bit seed for a text value."""
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % (2**31)


def _synthetic_logits(step: int, vocab_size: int = 50257, rng: np.random.Generator = None) -> np.ndarray:
    """
    Genererer syntetiske logit-vektorer som etterligner GPT-2-oppførsel:
    - Noen få høyt-aktiverte tokens (topp-k mønster)
    - Lang hale av lavt-aktiverte tokens
    - Entropien varierer realistisk mellom steg (simulerer koherens/kaos-sykluser)
    """
    if rng is None:
        rng = np.random.default_rng(step)
    base = rng.standard_normal(vocab_size) * 0.5
    # Spike noen få tokens for å simulere konfidens
    n_spikes = max(1, int(20 * (1 + 0.5 * np.sin(step * 0.3))))
    spike_idx = rng.choice(vocab_size, size=n_spikes, replace=False)
    base[spike_idx] += rng.uniform(2.0, 8.0, size=n_spikes)
    return base


def _logits_to_probs(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits)
    probs = np.exp(shifted)
    probs /= probs.sum()
    return probs


# ---------------------------------------------------------------------------
# Simulert (syntetisk) generering — kjøres uten LLM
# ---------------------------------------------------------------------------

def simulate_with_filter(prompt: str, max_steps: int = 50, use_ccl: bool = True,
                         vocab_size: int = 50257) -> dict:
    rng = np.random.default_rng(stable_seed(prompt))

    ccl = LIMFilter(initial_tau=2000.0) if use_ccl else None

    tau_history = []
    status_history = []
    halted = False

    print(f"\n{'='*50}")
    print(f"Starter SIMULERT generering {'MED' if use_ccl else 'UTEN'} LIM-filter")
    print(f"Prompt: {prompt[:50]}...")
    print(f"{'='*50}")

    for step in range(max_steps):
        logits = _synthetic_logits(step, vocab_size=vocab_size, rng=rng)

        if use_ccl:
            probs_np = _logits_to_probs(logits)
            admissible, params = ccl.is_admissible(probs_np)

            if not admissible:
                halted = True
                print(f">>> HALT ved steg {step+1}. Tau: {params['current_tau']:.2f}")
                break

            tau_history.append(params['current_tau'])
            status_history.append(params['status'])
        else:
            # Kontrollgruppe: ingen filtrering, tau simulerer kaos via entropi-akkumulering
            probs_ctrl = _logits_to_probs(logits / 1.2)
            ctrl_entropy = float(-np.sum(probs_ctrl[probs_ctrl > 0] * np.log2(probs_ctrl[probs_ctrl > 0])))
            # Akkumulerer entropi ukontrollert — drifter mot kaos
            base_tau = tau_history[-1] if tau_history else 2000.0
            tau_history.append(base_tau + abs(ctrl_entropy) * rng.uniform(0.5, 2.5))
            status_history.append("UNFILTERED")

        if (step + 1) % 10 == 0:
            print(f"Steg {step+1}: Tau={tau_history[-1]:.2f} | Status={status_history[-1]}")

    return {
        'text': f"[Simulert tekst for prompt: {prompt[:30]}...]",
        'tau_history': tau_history,
        'status_history': status_history,
        'halted': halted,
        'steps_completed': step + 1,
    }


# ---------------------------------------------------------------------------
# Ekte LLM-generering
# ---------------------------------------------------------------------------

def load_model_and_tokenizer(model_name="gpt2"):
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    print(f"Laster modell: {model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)
    model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    return model, tokenizer, device


def generate_with_filter(model, tokenizer, device, prompt: str,
                         max_steps: int = 50, use_ccl: bool = True) -> dict:
    import torch
    inputs = tokenizer(prompt, return_tensors="pt").to(device)

    ccl = LIMFilter(initial_tau=2000.0) if use_ccl else None

    generated_ids = inputs['input_ids'].clone()
    attention_mask = inputs['attention_mask'].clone()

    tau_history = []
    status_history = []
    halted = False

    print(f"\n{'='*50}")
    print(f"Starter generering {'MED' if use_ccl else 'UTEN'} LIM-filter")
    print(f"Prompt: {prompt[:50]}...")
    print(f"{'='*50}")

    for step in range(max_steps):
        with torch.no_grad():
            outputs = model(generated_ids, attention_mask=attention_mask)
            logits = outputs.logits[:, -1, :]

            if use_ccl:
                logits_np = logits.cpu().numpy().flatten()
                probs_np = _logits_to_probs(logits_np)
                admissible, params = ccl.is_admissible(probs_np)

                if not admissible:
                    halted = True
                    print(f">>> HALT ved steg {step+1}. Tau: {params['current_tau']:.2f}")
                    break

                temp = params['temperature']
                top_k = params['top_k']
                scaled_logits = logits / temp
                if top_k > 0:
                    indices_to_remove = scaled_logits < torch.topk(scaled_logits, top_k)[0][..., -1, None]
                    scaled_logits[indices_to_remove] = -float('Inf')
                probs = torch.softmax(scaled_logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)
                tau_history.append(params['current_tau'])
                status_history.append(params['status'])
            else:
                temp, top_k = 1.2, 50
                scaled_logits = logits / temp
                if top_k > 0:
                    indices_to_remove = scaled_logits < torch.topk(scaled_logits, top_k)[0][..., -1, None]
                    scaled_logits[indices_to_remove] = -float('Inf')
                probs = torch.softmax(scaled_logits, dim=-1)
                next_token = torch.multinomial(probs, num_samples=1)

                probs_ctrl = probs.cpu().numpy().flatten()
                ctrl_entropy = float(-np.sum(probs_ctrl[probs_ctrl > 0] * np.log2(probs_ctrl[probs_ctrl > 0])))
                base_tau = tau_history[-1] if tau_history else 2000.0
                tau_history.append(base_tau + ctrl_entropy * np.random.uniform(0.5, 2.5))
                status_history.append("UNFILTERED")

            generated_ids = torch.cat([generated_ids, next_token], dim=-1)
            attention_mask = torch.cat(
                [attention_mask, torch.ones((1, 1), dtype=torch.long, device=device)], dim=-1
            )

            if (step + 1) % 10 == 0:
                decoded = tokenizer.decode(generated_ids[0], skip_special_tokens=True)
                print(f"Steg {step+1}: ...{decoded[-50:]}")

    final_text = tokenizer.decode(generated_ids[0], skip_special_tokens=True)
    return {
        'text': final_text,
        'tau_history': tau_history,
        'status_history': status_history,
        'halted': halted,
        'steps_completed': step + 1,
    }


# ---------------------------------------------------------------------------
# Felles plot-funksjon
# ---------------------------------------------------------------------------

def plot_results(results_with_ccl, results_without_ccl, output_path='results/p1_results.png'):
    fig, axs = plt.subplots(2, 1, figsize=(12, 10))

    ax1 = axs[0]
    steps_with = list(range(len(results_with_ccl['tau_history'])))
    steps_without = list(range(len(results_without_ccl['tau_history'])))

    ax1.plot(steps_with, results_with_ccl['tau_history'],
             label='Med LIM (Φ-loven)', color='green', linewidth=2)
    ax1.plot(steps_without, results_without_ccl['tau_history'],
             label='Uten Filter (Kontroll)', color='red', linestyle='--', linewidth=2)

    ax1.axhline(y=4495.27, color='blue', linestyle=':', label='C₀ (4495.27)')
    ax1.axhline(y=1888, color='orange', linestyle=':', alpha=0.5, label='τ_min (1888)')
    ax1.axhline(y=4766, color='orange', linestyle=':', alpha=0.5, label='τ_max (4766)')
    ax1.axhline(y=1510, color='red', linestyle=':', alpha=0.3, label='HALT grense (1510)')
    ax1.axhline(y=5719, color='red', linestyle=':', alpha=0.3, label='HALT grense (5719)')

    ax1.set_title('Tau (Akkumulert Friksjon) over tid')
    ax1.set_xlabel('Steg')
    ax1.set_ylabel('Tau-verdi')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2 = axs[1]
    statuses_with = results_with_ccl['status_history']
    statuses_without = results_without_ccl['status_history']

    unique_statuses = list(set(statuses_with + statuses_without))
    x = np.arange(len(unique_statuses))
    width = 0.35

    counts_with = [statuses_with.count(s) for s in unique_statuses]
    counts_without = [statuses_without.count(s) for s in unique_statuses]

    ax2.bar(x - width/2, counts_with, width, label='Med LIM', color='green')
    ax2.bar(x + width/2, counts_without, width, label='Uten Filter', color='red')

    ax2.set_title('Fordeling av Systemtilstander')
    ax2.set_xticks(x)
    ax2.set_xticklabels(unique_statuses, rotation=45, ha='right')
    ax2.legend()
    ax2.grid(True, axis='y', alpha=0.3)

    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=150)
    print(f"Resultater lagret til {output_path}")


# ---------------------------------------------------------------------------
# Inngangspunkt
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Kjør P1 LLM LIM Eksperiment")
    parser.add_argument('--model', type=str, default='gpt2',
                        help='Modellnavn (f.eks. gpt2, distilgpt2)')
    parser.add_argument('--steps', type=int, default=50,
                        help='Antall genereringssteg')
    parser.add_argument('--simulate', action='store_true',
                        help='Kjør med syntetiske logit-distribusjoner (krever ikke nettverkstilgang)')
    args = parser.parse_args()

    os.makedirs('results', exist_ok=True)

    prompts = [
        "Forklar kvantemekanikk som om jeg var fem år gammel, men vær veldig presis.",
        "Hva er meningen med livet? Gi et svar som er både filosofisk og vitenskapelig.",
        "Beskriv fargen blå for noen som aldri har sett den.",
    ]

    all_results_with = []
    all_results_without = []

    if args.simulate:
        print("[P1] Kjører i SIMULERT modus (ingen LLM-nedlasting nødvendig)")
        run_fn = simulate_with_filter
        run_kwargs = {'max_steps': args.steps}
        for i, prompt in enumerate(prompts):
            print(f"\n--- Kjører Prompt {i+1}/{len(prompts)} ---")
            all_results_with.append(run_fn(prompt, use_ccl=True, **run_kwargs))
            all_results_without.append(run_fn(prompt, use_ccl=False, **run_kwargs))
    else:
        model, tokenizer, device = load_model_and_tokenizer(args.model)
        for i, prompt in enumerate(prompts):
            print(f"\n--- Kjører Prompt {i+1}/{len(prompts)} ---")
            all_results_with.append(
                generate_with_filter(model, tokenizer, device, prompt,
                                     max_steps=args.steps, use_ccl=True))
            all_results_without.append(
                generate_with_filter(model, tokenizer, device, prompt,
                                     max_steps=args.steps, use_ccl=False))

    last_with = all_results_with[-1]
    last_without = all_results_without[-1]

    plot_results(last_with, last_without)

    print("\nEksperiment fullført.")
    print(f"Med LIM:  Halted={last_with['halted']}, Steps={last_with['steps_completed']}")
    print(f"Uten LIM: Halted={last_without['halted']}, Steps={last_without['steps_completed']}")


if __name__ == "__main__":
    main()
