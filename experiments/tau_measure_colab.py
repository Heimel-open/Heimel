"""
Tau-måling: Qwen2.5-7B og Qwen3-8B
Kjøres på Colab T4 (gratis tier holder for 7B/8B med 4-bit quantization)

Installer:
  pip install transformers accelerate bitsandbytes torch numpy
"""

import torch
import numpy as np
import math
from transformers import AutoTokenizer, AutoModel

# Goldilocks-grenser
GAMMA  = 0.5772156649
ZETA3  = 1.2020569032
TAU_MIN = math.exp(-GAMMA)
TAU_MAX = 1.0 / ZETA3

TEXTS = {
    "coherent":   "The structure of a system reveals itself through the patterns it sustains over time. Coherence emerges when local rules propagate consistently across all scales.",
    "random":     "Quantum entropy bicycle seventeen. Mountain glass decides purple. The concept flows between adjacent memory structures. Floating decisions cascade.",
    "repetitive": "the the the the the the the the the the the the the the the the the the the the the the the the",
}


def measure_tau(hidden: torch.Tensor) -> dict:
    """
    tau = r_eff / r_max
    r_eff = exp(H_spectral), H_spectral = -sum(p_i * ln(p_i))
    p_i = s_i^2 / sum(s_j^2)  over SVD singular values of hidden state matrix
    """
    H = hidden.squeeze(0).float().cpu().numpy()   # (seq_len, hidden_dim)
    _, s, _ = np.linalg.svd(H, full_matrices=False)
    s2 = s ** 2
    p  = s2 / s2.sum()
    p  = p[p > 1e-10]
    H_sp  = -np.sum(p * np.log(p))
    r_eff = np.exp(H_sp)
    r_max = min(H.shape)
    tau   = r_eff / r_max
    return {"tau": tau, "r_eff": r_eff, "r_max": r_max, "H_sp": H_sp}


def run_model(model_name: str):
    print(f"\n{'='*60}")
    print(f"Modell: {model_name}")
    print(f"{'='*60}")

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModel.from_pretrained(
        model_name,
        output_hidden_states=True,
        trust_remote_code=True,
        torch_dtype=torch.float16,
        device_map="auto",
        load_in_4bit=True,       # 4-bit quantization — T4 holder
    )
    model.eval()

    results = {}
    for label, text in TEXTS.items():
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = model(**inputs)
        last_hidden = outputs.hidden_states[-1]
        r = measure_tau(last_hidden)
        results[label] = r
        status = ("GOLDILOCKS" if TAU_MIN <= r["tau"] <= TAU_MAX
                  else "BELOW" if r["tau"] < TAU_MIN else "ABOVE")
        print(f"  [{label:>10}]  tau={r['tau']:.4f}  r_eff={r['r_eff']:.1f}/{r['r_max']}  {status}")

    print(f"\n  Goldilocks [{TAU_MIN:.4f}, {TAU_MAX:.4f}]")
    print(f"  Rekkefølge koherent > tilfeldig > repetitivt: "
          f"{'JA' if results['coherent']['tau'] > results['random']['tau'] > results['repetitive']['tau'] else 'NEI'}")
    return results


if __name__ == "__main__":
    alle_resultater = {}

    # Test 1: Replikasjon — samme parameterklasse som Mistral-7B (0.2568)
    # MERK: Formelen tau ~ 0.10 * N^0.48 er FALSIFISERT for entropi-basert tau
    # (gir verdiar 745-5316 i staden for 0-1). Bruk berre som historisk referanse.
    # Prediksjon: tau ~ 0.10 * 7^0.48 = 0.254  [UGYLDIG — sjå master v1.3]
    alle_resultater["Qwen2.5-7B"] = run_model("Qwen/Qwen2.5-7B")

    # Test 2: Arkitektur — dual-mode thinking, prediksjon tau ~ 0.271
    alle_resultater["Qwen3-8B"] = run_model("Qwen/Qwen3-8B")

    print(f"\n{'='*60}")
    print("SAMMENDRAG")
    print(f"{'='*60}")
    print(f"{'Modell':<20} {'tau (koherent)':<18} {'Prediksjon':<12} {'Avvik'}")
    print("-"*60)
    forventede = {"Qwen2.5-7B": 0.254, "Qwen3-8B": 0.271}
    for navn, res in alle_resultater.items():
        tau_k = res["coherent"]["tau"]
        pred  = forventede[navn]
        print(f"{navn:<20} {tau_k:<18.4f} {pred:<12.3f} {abs(tau_k-pred):.4f}")
