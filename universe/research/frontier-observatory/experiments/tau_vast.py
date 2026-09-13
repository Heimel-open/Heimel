#!/usr/bin/env python3
"""
tau_vast.py — Tau-måling for Qwen2.5-familien på Vast.ai / RunPod A100

Køyr:
  pip install transformers accelerate bitsandbytes torch numpy
  python tau_vast.py [--models 7b 14b 32b 72b]

Standard: køyrer alle fire storleikar i rekkefølge.
Resultat lagra til tau_results.json.

VRAM-krav (4-bit):
  7B  ~  5 GB   →  T4 held
  14B ~ 10 GB   →  T4 held
  32B ~ 18 GB   →  A100 40GB held
  72B ~ 40 GB   →  A100 80GB (passer knappast på 40GB)
"""

import argparse
import json
import math
import sys
import time
from datetime import datetime

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

# ---------------------------------------------------------------------------
# Goldilocks-grenser
# ---------------------------------------------------------------------------
GAMMA   = 0.5772156649
ZETA3   = 1.2020569032
TAU_MIN = math.exp(-GAMMA)   # 0.5615
TAU_MAX = 1.0 / ZETA3        # 0.8319

# ---------------------------------------------------------------------------
# Teststekstar — same som i alle tidlegare målingar for samanliknbarheit
# ---------------------------------------------------------------------------
TEXTS = {
    "coherent":   (
        "The structure of a system reveals itself through the patterns it sustains "
        "over time. Coherence emerges when local rules propagate consistently across "
        "all scales."
    ),
    "random":     (
        "Quantum entropy bicycle seventeen. Mountain glass decides purple. "
        "The concept flows between adjacent memory structures. Floating decisions cascade."
    ),
    "repetitive": "the " * 24,
}

# ---------------------------------------------------------------------------
# Modellar
# ---------------------------------------------------------------------------
MODELS = {
    "7b":  "Qwen/Qwen2.5-7B",
    "14b": "Qwen/Qwen2.5-14B",
    "32b": "Qwen/Qwen2.5-32B",
    "72b": "Qwen/Qwen2.5-72B",
}


def measure_tau(hidden: torch.Tensor) -> dict:
    """
    tau = r_eff / r_max
    r_eff = exp(H_sp),  H_sp = -sum(p_i * ln(p_i))
    p_i   = s_i^2 / sum(s_j^2)   (SVD singular values of hidden state matrix)
    """
    H = hidden.squeeze(0).float().cpu().numpy()  # (seq_len, hidden_dim)
    _, s, _ = np.linalg.svd(H, full_matrices=False)
    s2   = s ** 2
    p    = s2 / s2.sum()
    p    = p[p > 1e-10]
    H_sp = -np.sum(p * np.log(p))
    r_eff = np.exp(H_sp)
    r_max = min(H.shape)
    tau   = r_eff / r_max
    return {
        "tau":   float(tau),
        "r_eff": float(r_eff),
        "r_max": int(r_max),
        "H_sp":  float(H_sp),
    }


def run_model(size_key: str) -> dict:
    model_name = MODELS[size_key]
    print(f"\n{'='*64}")
    print(f"  {model_name}")
    print(f"{'='*64}")

    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModel.from_pretrained(
        model_name,
        output_hidden_states=True,
        trust_remote_code=True,
        torch_dtype=torch.float16,
        device_map="auto",
        load_in_4bit=True,
    )
    model.eval()
    load_time = time.time() - t0
    print(f"  Last inn: {load_time:.1f}s")

    results = {}
    for label, text in TEXTS.items():
        inputs = tokenizer(
            text, return_tensors="pt", truncation=True, max_length=256
        )
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = model(**inputs)
        r = measure_tau(outputs.hidden_states[-1])
        results[label] = r
        zone = (
            "GOLDILOCKS" if TAU_MIN <= r["tau"] <= TAU_MAX
            else "BELOW" if r["tau"] < TAU_MIN
            else "ABOVE"
        )
        print(
            f"  [{label:>10}]  tau={r['tau']:.4f}"
            f"  r_eff={r['r_eff']:.1f}/{r['r_max']}"
            f"  {zone}"
        )

    ordering_ok = (
        results["coherent"]["tau"]
        > results["random"]["tau"]
        > results["repetitive"]["tau"]
    )
    print(f"  Goldilocks [{TAU_MIN:.4f}, {TAU_MAX:.4f}]")
    print(f"  Rekkefølge koherent > tilfeldig > repetitivt: {'JA' if ordering_ok else 'NEI'}")

    # Frigjere VRAM mellom modellar
    del model
    torch.cuda.empty_cache()

    return {
        "model":      model_name,
        "size_key":   size_key,
        "load_time_s": round(load_time, 1),
        "ordering_ok": ordering_ok,
        "results":    results,
    }


def print_summary(all_results: dict) -> None:
    print(f"\n{'='*64}")
    print("SAMMENDRAG")
    print(f"{'='*64}")
    header = f"{'Modell':<16} {'tau(koherent)':<16} {'tau(random)':<14} {'tau(repetitiv)':<16} {'Rekkefølge'}"
    print(header)
    print("-" * 80)
    for key, data in all_results.items():
        r = data["results"]
        print(
            f"{key:<16}"
            f" {r['coherent']['tau']:<16.4f}"
            f" {r['random']['tau']:<14.4f}"
            f" {r['repetitive']['tau']:<16.4f}"
            f" {'JA' if data['ordering_ok'] else 'NEI'}"
        )
    print(f"\nGoldilocks: [{TAU_MIN:.4f}, {TAU_MAX:.4f}]")
    print("\nEksisterande målingar (samanlikning):")
    kjente = {
        "GPT-2 (117M)":  0.060,
        "Phi-2 (2.7B)":  0.163,
        "Mistral-7B":    0.257,
    }
    for namn, tau in kjente.items():
        print(f"  {namn:<20}  tau={tau:.4f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Tau-måling Qwen2.5 på Vast.ai/RunPod")
    parser.add_argument(
        "--models",
        nargs="+",
        choices=["7b", "14b", "32b", "72b"],
        default=["7b", "14b", "32b", "72b"],
        help="Kva modellar som skal målast (standard: alle fire)",
    )
    args = parser.parse_args()

    print(f"Tau-måling Qwen2.5 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"CUDA: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'IKKJE TILGJENGELEG'}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB" if torch.cuda.is_available() else "")
    print(f"Modellar: {args.models}")

    all_results = {}
    for size_key in args.models:
        try:
            all_results[size_key] = run_model(size_key)
        except torch.cuda.OutOfMemoryError:
            print(f"\n  OOM: {MODELS[size_key]} passar ikkje i VRAM — hoppar over")
        except Exception as exc:
            print(f"\n  FEIL ved {MODELS[size_key]}: {exc}")

    print_summary(all_results)

    out_file = f"tau_results_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(out_file, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResultat lagra: {out_file}")


if __name__ == "__main__":
    main()
