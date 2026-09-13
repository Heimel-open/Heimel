"""
lim_filter.py - Implementasjon av Φ-lovens LIM-filter for LLM-er

Prinsipp:
Et selv-konsistent filter må være idempotent.
Filteret regulerer systemets "temperatur" og "top-k" basert på
akkumulert friksjon (tau) for å holde systemet i koherens-sonen [1888, 4766].

Konstanter fra Φ-loven:
- C_0 = 4495.27 (Likevektspunkt)
- alpha_target = 0.42 (Optimal glemselsrate)
- tau_min = 1888
- tau_max = 4766
"""

import numpy as np
import math
from typing import List, Tuple, Dict

class LIMFilter:
    def __init__(self, initial_tau: float = 0.0):
        """
        Initialiserer LIM-filteret.
        """
        self.tau = initial_tau
        self.C_0 = 4495.27
        self.alpha_target = 0.42
        self.tau_min = 1888.0
        self.tau_max = 4766.0

        self.prev_entropy = 0.0
        self.step_count = 0

        print(f"[LIM] Filter aktivert. Mål: C_0={self.C_0}, Alpha={self.alpha_target}")

    def calculate_entropy(self, token_probs) -> float:
        """
        Beregner Shannon-entropi for en gitt sannsynlighetsfordeling.
        H = - sum(p * log2(p))
        """
        arr = np.asarray(token_probs, dtype=np.float64)
        mask = arr > 0
        return float(-np.sum(arr[mask] * np.log2(arr[mask])))

    def update_tau(self, current_entropy: float) -> float:
        """
        Oppdaterer tau (akkumulert friksjon/entropi-endring).
        Tau øker når entropien endrer seg raskt (støy/kaos).
        """
        delta_h = abs(current_entropy - self.prev_entropy)
        self.tau += delta_h
        self.prev_entropy = current_entropy
        self.step_count += 1
        return self.tau

    def get_admissibility_params(self) -> Dict[str, float]:
        """
        Beregner de tillatte parameterne for neste generering (Temperatur og Top-K)
        basert på nåværende tau og avvik fra C_0.

        Dette er selve "Lovgiveren".
        """
        deviation = self.tau - self.C_0
        base_temp = 0.5

        if self.tau < self.tau_min:
            # KAOS: Stram inn. Lav temperatur, streng top-k.
            adjusted_temp = max(0.1, base_temp - (abs(deviation) / 1000))
            top_k = 10
            status = "KAOS_DETECTED"
        elif self.tau > self.tau_max:
            # STASIS: Løs opp. Høyere temperatur, bredere top-k.
            adjusted_temp = min(1.2, base_temp + (abs(deviation) / 1000))
            top_k = 100
            status = "STASIS_DETECTED"
        else:
            # KOHERENS: Hold balansen.
            adjusted_temp = base_temp
            top_k = 50
            status = "COHERENT"

        damping_factor = self.alpha_target
        final_temp = adjusted_temp * damping_factor

        return {
            "temperature": final_temp,
            "top_k": top_k,
            "status": status,
            "current_tau": self.tau,
            "deviation_from_C0": deviation
        }

    def is_admissible(self, token_probs: List[float]) -> Tuple[bool, Dict]:
        """
        Sjekk om output er tillatt (admissible).
        Returnerer True hvis systemet er innenfor sikre grenser, False hvis HALT bør aktiveres.
        HALT aktiveres kun når tau forlater koherenssonen [tau_min, tau_max] med >20% margin.
        """
        current_entropy = self.calculate_entropy(token_probs)
        current_tau = self.update_tau(current_entropy)

        params = self.get_admissibility_params()

        halt_triggered = False
        halt_low = self.tau_min * 0.8   # 1510
        halt_high = self.tau_max * 1.2  # 5719

        if current_tau < halt_low or current_tau > halt_high:
            halt_triggered = True
            print(f"[LIM] HALT TRIGGERED! Tau={current_tau:.2f} utenfor kritisk grense [{halt_low:.0f}, {halt_high:.0f}].")

        return not halt_triggered, params


# --- TESTKODE FOR Å VALIDERE LOGIKKEN ---

if __name__ == "__main__":
    print("--- Simulerer LIM-filter over 10 steg ---")

    ccl = LIMFilter(initial_tau=2000.0)

    # Uniform distributions over n tokens give entropy log2(n) ≈ target
    simulated_entropies = [1.2, 1.5, 2.8, 4.5, 6.0, 5.5, 3.0, 1.1, 0.9, 1.0]

    for i, h in enumerate(simulated_entropies):
        n = max(2, int(round(2 ** h)))
        probs = [1.0 / n] * n
        admissible, params = ccl.is_admissible(probs)

        print(f"Steg {i+1}: Entropi≈{h:.2f} | Tau={params['current_tau']:.2f} | Status={params['status']} | Temp={params['temperature']:.3f}")

        if not admissible:
            print(">>> SYSTEM STOPPET AV LOVGIVEREN <<<")
            break

    print("\n[LIM] Test fullført.")
