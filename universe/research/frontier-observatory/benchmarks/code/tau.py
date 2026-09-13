"""
tau.py — Reference implementation of the τ coherence metric.

Spec: tau/spec/tau_specification_v1.md
Version: 1.0 (draft)

τ = 1 - H_norm(S(h))
where h is the hidden state at a given layer and S is the singular value spectrum.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

import numpy as np


@dataclass
class TauResult:
    tau: float
    H: float
    H_norm: float
    n_singular_values: int
    model_id: str
    layer_index: int
    seq_len: int
    hidden_dim: int

    def to_dict(self) -> dict:
        return {
            "tau": round(self.tau, 6),
            "H": round(self.H, 6),
            "H_norm": round(self.H_norm, 6),
            "n_singular_values": self.n_singular_values,
            "model_id": self.model_id,
            "layer_index": self.layer_index,
            "seq_len": self.seq_len,
            "hidden_dim": self.hidden_dim,
        }


def compute_tau_from_hidden(
    hidden: np.ndarray,
    model_id: str = "unknown",
    layer_index: int = -1,
) -> TauResult:
    """
    Compute τ from a hidden state matrix.

    Args:
        hidden: shape [seq_len, hidden_dim] — hidden state at one layer
        model_id: identifier for the model (logging only)
        layer_index: which layer was used (logging only)

    Returns:
        TauResult with tau in [0, 1]
    """
    seq_len, hidden_dim = hidden.shape
    n = min(seq_len, hidden_dim)

    # SVD — singular values only (full_matrices=False for efficiency)
    singular_values = np.linalg.svd(hidden, compute_uv=False)  # shape [n]

    # Normalized squared singular values (probability distribution over spectrum)
    lambda_vals = singular_values**2
    total = lambda_vals.sum()
    if total == 0:
        # Zero matrix — undefined coherence; return 0
        return TauResult(
            tau=0.0, H=0.0, H_norm=0.0,
            n_singular_values=n, model_id=model_id,
            layer_index=layer_index, seq_len=seq_len, hidden_dim=hidden_dim,
        )

    lambda_vals = lambda_vals / total  # normalize to sum to 1

    # Spectral entropy (nats); avoid log(0)
    mask = lambda_vals > 0
    H = -np.sum(lambda_vals[mask] * np.log(lambda_vals[mask]))

    # Normalize by log(n) — maximum possible entropy
    log_n = np.log(n)
    H_norm = H / log_n if log_n > 0 else 0.0

    # τ = 1 - normalized entropy; clamp to [0, 1] for floating-point safety
    tau = float(np.clip(1.0 - H_norm, 0.0, 1.0))

    return TauResult(
        tau=tau, H=float(H), H_norm=float(H_norm),
        n_singular_values=n, model_id=model_id,
        layer_index=layer_index, seq_len=seq_len, hidden_dim=hidden_dim,
    )


def compute_tau(
    model_id: str,
    prompt: str,
    layer_index: int = -1,
    max_length: int = 128,
) -> TauResult:
    """
    Compute τ for a prompt using a HuggingFace model.

    Requires: torch, transformers
    """
    try:
        import torch
        from transformers import AutoModel, AutoTokenizer
    except ImportError as e:
        raise ImportError(
            "torch and transformers are required. "
            "Install with: pip install torch transformers"
        ) from e

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModel.from_pretrained(model_id, output_hidden_states=True)
    model.eval()

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=max_length,
    )

    with torch.no_grad():
        outputs = model(**inputs)

    hidden_states = outputs.hidden_states  # tuple of [1, seq_len, hidden_dim]
    hidden = hidden_states[layer_index][0].cpu().numpy()  # [seq_len, hidden_dim]

    return compute_tau_from_hidden(hidden, model_id=model_id, layer_index=layer_index)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute τ coherence metric for an LLM")
    parser.add_argument("--model", required=True, help="HuggingFace model ID")
    parser.add_argument("--prompt", required=True, help="Input text")
    parser.add_argument("--layer", type=int, default=-1, help="Layer index (default: -1 = last)")
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    result = compute_tau(
        model_id=args.model,
        prompt=args.prompt,
        layer_index=args.layer,
        max_length=args.max_length,
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"τ = {result.tau:.4f}  (H={result.H:.4f}, H_norm={result.H_norm:.4f})")
        print(f"model={result.model_id}, layer={result.layer_index}, "
              f"seq_len={result.seq_len}, hidden_dim={result.hidden_dim}")


if __name__ == "__main__":
    main()
