"""
VAIG Instrument Watchdog — automatisk bytte ved underlevering.

Dersom en blind mann konsekvent underleverer (AUC < terskel,
eller verre enn tilfeldig), degraderer watchdog implementasjonen
og forsøker neste tilgjengelige i prioritetstrekket.

Kobling:
    ContinuousEvaluator  → måler kvalitet per instrument
    Watchdog             → reagerer på dårlig ytelse
    Registry             → bytter til neste tilgjengelige impl
    Ensemble             → oppdateres live

Degraderingsregler:
    AUC < 0.55 etter 30+ eksempler  → nedgradert (prøv lavere prioritet)
    AUC < 0.50 etter 20+ eksempler  → deaktivert (støy)
    AUC stiger igjen                → reaktivert ved neste kalibrering
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from vaig.instruments.registry import _REGISTRY, best_available, SLOT_ORDER
from vaig.instruments.base import InstrumentBase

if TYPE_CHECKING:
    from vaig.instruments.eval import ContinuousEvaluator

logger = logging.getLogger("vaig.watchdog")

# ── Terskler ───────────────────────────────────

AUC_DEGRADE_THRESHOLD   = 0.55   # under dette → prøv neste impl
AUC_DISABLE_THRESHOLD   = 0.50   # under dette → deaktiver helt
MIN_SAMPLES_FOR_ACTION  = 20     # ikke ta aksjon på for lite data


@dataclass
class SlotStatus:
    slot: str
    active_impl: str
    active_priority: int
    state: str = "ok"            # ok | degraded | disabled
    degraded_impls: List[str] = field(default_factory=list)
    action_log: List[str] = field(default_factory=list)

    def log(self, msg: str) -> None:
        self.action_log.append(msg)
        logger.info(f"[watchdog:{self.slot}] {msg}")


class InstrumentWatchdog:
    """
    Overvåker instrument-kvalitet og bytter implementasjon ved behov.

    Kobles til et levende ensemble-dict — endringer skjer in-place,
    slik at neste evaluering bruker oppgradert implementasjon.
    """

    def __init__(
        self,
        ensemble: Dict[str, InstrumentBase],
        evaluator: "ContinuousEvaluator",
    ):
        self.ensemble = ensemble
        self.evaluator = evaluator
        self.slot_status: Dict[str, SlotStatus] = {}
        self._init_status()

    def _init_status(self) -> None:
        for slot, instrument in self.ensemble.items():
            impl_name = instrument.__class__.__name__
            self.slot_status[slot] = SlotStatus(
                slot=slot,
                active_impl=impl_name,
                active_priority=instrument.priority,
            )

    def check_and_rebalance(self) -> List[str]:
        """
        Kjøres etter hver ny batch med fasit-data.
        Returnerer liste over slotser som ble endret.
        """
        changed = []
        weights = self.evaluator.calibrated_weights()

        for slot in list(self.ensemble.keys()):
            metrics = self.evaluator.metrics.get(slot)
            if metrics is None or metrics.n_labeled < MIN_SAMPLES_FOR_ACTION:
                continue

            auc = metrics.auc
            if auc is None:
                continue

            status = self.slot_status.get(slot)

            if auc < AUC_DISABLE_THRESHOLD:
                action = self._try_swap_or_disable(slot, auc, reason="AUC < 0.50 (verre enn tilfeldig)")
                if action:
                    changed.append(slot)

            elif auc < AUC_DEGRADE_THRESHOLD:
                action = self._try_swap_or_disable(slot, auc, reason=f"AUC < {AUC_DEGRADE_THRESHOLD}")
                if action:
                    changed.append(slot)

        return changed

    def _try_swap_or_disable(self, slot: str, auc: float, reason: str) -> bool:
        """
        Forsøk å bytte til neste prioriterte implementasjon.
        Deaktiver hvis ingen alternativ finnes.
        """
        status = self.slot_status[slot]
        current_priority = self.ensemble[slot].priority

        # Finn neste tilgjengelige implementasjon med lavere prioritet
        candidates = [
            (p, name, cls)
            for p, name, cls in _REGISTRY.get(slot, [])
            if p < current_priority and p > 0 and cls.is_available()
            and name not in status.degraded_impls
        ]

        if candidates:
            # Velg høyest tilgjengelige blant kandidatene
            p, name, cls = candidates[0]
            new_instrument = cls()
            self.ensemble[slot] = new_instrument
            status.active_impl = name
            status.active_priority = p
            status.state = "degraded"
            status.degraded_impls.append(name)
            status.log(f"Byttet til [{name}] (priority={p}) — {reason}, AUC={auc:.3f}")
            return True
        else:
            # Ingen alternativ — deaktiver sloten
            del self.ensemble[slot]
            status.state = "disabled"
            status.log(f"Deaktivert — {reason}, AUC={auc:.3f}, ingen alternativ tilgjengelig")
            return True

    def upgrade_if_available(self) -> List[str]:
        """
        Sjekk om nye/bedre implementasjoner er blitt tilgjengelige
        siden sist (f.eks. ny pip-installasjon, ny GitHub-impl registrert).
        Oppgrader automatisk hvis høyere prioritet nå er tilgjengelig.

        Dette er koblingen til GitHub-søket annenhver dag:
        ny impl registrert → neste upgrade_if_available() plukker den opp.
        """
        upgraded = []
        for slot in SLOT_ORDER:
            current_priority = self.ensemble[slot].priority if slot in self.ensemble else 0

            # Finn høyeste tilgjengelige prioritet
            best = None
            best_priority = current_priority
            for p, name, cls in _REGISTRY.get(slot, []):
                if p > best_priority and cls.is_available():
                    best = (p, name, cls)
                    best_priority = p

            if best:
                p, name, cls = best
                new_instrument = cls()
                self.ensemble[slot] = new_instrument
                status = self.slot_status.get(slot)
                if status:
                    status.active_impl = name
                    status.active_priority = p
                    status.state = "ok"
                    status.log(f"Oppgradert til [{name}] (priority={p})")
                else:
                    self.slot_status[slot] = SlotStatus(slot=slot, active_impl=name, active_priority=p)
                upgraded.append(slot)

        return upgraded

    def reinstate_disabled(self) -> List[str]:
        """
        Reaktiver deaktiverte slots om noe har blitt tilgjengelig.
        Kalles automatisk etter upgrade_if_available().
        """
        reinstated = []
        for slot in SLOT_ORDER:
            if slot in self.ensemble:
                continue
            instrument = best_available(slot)
            if instrument is not None:
                self.ensemble[slot] = instrument
                status = self.slot_status.get(slot)
                if status:
                    status.state = "ok"
                    status.active_impl = instrument.__class__.__name__
                    status.active_priority = instrument.priority
                    status.log(f"Reaktivert med [{instrument.__class__.__name__}]")
                reinstated.append(slot)
        return reinstated

    def scan_and_evolve(self) -> Dict[str, List[str]]:
        """
        Kjør full syklus: mål → bytt nedover ved feil → oppgrader ved mulighet.
        Returner oversikt over alle endringer.
        """
        return {
            "degraded":  self.check_and_rebalance(),
            "upgraded":  self.upgrade_if_available(),
            "reinstated": self.reinstate_disabled(),
        }

    def report(self) -> str:
        lines = ["\nVAIG Watchdog Status", "=" * 50]
        for slot in SLOT_ORDER:
            status = self.slot_status.get(slot)
            if slot in self.ensemble:
                inst = self.ensemble[slot]
                m = self.evaluator.metrics.get(slot)
                auc_str = f"AUC={m.auc:.3f}" if (m and m.auc) else "AUC=—"
                state_icon = "✓" if (not status or status.state == "ok") else "⚠"
                lines.append(f"  {state_icon} {slot:<22} {inst.__class__.__name__:<30} {auc_str}")
            else:
                last_log = status.action_log[-1] if (status and status.action_log) else "—"
                lines.append(f"  ✗ {slot:<22} DEAKTIVERT — {last_log}")
        return "\n".join(lines)
