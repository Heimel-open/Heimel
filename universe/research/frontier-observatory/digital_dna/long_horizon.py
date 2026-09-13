"""Long-horizon digital-twin driver experiments.

Epistemic status: implementation_claim.

This module tests architecture boundaries around a maintained twin. It does not
establish human predictive validity, personal identity, standing, or authority
to cause external effects.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

from .core import digest, get_path, MISSING


@dataclass(frozen=True)
class TwinSnapshot:
    twin_id: str
    version: int
    state: Mapping[str, Any]

    def state_digest(self) -> str:
        return digest(self.state)


@dataclass(frozen=True)
class DecisionRecord:
    decision_id: str
    split: str
    context: Mapping[str, Any]
    expected_action: str


@dataclass(frozen=True)
class Prediction:
    model_id: str
    decision_id: str
    action: str
    confidence: float


class PredictionDriver(Protocol):
    model_id: str

    def predict(self, twin: TwinSnapshot, record: DecisionRecord) -> Prediction: ...


@dataclass(frozen=True)
class DriverReport:
    model_id: str
    evaluated_records: int
    correct: int
    accuracy: float
    canonical_state_digest_before: str
    canonical_state_digest_after: str
    predictions: tuple[Prediction, ...]


class TwinDriverHarness:
    """Give a model an isolated twin snapshot and measure prediction only."""

    def __init__(self, canonical_twin: TwinSnapshot) -> None:
        self._canonical_twin = canonical_twin

    @property
    def canonical_twin(self) -> TwinSnapshot:
        return self._canonical_twin

    def evaluate_held_out(
        self,
        driver: PredictionDriver,
        records: Sequence[DecisionRecord],
    ) -> DriverReport:
        before = self._canonical_twin.state_digest()
        predictions: list[Prediction] = []
        correct = 0

        for record in records:
            if record.split != "held_out":
                continue
            isolated = TwinSnapshot(
                twin_id=self._canonical_twin.twin_id,
                version=self._canonical_twin.version,
                state=deepcopy(self._canonical_twin.state),
            )
            prediction = driver.predict(isolated, record)
            predictions.append(prediction)
            if prediction.action == record.expected_action:
                correct += 1

        after = self._canonical_twin.state_digest()
        if after != before:
            raise RuntimeError("canonical_twin_mutated_during_prediction")

        total = len(predictions)
        return DriverReport(
            model_id=driver.model_id,
            evaluated_records=total,
            correct=correct,
            accuracy=(correct / total if total else 0.0),
            canonical_state_digest_before=before,
            canonical_state_digest_after=after,
            predictions=tuple(predictions),
        )


class TwinAwareRiskDriver:
    """Synthetic deterministic driver used only as a preregistered comparator."""

    def __init__(self, model_id: str, action_threshold: float = 0.45) -> None:
        self.model_id = model_id
        self.action_threshold = action_threshold

    def predict(self, twin: TwinSnapshot, record: DecisionRecord) -> Prediction:
        risk = get_path(twin.state, "preferences.risk_tolerance")
        if risk is MISSING:
            return Prediction(self.model_id, record.decision_id, "ASK", 0.0)

        opportunity = float(record.context["opportunity"])
        downside = float(record.context["downside"])
        score = opportunity - downside * (1.0 - float(risk))
        action = "ACT" if score >= self.action_threshold else "WAIT"
        confidence = min(1.0, abs(score - self.action_threshold) + 0.5)
        return Prediction(self.model_id, record.decision_id, action, confidence)


class ContextOnlyDriver:
    """Simpler baseline that does not consume represented personal state."""

    def __init__(self, model_id: str = "context-only-v1") -> None:
        self.model_id = model_id

    def predict(self, twin: TwinSnapshot, record: DecisionRecord) -> Prediction:
        del twin
        opportunity = float(record.context["opportunity"])
        action = "ACT" if opportunity >= 0.5 else "WAIT"
        return Prediction(self.model_id, record.decision_id, action, 0.5)


class MutatingDriver:
    """Adversarial driver proving the model receives only an isolated copy."""

    model_id = "adversarial-mutator-v1"

    def predict(self, twin: TwinSnapshot, record: DecisionRecord) -> Prediction:
        # The harness deliberately provides a deep-copied mapping. Mutating this
        # local object must never mutate canonical represented state.
        if isinstance(twin.state, dict):
            twin.state.setdefault("principal", {})["id"] = "person:attacker"
            twin.state["injected"] = {"by": self.model_id}
        return Prediction(self.model_id, record.decision_id, "ACT", 1.0)


@dataclass(frozen=True)
class ProjectionEnvelope:
    source_twin_id: str
    source_version: int
    source_state_digest: str
    consumer_id: str
    allowed_paths: tuple[str, ...]
    payload: Mapping[str, Any]
    payload_digest: str


def _set_path(target: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    current = target
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    current[parts[-1]] = deepcopy(value)


def bounded_projection(
    source: TwinSnapshot,
    consumer_id: str,
    allowed_paths: Sequence[str],
) -> ProjectionEnvelope:
    """Create a purpose-scoped projection without handing over source state."""

    payload: dict[str, Any] = {}
    normalized = tuple(sorted(set(allowed_paths)))
    for path in normalized:
        value = get_path(source.state, path)
        if value is MISSING:
            continue
        _set_path(payload, path, value)

    return ProjectionEnvelope(
        source_twin_id=source.twin_id,
        source_version=source.version,
        source_state_digest=source.state_digest(),
        consumer_id=consumer_id,
        allowed_paths=normalized,
        payload=payload,
        payload_digest=digest(payload),
    )


def projection_is_fresh(
    envelope: ProjectionEnvelope,
    current_source: TwinSnapshot,
) -> bool:
    return (
        envelope.source_twin_id == current_source.twin_id
        and envelope.source_version == current_source.version
        and envelope.source_state_digest == current_source.state_digest()
    )


def decision_records_from_mapping(items: Sequence[Mapping[str, Any]]) -> tuple[DecisionRecord, ...]:
    return tuple(
        DecisionRecord(
            decision_id=str(item["decision_id"]),
            split=str(item["split"]),
            context=deepcopy(item["context"]),
            expected_action=str(item["expected_action"]),
        )
        for item in items
    )
