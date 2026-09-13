#!/usr/bin/env python3
"""
P1-PROTOKOLL: K-idempotens eksperiment (KORRIGERT)

Innsikt: K er Lovgiverens strukturelle kapasitet — den malles fra VEKT-matriser,
ikke hidden states. Hidden states er Tolken (transient, adaptiv). Vektmatriser
er Lovgiveren (invariant, frossen).

K = sum( H(W) ) over alle vektmatriser W
H(W) = -sum( p_i * log2(p_i) ) der p_i = sigma_i / sum(sigma_j)
C0 = rho * K  (rho = gamma/(delta-4) = 0.86254...)

Avgjørende test:
    python p1_final_corrected.py --model gpt2 --output p1_gpt2.json
    python p1_final_corrected.py --model meta-llama/Llama-3.2-3B-Instruct --output p1_llama.json

Forutsetninger:
    pip install transformers torch scipy
"""

import argparse
import math
import time
import json
from pathlib import Path

import numpy as np
import torch


# =============================================================================
# LIM-FILTER (Phi-lloven)
# =============================================================================

class LIMFilter:
    """Law of Identity Maintenance Filter"""
    
    def __init__(self, alpha=0.42, gamma=0.5772156649, delta=4.6692016091, zeta3=1.2020569032):
        self.alpha = alpha
        self.gamma = gamma
        self.delta = delta
        self.zeta3 = zeta3
        
        # Dimensjonslose grenser
        self.tau_min_dimless = math.exp(-gamma)   # 0.5615...
        self.tau_max_dimless = 1.0 / zeta3         # 0.8319...
        
        # Rho: konverteringsfaktor
        self.rho = gamma / (delta - 4)  # 0.8625437492...
    
    def compute_tau(self, hidden_states):
        """Beregn tau fra hidden states (Tolken — transient maling)."""
        batch_size, seq_len, hidden_dim = hidden_states.shape
        states_flat = hidden_states.reshape(-1, hidden_dim)
        states_centered = states_flat - states_flat.mean(dim=0)
        L = torch.mm(states_centered.T, states_centered) / seq_len
        L = L + 1e-6 * torch.eye(hidden_dim, device=L.device)
        eigenvalues = torch.linalg.eigvalsh(L)
        eigenvalues = eigenvalues[eigenvalues > 0]
        total_energy = torch.sum(eigenvalues)
        probabilities = eigenvalues / total_energy
        probabilities = probabilities[probabilities > 1e-10]
        tau_bits = -torch.sum(probabilities * torch.log2(probabilities))
        return tau_bits.item(), eigenvalues.numpy()
    
    def compute_spectral_entropy(self, W):
        """
        Beregn spektral entropi av en vektmatrise.
        
        Operasjon: SVD -> normaliser singulaer verdier -> Shannon entropi.
        Dette er informasjonsinnholdet kodet i W's struktur.
        """
        if W is None or W.numel() == 0:
            return 0.0, 0
        
        try:
            Wf = W.float()
            min_d = min(Wf.shape)
            
            if min_d > 2048:
                _, S, _ = torch.svd_lowrank(Wf, q=min(512, min_d))
            else:
                _, S, _ = torch.linalg.svd(Wf, full_matrices=False)
            
            s = S.detach().cpu().numpy()
            s = s[s > 1e-10]
            
            if len(s) == 0:
                return 0.0, 0
            
            p = s / np.sum(s)
            H = float(-np.sum(p * np.log2(p + 1e-10)))
            return H, len(s)
            
        except Exception:
            return 0.0, 0
    
    def compute_K_from_weights(self, model):
        """
        Beregn K fra ALLE vektmatriser i modellen.
        
        K = sum( H(W) ) over alle vektmatriser W
        
        H(W) er spektral entropien — informasjonen kodet i W's struktur.
        Summen over alle W gir Lovgiverens totale strukturelle kapasitet.
        """
        K_total = 0.0
        details = []
        
        for name, param in model.named_parameters():
            # Bare vektmatriser (2D+), ikke bias, LayerNorm, etc.
            if param.requires_grad and len(param.shape) >= 2 and param.shape[0] > 1 and param.shape[1] > 1:
                H, num_sv = self.compute_spectral_entropy(param.detach())
                if H > 0:
                    K_total += H
                    details.append({
                        'name': name,
                        'shape': list(param.shape),
                        'entropy': H,
                        'num_sv': num_sv,
                    })
        
        return K_total, details


# =============================================================================
# P1-PROTOKOLL
# =============================================================================

class P1Protocol:
    """P1: Coherence Measurement Protocol (KORRIGERT)"""
    
    def __init__(self, model_name, device=None):
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_name = model_name
        
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
        print(f"[P1] Laster {model_name}...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float32,
            device_map=self.device,
            trust_remote_code=True,
            output_hidden_states=True,
        )
        self.model.eval()
        
        self.config = self.model.config
        self.lim = LIMFilter()
        
        self.hidden_dim = self.config.hidden_size
        self.num_layers = self.config.num_hidden_layers
        self.num_heads = getattr(self.config, 'num_attention_heads', 'N/A')
        
        print(f"       Loaded: {sum(p.numel() for p in self.model.parameters())/1e6:.1f}M params")
    
    def run(self, num_samples=20):
        """
        Kjor det komplette P1-eksperimentet.
        
        K MALLES fra vektmatriser (Lovgiveren, invariant).
        tau MALLES fra hidden states (Tolken, transient).
        C0 = rho * K (likevektspunktet).
        """
        print(f"\n{'='*70}")
        print(f"P1 EKSPERIMENT: {self.model_name}")
        print(f"{'='*70}\n")
        
        # --- Steg 1: K fra vektmatriser (Lovgiveren) ---
        print("[1/3] Beregner K fra vektmatriser...")
        K, K_details = self.lim.compute_K_from_weights(self.model)
        print(f"       K = {K:.4f}")
        print(f"       Vektmatriser analysert: {len(K_details)}")
        print(f"       Gj.snitt H per matrise: {K/len(K_details) if K_details else 0:.4f}")
        
        # Vis topp 5 største bidrag
        top5 = sorted(K_details, key=lambda x: x['entropy'], reverse=True)[:5]
        print(f"       Top 5 bidrag:")
        for d in top5:
            print(f"         {d['name']}: {d['entropy']:.4f} bits")
        
        # --- Steg 2: C0 = rho * K ---
        C0 = self.lim.rho * K
        print(f"\n[2/3] C0 = rho * K = {C0:.4f} bits")
        
        # --- Steg 3: tau fra hidden states (Tolken) ---
        print(f"[3/3] Maling tau fra hidden states...")
        seed_text = "The coherence of a system is determined by its ability to maintain identity through constrained boundaries."
        
        tau_values = []
        for i in range(num_samples):
            text = (seed_text * (256 // len(seed_text) + 1))[:256]
            inputs = self.tokenizer(text, return_tensors='pt', truncation=True, max_length=256)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = self.model(**inputs, output_hidden_states=True)
            
            last_hidden = outputs.hidden_states[-1]
            tau, _ = self.lim.compute_tau(last_hidden)
            tau_values.append(tau)
        
        tau_median = float(np.median(tau_values))
        tau_mean = float(np.mean(tau_values))
        tau_std = float(np.std(tau_values))
        
        print(f"       tau (median) = {tau_median:.4f} bits")
        print(f"       tau (mean)   = {tau_mean:.4f} +/- {tau_std:.4f}")
        
        # --- Stabilitetssjekk ---
        tau_min = C0 * self.lim.tau_min_dimless
        tau_max = C0 * self.lim.tau_max_dimless
        in_zone = tau_min <= tau_median <= tau_max
        state = 'COHERENCE' if in_zone else ('CHAOS' if tau_median < tau_min else 'STASIS')
        
        print(f"\n--- Stabilitet ---")
        print(f"       C0 = {C0:.4f}")
        print(f"       Zone: [{tau_min:.4f}, {tau_max:.4f}]")
        print(f"       tau median i zone: {in_zone}")
        print(f"       Tilstand: {state}")
        
        # --- Resultater ---
        results = {
            'model': self.model_name,
            'timestamp': time.strftime("%Y-%m-%dT%H:%M:%S"),
            'architecture': {
                'hidden_dim': self.hidden_dim,
                'num_layers': self.num_layers,
                'num_heads': self.num_heads,
            },
            'K': {
                'value': float(K),
                'num_matrices': len(K_details),
                'top_contributors': [{k: v for k, v in d.items() if k != 'name' or True} 
                                      for d in top5],
            },
            'C0': float(C0),
            'rho': self.lim.rho,
            'tau': {
                'median': tau_median,
                'mean': tau_mean,
                'std': tau_std,
            },
            'stability': {
                'in_zone': in_zone,
                'state': state,
                'tau_min': float(tau_min),
                'tau_max': float(tau_max),
            },
        }
        
        return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, default='gpt2')
    parser.add_argument('--samples', type=int, default=20)
    parser.add_argument('--output', type=str, default='p1_result.json')
    parser.add_argument('--device', type=str, default=None)
    args = parser.parse_args()
    
    p1 = P1Protocol(args.model, device=args.device)
    results = p1.run(num_samples=args.samples)
    
    # --- Sammenligning med baseline ---
    print(f"\n{'='*70}")
    print(f"SAMMENLIGNING")
    print(f"{'='*70}")
    
    GPT2_C0 = 4495.27  # Observert baseline
    our_C0 = results['C0']
    ratio = our_C0 / GPT2_C0
    hidden_ratio = results['architecture']['hidden_dim'] / 768
    
    print(f"  GPT-2 baseline C0: {GPT2_C0:.2f}")
    print(f"  {args.model} C0:     {our_C0:.2f}")
    print(f"  Forhold:           {ratio:.4f}x")
    print(f"  Hidden dim ratio:  {hidden_ratio:.4f}x")
    
    if abs(ratio - 1.0) < 0.15:
        print(f"\n  >>> ALT 2: C0 stabil! K er SUBSTRATUAVHENGIG!")
        results['verdict'] = 'ALT_2_UNIVERSAL'
    elif abs(ratio - hidden_ratio) / hidden_ratio < 0.25:
        print(f"\n  >>> ALT 1: C0 skalerer med hidden_dim!")
        results['verdict'] = 'ALT_1_ARCHITECTURE'
    else:
        print(f"\n  >>> Kompleks skalering - trenger flere modeller")
        results['verdict'] = 'UNCLEAR'
    
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nLagret: {args.output}")


if __name__ == "__main__":
    main()
