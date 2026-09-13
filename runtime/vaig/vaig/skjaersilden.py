"""Skjærsilden — L6.5, Council verdicts → domain threshold calibration."""

import json
import os
from typing import Dict, Optional

from vaig.council.queue import CouncilQueue


_MIN_THRESHOLD = 0.05
_MAX_THRESHOLD = 0.95
_DELTA = 0.05
_MIN_SAMPLE = 10   # require at least 10 verdicts per domain before adjusting


class Skjaersilden:
    """
    L6.5 — Feedback loop from Council verdicts to domain thresholds.

    REJECT-rate > 30%  → lower DEGRADE threshold (more sensitive)
    APPROVE-rate > 80% → raise DEGRADE threshold (reduce noise)

    Usage:
        s = Skjaersilden()
        updated = s.calibrate(council_queue)
        s.apply(updated, path="vaig_thresholds.json")

        # Dirigent loads at startup:
        # VAIG_THRESHOLDS_PATH=vaig_thresholds.json
    """

    def calibrate(self, council: CouncilQueue) -> Dict[str, Dict]:
        """
        Compute updated thresholds from Council verdict history.
        Returns {domain: {"HALT": float, "DEGRADE": float, "WARN": float, "MONITOR": float}}
        """
        from vaig.scout.dirigent import _DOMAIN_THRESHOLDS
        from vaig.scout.terrain import Domain

        result: Dict[str, Dict] = {}
        items = council.recent(limit=500)

        domain_buckets: Dict[str, list] = {}
        for item in items:
            if item.verdict is None:
                continue
            domain_buckets.setdefault(item.domain, []).append(item)

        for domain_str, verdicts in domain_buckets.items():
            if len(verdicts) < _MIN_SAMPLE:
                continue

            approve = sum(1 for v in verdicts if v.verdict == "APPROVE")
            reject = sum(1 for v in verdicts if v.verdict == "REJECT")
            total = approve + reject
            if total == 0:
                continue

            try:
                domain = Domain[domain_str]
            except KeyError:
                domain = Domain.GENERAL

            base = dict(_DOMAIN_THRESHOLDS.get(domain, _DOMAIN_THRESHOLDS.get(Domain.GENERAL, {})))
            current_degrade = base.get("DEGRADE", 0.55)
            approve_rate = approve / total
            reject_rate = reject / total

            if approve_rate > 0.80:
                new_degrade = min(current_degrade + _DELTA, _MAX_THRESHOLD)
            elif reject_rate > 0.30:
                new_degrade = max(current_degrade - _DELTA, _MIN_THRESHOLD)
            else:
                new_degrade = current_degrade

            result[domain_str] = {
                "HALT": base.get("HALT", 0.75),
                "DEGRADE": round(new_degrade, 4),
                "WARN": base.get("WARN", 0.35),
                "MONITOR": base.get("MONITOR", 0.15),
                "_sample_size": total,
                "_approve_rate": round(approve_rate, 4),
            }

        return result

    def delta(self, domain: str, council: CouncilQueue) -> float:
        """Return the DEGRADE threshold delta for a single domain from last 100 verdicts."""
        items = [
            i for i in council.recent(100)
            if i.domain == domain and i.verdict is not None
        ]
        if len(items) < _MIN_SAMPLE:
            return 0.0
        approve = sum(1 for i in items if i.verdict == "APPROVE")
        reject = sum(1 for i in items if i.verdict == "REJECT")
        total = approve + reject
        if total == 0:
            return 0.0
        if approve / total > 0.80:
            return _DELTA
        if reject / total > 0.30:
            return -_DELTA
        return 0.0

    def apply(self, thresholds: Dict, path: str = "vaig_thresholds.json") -> None:
        """Persist calibrated thresholds to JSON file (merges with existing)."""
        existing: Dict = {}
        if os.path.exists(path):
            try:
                with open(path) as f:
                    existing = json.load(f)
            except Exception:
                pass
        existing.update(thresholds)
        with open(path, "w") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)

    def load(self, path: str = "vaig_thresholds.json") -> Optional[Dict]:
        """Load persisted thresholds. Returns None if file absent."""
        if not os.path.exists(path):
            return None
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return None
