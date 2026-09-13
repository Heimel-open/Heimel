"""
colab.py — Goldilocks-test (neste test)
=======================================
Måler spektral-koherens tau på ein kapabel resonneringsmodell (Qwen2.5-72B)
for å teste om han landar i Goldilocks-intervallet [e^-gamma, 1/zeta(3)]
= [0.5615, 0.8319].

Dette er keystone-målinga paperet 2026-07-09-emergent-global-workspaces-
framleis-unified.tex kviler på. Alle tidlegare målte modellar ligg UNDER
intervallet (GPT-2 0.06, Phi-2 0.16, Mistral-7B 0.26). Halvautomata-
prinsippet predikerer at fyrst ein 70B+-modell kryssar inn i Goldilocks.

  Kryssar inn  -> prediksjonen styrka.
  Blir under   -> universalitetspåstanden falsifisert, berre den
                  kontekstavhengige lesinga overlever.

Metoden (measure_tau) er IDENTISK med tau_measure_70b_runpod.py, slik at
72B-tallet er direkte samanliknbart med dei tidlegare målingane.

MASKINVARE
----------
Vi lastar ein FERDIG-KVANTISERT AWQ-sjekkpunkt (~41 GB nedlasting), ikkje full
bf16 (~145 GB). Det siste sprenger Colab-disken (No space left on device).
72B-AWQ ~ 38-40 GB VRAM -> krev A100 40GB (Colab Pro+) eller 80GB.
Gratis Colab (T4 15GB) klarer IKKJE 72B — set MODEL til 14B-AWQ-varianten då.

KØYRING I COLAB
---------------
1. Runtime -> Change runtime type -> A100 GPU
2. Lim inn heile denne fila i ei celle, køyr.
3. Skriv inn HF-token når du blir spurt (eller la stå tom for opne modellar).
"""

# ---------------------------------------------------------------------------
# 1. Avhengigheiter (Colab: dei fleste er førehandsinstallerte)
# ---------------------------------------------------------------------------
import subprocess, sys

def _pip(*pkgs):
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", *pkgs], check=False)

_pip("transformers>=4.44", "accelerate>=0.33", "bitsandbytes>=0.43",
     "autoawq>=0.2.6", "numpy")

import os, math
import numpy as np
import torch
from transformers import (AutoTokenizer, AutoModelForCausalLM,
                          BitsAndBytesConfig)

# ---------------------------------------------------------------------------
# 2. Konstantar og Goldilocks-grenser
# ---------------------------------------------------------------------------
GAMMA   = 0.5772156649
ZETA3   = 1.2020569032
TAU_MIN = math.exp(-GAMMA)   # 0.5615
TAU_MAX = 1.0 / ZETA3        # 0.8319

# Vel modell. 72B = den fulle Goldilocks-testen.
# VIKTIG: bruk ein FERDIG-KVANTISERT 4-bit-sjekkpunkt. Å laste full bf16
# (~145 GB) og kvantisere on-the-fly sprenger Colab-disken. AWQ-versjonen
# lastar berre ~41 GB og passar A100 40GB + disk.
MODEL = "Qwen/Qwen2.5-72B-Instruct-AWQ"       # ~41 GB, offisiell Qwen 4-bit
# MODEL = "Qwen/Qwen2.5-32B-Instruct-AWQ"     # mellomsteg, ~19 GB
# MODEL = "Qwen/Qwen2.5-14B-Instruct-AWQ"     # fallback, ~9 GB

PREDICTIONS = {
    "Qwen/Qwen2.5-14B-Instruct-AWQ": 0.350,
    "Qwen/Qwen2.5-32B-Instruct-AWQ": 0.543,
    "Qwen/Qwen2.5-72B-Instruct-AWQ": 0.750,   # Goldilocks-test
}

# Kjenner scriptet igjen ferdig-kvantiserte sjekkpunkt (AWQ/GPTQ/bnb-4bit)
# og hoppar over on-the-fly BitsAndBytes-kvantisering for dei.
def _is_prequantized(name: str) -> bool:
    n = name.lower()
    return any(t in n for t in ("awq", "gptq", "4bit", "int4", "int8"))

# Fleire koherente prompt gir eit stabilt hovudtal (mean +/- std),
# medan den fyrste blir rapportert åleine for samanlikning med gamle tal.
COHERENT = [
    "The structure of a system reveals itself through the patterns it sustains "
    "over time. Coherence emerges when local rules propagate consistently across "
    "all scales of description.",
    "A theorem is proved by reducing an unfamiliar statement to familiar ones, "
    "step by step, until each inference is one no reasonable reader could refuse.",
    "When a river meets a plain it slows, spreads, and deposits what it carried; "
    "the landscape downstream is written by everything that happened upstream.",
]
RANDOM = ("Quantum entropy bicycle seventeen. Mountain glass decides purple. The "
          "concept flows between adjacent memory structures. Floating decisions "
          "cascade into meaningless patterns.")
REPETITIVE = "the " * 24

# ---------------------------------------------------------------------------
# 3. Tau-måling — IDENTISK med tau_measure_70b_runpod.py
# ---------------------------------------------------------------------------
def measure_tau(hidden: torch.Tensor) -> dict:
    H = hidden.squeeze(0).float().cpu().numpy()      # [seq_len, d_model]
    _, s, _ = np.linalg.svd(H, full_matrices=False)
    s2 = s ** 2
    p  = s2 / s2.sum()
    p  = p[p > 1e-10]
    H_sp  = -np.sum(p * np.log(p))                   # spektral entropi
    r_eff = np.exp(H_sp)                             # effektiv rang
    r_max = min(H.shape)
    return {"tau": r_eff / r_max, "r_eff": r_eff, "r_max": r_max}


def status_of(tau: float) -> str:
    if TAU_MIN <= tau <= TAU_MAX:
        return "GOLDILOCKS *"
    return "BELOW" if tau < TAU_MIN else "ABOVE"


# ---------------------------------------------------------------------------
# 4. Last modell (4-bit) og mål
# ---------------------------------------------------------------------------
def run(model_name: str):
    # Qwen2.5 er open tilgang -> ingen token trengst. Sett HF_TOKEN som
    # miljovariabel berre om du byter til ein gated modell (t.d. Llama).
    hf_token = os.environ.get("HF_TOKEN") or None

    pred = PREDICTIONS.get(model_name)
    print("=" * 68)
    print(f"Modell: {model_name}")
    if pred:
        print(f"Prediksjon (skaleringslov tau ~ 0.10*N^0.48): tau ~ {pred:.3f}")
    print(f"Goldilocks: [{TAU_MIN:.4f}, {TAU_MAX:.4f}]")
    print("=" * 68)

    tok = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True,
                                        token=hf_token)

    load_kwargs = dict(
        device_map="auto", trust_remote_code=True,
        output_hidden_states=True, token=hf_token,
    )
    if _is_prequantized(model_name):
        # Kvantiseringa ligg alt i sjekkpunktet (config.json). Ikkje send ny
        # quant-config. Berre last ned ~41 GB og legg rett i VRAM.
        print("  (ferdig-kvantisert sjekkpunkt — lastar 4-bit direkte)")
        load_kwargs["torch_dtype"] = torch.float16
    else:
        # Full-presisjons modell -> kvantiser on-the-fly. NB: krev at heile
        # bf16-vekta fyrst lastast til disk (kan sprenge Colab for 70B+).
        load_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
        )
    model = AutoModelForCausalLM.from_pretrained(model_name, **load_kwargs)
    model.eval()

    def tau_of(text: str) -> dict:
        inp = tok(text, return_tensors="pt", truncation=True, max_length=512)
        inp = {k: v.to(model.device) for k, v in inp.items()}
        with torch.no_grad():
            out = model(**inp)
        return measure_tau(out.hidden_states[-1])

    # Koherente
    coh = [tau_of(t) for t in COHERENT]
    coh_tau = np.array([r["tau"] for r in coh])
    head = coh[0]                                   # samanliknbar med gamle tal
    ran  = tau_of(RANDOM)
    rep  = tau_of(REPETITIVE)

    print(f"\n  [coherent #1 ]  tau={head['tau']:.4f}  "
          f"r_eff={head['r_eff']:.1f}/{head['r_max']}   {status_of(head['tau'])}")
    print(f"  [coherent avg]  tau={coh_tau.mean():.4f} +/- {coh_tau.std():.4f}  "
          f"(n={len(coh_tau)})   {status_of(coh_tau.mean())}")
    print(f"  [random      ]  tau={ran['tau']:.4f}   {status_of(ran['tau'])}")
    print(f"  [repetitive  ]  tau={rep['tau']:.4f}   {status_of(rep['tau'])}")

    ordered = head["tau"] > ran["tau"] > rep["tau"]
    print(f"\n  Koherent > tilfeldig > repetitivt: {'JA' if ordered else 'NEI'}")
    if pred:
        print(f"  Avvik frå prediksjon: {abs(head['tau'] - pred):.4f}")

    print("\n" + "-" * 68)
    if TAU_MIN <= coh_tau.mean() <= TAU_MAX:
        print("  RESULTAT: I GOLDILOCKS. Framleis-prediksjonen er STYRKA.")
        print("  Fyrste målte modell innanfor [e^-gamma, 1/zeta(3)].")
    elif coh_tau.mean() < TAU_MIN:
        print("  RESULTAT: UNDER GOLDILOCKS. Universalitetspåstanden er")
        print("  FALSIFISERT for denne modellen — berre den kontekstavhengige")
        print("  (halvautomata) lesinga overlever.")
    else:
        print("  RESULTAT: OVER GOLDILOCKS. Uventa — sjekk sekvenslengd/normalisering.")
    print("-" * 68)

    # Alt kasta til rein Python-type -> JSON-serialiserbart (unngå float32-feil).
    return {"model": model_name, "coherent_mean": float(coh_tau.mean()),
            "coherent_std": float(coh_tau.std()),
            "coherent_head": float(head["tau"]),
            "random": float(ran["tau"]), "repetitive": float(rep["tau"]),
            "in_goldilocks": bool(TAU_MIN <= coh_tau.mean() <= TAU_MAX),
            "ordered": bool(ordered)}


if __name__ == "__main__":
    import json
    result = run(MODEL)
    print("\n" + json.dumps(result, indent=2))
