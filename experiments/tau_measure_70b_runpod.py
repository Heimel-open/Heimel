"""
Tau-måling: 70B Goldilocks-test
Kjøres på RunPod A100 (40GB eller 80GB)

Installer:
  pip install transformers accelerate torch numpy

Anbefalte modeller (velg én):
  meta-llama/Meta-Llama-3-70B-Instruct   (krever HF-token)
  Qwen/Qwen3-32B                          (mellomsteg, prediksjon tau~0.543)
  Qwen/Qwen2.5-72B                        (alternativ til Llama-3 70B)
"""

import torch
import numpy as np
import math
import os
from transformers import AutoTokenizer, AutoModel

# Goldilocks-grenser
GAMMA   = 0.5772156649
ZETA3   = 1.2020569032
TAU_MIN = math.exp(-GAMMA)   # 0.5615
TAU_MAX = 1.0 / ZETA3        # 0.8319

# Sett HF_TOKEN som miljøvariabel på RunPod hvis nødvendig
HF_TOKEN = os.environ.get("HF_TOKEN", None)

TEXTS = {
    "coherent":   "The structure of a system reveals itself through the patterns it sustains over time. Coherence emerges when local rules propagate consistently across all scales of description.",
    "random":     "Quantum entropy bicycle seventeen. Mountain glass decides purple. The concept flows between adjacent memory structures. Floating decisions cascade into meaningless patterns.",
    "repetitive": "the the the the the the the the the the the the the the the the the the the the the the the the",
}

# Prediksjoner fra skaleringslov tau ~ 0.10 * N^0.48
PREDICTIONS = {
    "Qwen/Qwen3-32B":                    0.543,   # mellomsteg mot Goldilocks
    "Qwen/Qwen2.5-72B":                  0.750,   # Goldilocks-test
    "meta-llama/Meta-Llama-3-70B-Instruct": 0.750, # Goldilocks-test
}


def measure_tau(hidden: torch.Tensor) -> dict:
    H = hidden.squeeze(0).float().cpu().numpy()
    _, s, _ = np.linalg.svd(H, full_matrices=False)
    s2 = s ** 2
    p  = s2 / s2.sum()
    p  = p[p > 1e-10]
    H_sp  = -np.sum(p * np.log(p))
    r_eff = np.exp(H_sp)
    r_max = min(H.shape)
    tau   = r_eff / r_max
    return {"tau": tau, "r_eff": r_eff, "r_max": r_max}


def run_model(model_name: str):
    print(f"\n{'='*65}")
    print(f"Modell: {model_name}")
    pred = PREDICTIONS.get(model_name, None)
    if pred:
        print(f"Prediksjon (skaleringslov): tau ~ {pred:.3f}")
    print(f"{'='*65}")

    kwargs = dict(
        output_hidden_states=True,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )
    if HF_TOKEN:
        kwargs["token"] = HF_TOKEN

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True,
                                              token=HF_TOKEN)
    model = AutoModel.from_pretrained(model_name, **kwargs)
    model.eval()

    results = {}
    for label, text in TEXTS.items():
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = model(**inputs)
        r = measure_tau(outputs.hidden_states[-1])
        results[label] = r
        in_gold = TAU_MIN <= r["tau"] <= TAU_MAX
        status = "GOLDILOCKS ★" if in_gold else ("BELOW" if r["tau"] < TAU_MIN else "ABOVE")
        print(f"  [{label:>10}]  tau={r['tau']:.4f}  r_eff={r['r_eff']:.1f}/{r['r_max']}  {status}")

    tau_k = results["coherent"]["tau"]
    print(f"\n  Goldilocks [{TAU_MIN:.4f}, {TAU_MAX:.4f}]")
    if pred:
        print(f"  Avvik fra prediksjon: {abs(tau_k - pred):.4f}")
    print(f"  Koherent > tilfeldig > repetitivt: "
          f"{'JA ✓' if results['coherent']['tau'] > results['random']['tau'] > results['repetitive']['tau'] else 'NEI ✗'}")

    if TAU_MIN <= tau_k <= TAU_MAX:
        print(f"\n  *** FØRSTE MODELL I GOLDILOCKS-INTERVALLET ***")
        print(f"  Phi-lovens prediksjon bekreftet.")

    return results


if __name__ == "__main__":
    # Velg modell — 32B er billigere, 70B/72B er Goldilocks-testen
    MODEL = "Qwen/Qwen3-32B"          # mellomsteg
    # MODEL = "Qwen/Qwen2.5-72B"      # full Goldilocks-test
    # MODEL = "meta-llama/Meta-Llama-3-70B-Instruct"

    run_model(MODEL)
