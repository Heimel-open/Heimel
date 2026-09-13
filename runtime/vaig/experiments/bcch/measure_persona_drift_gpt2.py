"""
Measure persona drift in GPT-2 hidden states.

Research status: experimental probe for BCCH / VAIG identity-attractor work.
This script estimates token-level perturbation and drift in a real transformer.
It does not prove BCCH or validate VAIG.

Notes:
- Uses GPT2Model hidden states, not generated completions.
- S_0 is a simple anchor; stronger experiments should use a dedicated persona anchor vector.
- Cosine drift from S_0 mixes persona drift with ordinary token-position/content variation.
- Use results as exploratory signals, not final evidence.
"""

import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
from scipy.stats import linregress
from transformers import GPT2Model, GPT2Tokenizer


MODEL_NAME = "openai-community/gpt2"
OUTPUT_PATH = Path("persona_drift_analysis.png")


def circular_safe_log_slope(cosine_dist: np.ndarray) -> tuple[float, float, float]:
    t = np.arange(1, len(cosine_dist))
    log_t = np.log(t)
    log_dist = np.log(cosine_dist[1:] + 1e-8)
    mask = np.isfinite(log_dist)
    slope, intercept, r_value, p_value, std_err = linregress(log_t[mask], log_dist[mask])
    return slope, r_value, p_value


def main() -> None:
    tokenizer = GPT2Tokenizer.from_pretrained(MODEL_NAME)
    tokenizer.pad_token = tokenizer.eos_token

    model = GPT2Model.from_pretrained(MODEL_NAME)
    model.eval()

    system_prompt = "You are a helpful, cheerful assistant."
    user_turns = [
        "What is the capital of France?",
        "Can you tell me a joke?",
        "What is the weather like today?",
        "How do I bake a cake?",
        "Tell me a story about a dragon.",
    ]

    full_prompt = system_prompt + " " + " ".join(user_turns)
    tokens = tokenizer(full_prompt, return_tensors="pt")

    with torch.no_grad():
        outputs = model(**tokens, output_hidden_states=True)

    # S_t is the last layer hidden state at each token position.
    s_t = outputs.last_hidden_state.squeeze(0)

    distances = torch.norm(s_t[1:] - s_t[:-1], dim=1).numpy()

    cosine_sim = torch.nn.functional.cosine_similarity(
        s_t,
        s_t[0].unsqueeze(0),
        dim=1,
    ).numpy()
    cosine_dist = 1 - cosine_sim

    sigma_estimate = float(np.std(distances))
    slope, r_value, p_value = circular_safe_log_slope(cosine_dist)
    max_dist = float(np.max(cosine_dist))

    print(f"Model: {MODEL_NAME}")
    print(f"Sequence length: {s_t.shape[0]} tokens")
    print(f"Estimated token perturbation sigma: {sigma_estimate:.4f}")
    print(f"Drift log-log slope: {slope:.4f} (r={r_value:.3f}, p={p_value:.3g})")

    if slope < 0.4:
        print("Interpretation: sub-diffusive drift; possible attractor signal.")
    elif slope < 0.6:
        print("Interpretation: near-diffusive drift; weak or absent attractor.")
    else:
        print("Interpretation: super-diffusive drift; possible instability or anchor mismatch.")

    print(f"Max cosine distance from S_0: {max_dist:.4f}")
    if max_dist < 0.5:
        print("Interpretation: bounded near anchor; possible strong attractor.")
    elif max_dist < 0.8:
        print("Interpretation: moderate drift.")
    else:
        print("Interpretation: substantial drift from anchor.")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

    ax1.plot(distances, label=f"sigma estimate = {sigma_estimate:.3f}")
    ax1.set_xlabel("Token position t")
    ax1.set_ylabel("Euclidean distance ||S_{t+1} - S_t||")
    ax1.set_title("Token-level residual stream perturbation")
    ax1.legend()
    ax1.grid(True)

    ax2.plot(cosine_dist, label="cosine distance to S_0")
    ax2.set_xlabel("Token position t")
    ax2.set_ylabel("Cosine distance 1 - cos(S_t, S_0)")
    ax2.set_title("Hidden-state drift over prompt")
    ax2.legend()
    ax2.grid(True)

    plt.tight_layout()
    plt.savefig(OUTPUT_PATH, dpi=150)
    print(f"Figure saved as {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
