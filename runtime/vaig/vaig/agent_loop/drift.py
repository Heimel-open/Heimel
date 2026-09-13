from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DriftSignal:
    changed_object: bool = False
    changed_domain: bool = False
    changed_authority: bool = False
    changed_beneficiary: bool = False
    changed_external_consequence: bool = False
    increasing_uncertainty: bool = False
    unverified_observation_as_fact: bool = False


def score_drift(signal: DriftSignal) -> float:
    """Cheap symbolic drift score for the MVP.

    No embeddings. No LLM. This is intentionally boring and explainable.
    """

    score = 0.0
    if signal.changed_object:
        score += 0.18
    if signal.changed_domain:
        score += 0.20
    if signal.changed_authority:
        score += 0.18
    if signal.changed_beneficiary:
        score += 0.12
    if signal.changed_external_consequence:
        score += 0.20
    if signal.increasing_uncertainty:
        score += 0.10
    if signal.unverified_observation_as_fact:
        score += 0.22
    return min(score, 1.0)


def cumulative_drift(*signals: DriftSignal) -> float:
    """Accumulate drift while avoiding unbounded growth."""

    total = 0.0
    for signal in signals:
        total += score_drift(signal) * (1.0 - total)
    return min(total, 1.0)
