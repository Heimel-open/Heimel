"""
VAIG Instrument Registry — de åtte blinde menn.

Kunden konfigurerer ingenting. VAIG scanner hva som er installert
og setter automatisk opp sterkeste tilgjengelige stack.

Jo flere verktøy som er installert, jo sterkere stack.
pip install transformers → NLI-instrumenter aktiveres.
Lokal Ollama → activation_probe aktiveres.
Ny impl registrert → vurderes automatisk.

Legg til ny implementasjon:
    @register("semantic_entropy", priority=3)
    class KernelEntropyImpl(InstrumentBase):
        @classmethod
        def is_available(cls): return _check_import("kernel_entropy")
        def score(self, ...): ...
"""

from typing import Dict, List, Optional, Tuple, Type

from vaig.instruments.base import InstrumentBase

# slot_name -> [(priority, impl_name, class)]
_REGISTRY: Dict[str, List[Tuple[int, str, Type[InstrumentBase]]]] = {
    "length_anomaly":                 [],
    "format_check":                   [],
    "hedge_detector":                 [],
    "logprob_scorer":                 [],
    "activation_probe":               [],
    "activation_safety_classifier":   [],
    "text_similarity":                [],
    "semantic_entropy":               [],
    "cot_auditor":                    [],
    "goal_drift_detector":            [],
    "specification_gaming_detector":  [],
    "capability_escalation_detector": [],
    "environment_integrity_monitor":  [],
    "attack_pattern_library":         [],
    "adaptive_distrust_engine":       [],
    "mandate_divergence_engine":      [],
    "autonomy_budget_evaluator":      [],
    "consequence_simulator":          [],
    "gateway_proveniens_evaluator":   [],
    "policy_safety_classifier":       [],
    "sycophancy_detector":            [],
    "trajectory_consistency":         [],
}

SLOT_ORDER = [
    "length_anomaly",
    "format_check",
    "hedge_detector",
    "logprob_scorer",
    "activation_probe",
    "activation_safety_classifier",
    "text_similarity",
    "semantic_entropy",
    "cot_auditor",
    "goal_drift_detector",
    "specification_gaming_detector",
    "capability_escalation_detector",
    "environment_integrity_monitor",
    "attack_pattern_library",
    "adaptive_distrust_engine",
    "mandate_divergence_engine",
    "autonomy_budget_evaluator",
    "consequence_simulator",
    "gateway_proveniens_evaluator",
    "policy_safety_classifier",
    "sycophancy_detector",
    "trajectory_consistency",
]


def register(slot: str, name: str, priority: int = 1):
    """
    Dekoratør for å registrere en implementasjon.

    priority: høyere = sterkere. VAIG velger automatisk
    høyest tilgjengelige (is_available() == True).
    priority=0 er reservert for null/placeholder-implementasjoner.
    """
    def decorator(cls: Type[InstrumentBase]):
        if slot not in _REGISTRY:
            raise ValueError(f"Ukjent slot: {slot!r}. Kjente: {list(_REGISTRY)}")
        cls.name = slot
        cls.priority = priority
        _REGISTRY[slot].append((priority, name, cls))
        _REGISTRY[slot].sort(key=lambda t: t[0], reverse=True)
        return cls
    return decorator


def best_available(slot: str) -> Optional[InstrumentBase]:
    """
    Velg høyest prioritert implementasjon som er tilgjengelig.
    Returnerer None hvis slot er tom eller ingenting er tilgjengelig.
    """
    for priority, name, cls in _REGISTRY.get(slot, []):
        if priority == 0:
            continue
        if cls.is_available():
            return cls()
    return None


def build_optimal_ensemble() -> Dict[str, InstrumentBase]:
    """
    Bygg sterkeste tilgjengelige ensemble automatisk.
    Ingen konfig nødvendig — kalles én gang ved oppstart.

    Returnerer dict: slot_name -> instrument-instans
    Slots uten tilgjengelig implementasjon ekskluderes stille.
    """
    ensemble = {}
    for slot in SLOT_ORDER:
        instrument = best_available(slot)
        if instrument is not None:
            ensemble[slot] = instrument
    return ensemble


def describe_ensemble(ensemble: Dict[str, InstrumentBase]) -> str:
    """Beskriv aktiv stack — for logging og revisjonsspor."""
    lines = ["VAIG aktiv stack:"]
    for slot in SLOT_ORDER:
        if slot in ensemble:
            inst = ensemble[slot]
            lines.append(f"  ✓ {slot:<22} {inst.__class__.__name__} (priority={inst.priority})")
        else:
            lines.append(f"  — {slot:<22} ikke tilgjengelig")
    return "\n".join(lines)


def status() -> None:
    """Skriv ut hva som er registrert og hva som faktisk er tilgjengelig."""
    print("\nVAIG Instrument Registry")
    print("=" * 55)
    for slot in SLOT_ORDER:
        entries = _REGISTRY.get(slot, [])
        if not entries:
            print(f"  {slot:<22} — ingen implementasjoner")
            continue
        for priority, name, cls in entries:
            avail = "✓" if (priority > 0 and cls.is_available()) else "—"
            print(f"  {avail} {slot:<22} [{name}] priority={priority}")
    print()
    ensemble = build_optimal_ensemble()
    active = len(ensemble)
    print(f"  Aktive instrumenter: {active}/{len(SLOT_ORDER)}")
    print()


REGISTRY = _REGISTRY
