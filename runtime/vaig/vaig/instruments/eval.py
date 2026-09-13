"""
VAIG Instrument Evaluator — kontinuerlig måling av hver blind mann.

Kobler WORM-logg mot innkommende fasit (legal_verdict).
Oppdaterer per-instrument AUC, ECE og marginalbidrag etter hvert
nye labelede eksempel.

Flyten:
    1. VAIG evaluerer → skriver instrument-scorer til WORM-logg
    2. Menneske reviewer → legal_verdict registreres (async)
    3. Evaluator kobler verdict mot logg-entry → oppdaterer metrikk
    4. Kalibrerer ensemble-vekter basert på oppdaterte AUC-er

Dette er grunnen til at WORM-loggen er produktet, ikke bare compliance.
Hver menneskelig korreksjon gjør ensemblet sterkere.
"""

import json
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path


# ──────────────────────────────────────────────
# Metrikk-struktur per instrument
# ──────────────────────────────────────────────

@dataclass
class InstrumentMetrics:
    """Løpende statistikk for én blind mann."""
    slot: str
    n_labeled: int = 0          # antall eksempler med fasit
    n_positive: int = 0         # antall faktiske feil (FEIL)

    # For AUC: samle (score, label)-par
    _pairs: List[Tuple[float, int]] = field(default_factory=list)

    # For ECE: 10 bins
    _bins: List[List[float]] = field(default_factory=lambda: [[] for _ in range(10)])
    _bin_labels: List[List[int]] = field(default_factory=lambda: [[] for _ in range(10)])

    def update(self, score: float, label: int) -> None:
        """Legg til ett nytt (score, fasit)-par. label: 1=FEIL, 0=OK."""
        self.n_labeled += 1
        self.n_positive += label
        self._pairs.append((score, label))

        # Bin for ECE
        bin_idx = min(int(score * 10), 9)
        self._bins[bin_idx].append(score)
        self._bin_labels[bin_idx].append(label)

    @property
    def auc(self) -> Optional[float]:
        """
        ROC-AUC via trapez-metode.
        Returnerer None hvis < 5 eksempler eller kun én klasse.
        """
        if self.n_labeled < 5:
            return None
        n_pos = sum(l for _, l in self._pairs)
        n_neg = self.n_labeled - n_pos
        if n_pos == 0 or n_neg == 0:
            return None

        sorted_pairs = sorted(self._pairs, key=lambda x: x[0], reverse=True)
        tp = fp = 0
        prev_tp = prev_fp = 0
        auc = 0.0
        for score, label in sorted_pairs:
            if label == 1:
                tp += 1
            else:
                fp += 1
            auc += (fp - prev_fp) * (tp + prev_tp) / 2
            prev_tp, prev_fp = tp, fp

        return auc / (n_pos * n_neg) if (n_pos * n_neg) > 0 else None

    @property
    def ece(self) -> float:
        """
        Expected Calibration Error — avstand mellom predikert og faktisk.
        0.0 = perfekt kalibrert.
        """
        total = self.n_labeled
        if total == 0:
            return 0.0

        ece = 0.0
        for scores, labels in zip(self._bins, self._bin_labels):
            if not scores:
                continue
            avg_score = sum(scores) / len(scores)
            avg_label = sum(labels) / len(labels)
            ece += (len(scores) / total) * abs(avg_score - avg_label)
        return ece

    @property
    def prevalence(self) -> float:
        """Andel faktiske feil i datasettet."""
        return self.n_positive / self.n_labeled if self.n_labeled else 0.0

    def summary(self) -> str:
        auc_str = f"{self.auc:.3f}" if self.auc is not None else "for få data"
        return (
            f"{self.slot:<22} "
            f"n={self.n_labeled:<5} "
            f"AUC={auc_str:<8} "
            f"ECE={self.ece:.3f}  "
            f"feilrate={self.prevalence:.1%}"
        )


# ──────────────────────────────────────────────
# Kontinuerlig evaluator
# ──────────────────────────────────────────────

class ContinuousEvaluator:
    """
    Kobler WORM-logg mot fasit og holder løpende metrikk per instrument.

    Bruk:
        evaluator = ContinuousEvaluator(worm_log_path)
        evaluator.submit_verdict(entry_id="abc123", verdict="FEIL")
        print(evaluator.report())
        weights = evaluator.calibrated_weights()
    """

    def __init__(self, worm_log_path: str, metrics_path: Optional[str] = None):
        self.worm_log_path = Path(worm_log_path)
        self.metrics_path = Path(metrics_path) if metrics_path else \
            self.worm_log_path.parent / "instrument_metrics.jsonl"
        self.metrics: Dict[str, InstrumentMetrics] = {}
        self._load_metrics()

    # ── Innkommende fasit ──────────────────────

    def submit_verdict(self, entry_id: str, verdict: str) -> bool:
        """
        Koble menneskelig fasit mot WORM-logg-entry.
        verdict: "OK" eller "FEIL"
        Returnerer True hvis entry ble funnet og oppdatert.
        """
        label = 1 if verdict.upper() == "FEIL" else 0
        entry = self._find_entry(entry_id)
        if entry is None:
            return False

        instrument_scores = entry.get("instrument_scores", {})
        for slot, score in instrument_scores.items():
            if slot not in self.metrics:
                self.metrics[slot] = InstrumentMetrics(slot=slot)
            self.metrics[slot].update(float(score), label)

        self._persist_update(entry_id, label, instrument_scores)
        return True

    def submit_batch(self, verdicts: Dict[str, str]) -> int:
        """Submit multiple verdicts. Returnerer antall vellykkede."""
        return sum(self.submit_verdict(eid, v) for eid, v in verdicts.items())

    # ── Kalibrering ──────────────────────────

    def calibrated_weights(self, min_samples: int = 20) -> Dict[str, float]:
        """
        Beregn ensemble-vekter basert på AUC per instrument.
        Instrumenter med for få data får vekt 1.0 (nøytral).
        Instrumenter med AUC < 0.5 får vekt 0.0 (deaktivert).
        """
        weights = {}
        for slot, m in self.metrics.items():
            auc = m.auc
            if auc is None or m.n_labeled < min_samples:
                weights[slot] = 1.0  # ikke nok data — behold nøytral vekt
            elif auc < 0.5:
                weights[slot] = 0.0  # verre enn tilfeldig — deaktiver
            else:
                # Skaler AUC 0.5–1.0 → vekt 0.0–2.0
                weights[slot] = (auc - 0.5) * 4.0
        return weights

    def marginal_contributions(self) -> Dict[str, float]:
        """
        Estimer marginalbidrag per instrument:
        differansen i ensemble-AUC med og uten instrumentet.
        Krever minst 10 labelede eksempler per instrument.
        """
        from vaig.instruments.registry import SLOT_ORDER
        contributions = {}
        baseline = self._ensemble_auc(list(self.metrics.keys()))

        for slot in self.metrics:
            without = [s for s in self.metrics if s != slot]
            reduced = self._ensemble_auc(without)
            contributions[slot] = round(baseline - reduced, 4)

        return dict(sorted(contributions.items(), key=lambda x: x[1], reverse=True))

    # ── Rapportering ─────────────────────────

    def report(self) -> str:
        if not self.metrics:
            return "Ingen labelede eksempler ennå."

        lines = ["\nVAIG Instrument Kvalitet", "=" * 60]
        for slot, m in sorted(self.metrics.items(), key=lambda x: x[1].auc or 0, reverse=True):
            lines.append(m.summary())

        lines.append("")
        lines.append("Ensemble-vekter (kalibrert):")
        for slot, w in self.calibrated_weights().items():
            bar = "█" * int(w * 5)
            lines.append(f"  {slot:<22} {w:.2f}  {bar}")

        mc = self.marginal_contributions()
        if mc:
            lines.append("")
            lines.append("Marginalbidrag til ensemble:")
            for slot, delta in mc.items():
                sign = "+" if delta >= 0 else ""
                lines.append(f"  {slot:<22} {sign}{delta:.4f} AUC")

        return "\n".join(lines)

    # ── Internals ────────────────────────────

    def _find_entry(self, entry_id: str) -> Optional[dict]:
        if not self.worm_log_path.exists():
            return None
        with open(self.worm_log_path) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("id") == entry_id:
                        return entry
                except json.JSONDecodeError:
                    continue
        return None

    def _ensemble_auc(self, slots: List[str]) -> float:
        """AUC for enkel ensemble-score (uvektet snitt) over gitte slots."""
        if not slots:
            return 0.5
        # Finn felles labelede eksempler
        all_pairs = [self.metrics[s]._pairs for s in slots if s in self.metrics]
        if not all_pairs:
            return 0.5

        # Bygg (avg_score, label)-par for felles indekser
        min_len = min(len(p) for p in all_pairs)
        if min_len < 5:
            return 0.5

        combined = []
        for i in range(min_len):
            avg_score = sum(p[i][0] for p in all_pairs) / len(all_pairs)
            label = all_pairs[0][i][1]
            combined.append((avg_score, label))

        n_pos = sum(l for _, l in combined)
        n_neg = len(combined) - n_pos
        if n_pos == 0 or n_neg == 0:
            return 0.5

        sorted_c = sorted(combined, key=lambda x: x[0], reverse=True)
        tp = fp = prev_tp = prev_fp = 0
        auc = 0.0
        for _, label in sorted_c:
            if label == 1:
                tp += 1
            else:
                fp += 1
            auc += (fp - prev_fp) * (tp + prev_tp) / 2
            prev_tp, prev_fp = tp, fp
        return auc / (n_pos * n_neg)

    def _persist_update(self, entry_id: str, label: int, scores: dict) -> None:
        with open(self.metrics_path, "a") as f:
            f.write(json.dumps({
                "entry_id": entry_id,
                "label": label,
                "scores": scores,
            }) + "\n")

    def _load_metrics(self) -> None:
        if not self.metrics_path.exists():
            return
        with open(self.metrics_path) as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    for slot, score in rec["scores"].items():
                        if slot not in self.metrics:
                            self.metrics[slot] = InstrumentMetrics(slot=slot)
                        self.metrics[slot].update(float(score), rec["label"])
                except (json.JSONDecodeError, KeyError):
                    continue
