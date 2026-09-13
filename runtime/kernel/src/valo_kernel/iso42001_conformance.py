from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Iterable


class Coverage(str, Enum):
    DIRECT = "direct"
    PARTIAL = "partial"
    RESIDUAL = "residual"


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True)
class ControlSpec:
    control: str
    evidence_objective: str
    required_signals: tuple[str, ...]
    coverage: Coverage
    residual_evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class ControlResult:
    control: str
    verdict: Verdict
    coverage: Coverage
    observed: tuple[str, ...]
    missing: tuple[str, ...]
    residual_evidence: tuple[str, ...]


@dataclass(frozen=True)
class ConformanceReceipt:
    pack: str
    version: str
    results: tuple[ControlResult, ...]
    digest: str

    @property
    def verdict(self) -> Verdict:
        if any(r.verdict is Verdict.FAIL for r in self.results):
            return Verdict.FAIL
        if any(r.verdict is Verdict.INSUFFICIENT_EVIDENCE for r in self.results):
            return Verdict.INSUFFICIENT_EVIDENCE
        return Verdict.PASS


ISO42001_CONTROLS: tuple[ControlSpec, ...] = (
    ControlSpec(
        "A.6.2.4",
        "verification and validation measures are defined and evidenced",
        ("verification_defined", "validation_defined", "criteria_applied", "vv_receipt"),
        Coverage.PARTIAL,
        ("management approval of the organization's V&V framework",),
    ),
    ControlSpec(
        "A.6.2.5",
        "pre-deployment requirements are checked before effect",
        ("deployment_requirements_present", "predeployment_gate", "deployment_receipt"),
        Coverage.PARTIAL,
        ("management approval of the deployment plan",),
    ),
    ControlSpec(
        "A.6.2.6",
        "operation and monitoring requirements are enforced and evidenced",
        ("operation_requirements_present", "monitoring_active", "operation_receipt"),
        Coverage.PARTIAL,
        ("organizational operational-framework approval",),
    ),
    ControlSpec(
        "A.6.2.8",
        "AI-system use produces retained event evidence",
        ("event_logging_enabled", "decision_logged", "effect_logged", "receipt_replayable"),
        Coverage.DIRECT,
    ),
    ControlSpec(
        "A.7.5",
        "data provenance is recorded with integrity evidence",
        ("provenance_origin", "provenance_transformations", "provenance_usage", "provenance_integrity"),
        Coverage.PARTIAL,
        ("organization-wide provenance process governance",),
    ),
    ControlSpec(
        "A.9.4",
        "intended use is enforced and unauthorized use is detectable",
        ("purpose_bound", "unauthorized_use_denied", "usage_logged", "denial_receipt"),
        Coverage.DIRECT,
    ),
    ControlSpec(
        "A.10.2",
        "responsibility allocation is represented at the execution boundary",
        ("actor_identified", "authority_resolved", "delegation_resolved", "responsibility_receipt"),
        Coverage.PARTIAL,
        ("agreements among all external parties", "periodic responsibility review"),
    ),
)


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def evaluate_control(spec: ControlSpec, signals: Iterable[str], failed: Iterable[str] = ()) -> ControlResult:
    observed_set = frozenset(signals)
    failed_set = frozenset(failed)
    required = frozenset(spec.required_signals)
    missing = tuple(sorted(required - observed_set))
    observed = tuple(sorted(required & observed_set))

    if required & failed_set:
        verdict = Verdict.FAIL
    elif missing:
        verdict = Verdict.INSUFFICIENT_EVIDENCE
    else:
        verdict = Verdict.PASS

    return ControlResult(
        control=spec.control,
        verdict=verdict,
        coverage=spec.coverage,
        observed=observed,
        missing=missing,
        residual_evidence=spec.residual_evidence,
    )


def evaluate_iso42001(signals: Iterable[str], failed: Iterable[str] = ()) -> ConformanceReceipt:
    signal_set = frozenset(signals)
    failed_set = frozenset(failed)
    results = tuple(evaluate_control(spec, signal_set, failed_set) for spec in ISO42001_CONTROLS)
    payload = {
        "pack": "iso-iec-42001-runtime-evidence",
        "version": "0.1.0",
        "results": [
            {
                "control": r.control,
                "verdict": r.verdict.value,
                "coverage": r.coverage.value,
                "observed": r.observed,
                "missing": r.missing,
                "residual_evidence": r.residual_evidence,
            }
            for r in results
        ],
    }
    digest = sha256(_canonical(payload)).hexdigest()
    return ConformanceReceipt(
        pack=payload["pack"],
        version=payload["version"],
        results=results,
        digest=digest,
    )


def replay(receipt: ConformanceReceipt, signals: Iterable[str], failed: Iterable[str] = ()) -> bool:
    rerun = evaluate_iso42001(signals, failed)
    return rerun.digest == receipt.digest and rerun.results == receipt.results
