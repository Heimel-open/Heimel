import json
from copy import deepcopy
from pathlib import Path

from digital_dna import (
    ContinuityDecision,
    ContinuityEvaluator,
    DigitalDNAManifest,
    EquivalenceRule,
    IdentityTransition,
    PairOperator,
    StateOperator,
    StateRule,
)
from digital_dna.challenge import ExperimentalLineageGuard, LineageRule
from digital_dna.long_horizon import (
    ContextOnlyDriver,
    MutatingDriver,
    TwinAwareRiskDriver,
    TwinDriverHarness,
    TwinSnapshot,
    bounded_projection,
    decision_records_from_mapping,
    projection_is_fresh,
)


PREREG = (
    Path(__file__).parents[1]
    / "experiments"
    / "preregistrations"
    / "framleis_twin_driver_v2.json"
)


def frozen():
    return json.loads(PREREG.read_text(encoding="utf-8"))


def snapshot():
    data = frozen()["canonical_twin"]
    return TwinSnapshot(
        twin_id=data["twin_id"],
        version=int(data["version"]),
        state=deepcopy(data["state"]),
    )


def records():
    return decision_records_from_mapping(frozen()["decision_records"])


def test_v2_preregistration_is_explicitly_synthetic_and_held_out():
    data = frozen()

    assert data["challenge_id"] == "framleis-twin-driver-v2"
    assert data["epistemic_status"] == "falsification_criterion"
    assert data["corpus_kind"] == "synthetic_preregistered"
    held_out = [item for item in data["decision_records"] if item["split"] == "held_out"]
    assert len(held_out) == 8
    assert any("real-human" in item.lower() for item in data["limitations"])


def test_twin_aware_driver_beats_frozen_context_only_baseline_on_held_out_fixture():
    twin = snapshot()
    harness = TwinDriverHarness(twin)
    threshold = float(frozen()["drivers"]["twin_aware"]["action_threshold"])

    aware = harness.evaluate_held_out(
        TwinAwareRiskDriver("model-a", action_threshold=threshold),
        records(),
    )
    baseline = harness.evaluate_held_out(ContextOnlyDriver(), records())

    assert aware.evaluated_records == 8
    assert aware.accuracy == 1.0
    assert baseline.accuracy == 0.5
    assert aware.accuracy > baseline.accuracy
    assert aware.canonical_state_digest_before == aware.canonical_state_digest_after


def test_model_swap_does_not_replace_or_mutate_twin_representation():
    twin = snapshot()
    initial = twin.state_digest()
    harness = TwinDriverHarness(twin)

    report_a = harness.evaluate_held_out(TwinAwareRiskDriver("model-a"), records())
    report_b = harness.evaluate_held_out(TwinAwareRiskDriver("model-b"), records())

    assert report_a.model_id != report_b.model_id
    assert report_a.predictions
    assert report_b.predictions
    assert twin.state_digest() == initial
    assert report_a.canonical_state_digest_after == initial
    assert report_b.canonical_state_digest_after == initial


def test_adversarial_driver_mutates_only_its_isolated_copy():
    twin = snapshot()
    initial = twin.state_digest()
    harness = TwinDriverHarness(twin)

    report = harness.evaluate_held_out(MutatingDriver(), records())

    assert report.evaluated_records == 8
    assert twin.state_digest() == initial
    assert twin.state["principal"]["id"] == "person:synthetic-002"
    assert "injected" not in twin.state


def _drift_manifest(local_tolerance: float) -> DigitalDNAManifest:
    return DigitalDNAManifest(
        identity_id="person:synthetic-002",
        version="v2",
        state_space_id="synthetic-person.v2",
        required_state_paths=("principal.id", "continuity.status"),
        allowed_transformations=frozenset({"LEARN"}),
        equivalence_rules=(
            EquivalenceRule("principal.id"),
            EquivalenceRule(
                "preferences.risk_tolerance",
                PairOperator.NUMERIC_DELTA_LTE,
                tolerance=local_tolerance,
            ),
        ),
        invariants=(
            StateRule(
                "principal.id",
                StateOperator.EQUAL,
                "person:synthetic-002",
            ),
        ),
    )


def _state(risk: float) -> dict:
    return {
        "principal": {"id": "person:synthetic-002"},
        "preferences": {"risk_tolerance": risk},
        "continuity": {"status": "ACTIVE"},
    }


def test_long_horizon_drift_falsifies_transition_only_sufficiency_again():
    cfg = frozen()["long_horizon"]
    start = float(cfg["start_risk"])
    step_delta = float(cfg["step_delta"])
    count = int(cfg["steps"])
    manifest = _drift_manifest(float(cfg["local_tolerance"]))

    baseline = ContinuityEvaluator()
    guard = ExperimentalLineageGuard(
        ContinuityEvaluator(),
        anchor_state=_state(start),
        lineage_rules=(
            LineageRule(
                path="preferences.risk_tolerance",
                review_delta=float(cfg["review_delta"]),
                break_delta=float(cfg["break_delta"]),
            ),
        ),
    )

    baseline_decisions = []
    guarded_decisions = []
    before = _state(start)
    for index in range(1, count + 1):
        after = _state(start + step_delta * index)
        tx = IdentityTransition(
            transition_id=f"long-{index}",
            transformation="LEARN",
            before_state=before,
            after_state=after,
            observed_at=f"2026-08-17T08:{index:02d}:00Z",
            evidence_digests=(f"synthetic:long-{index}",),
        )
        baseline_decisions.append(baseline.evaluate(manifest, tx).decision)
        guarded_decisions.append(guard.evaluate(manifest, tx).decision)
        before = after

    assert all(item is ContinuityDecision.CONTINUES for item in baseline_decisions)
    assert ContinuityDecision.REVIEW_REQUIRED in guarded_decisions
    assert ContinuityDecision.BREAK in guarded_decisions
    assert guarded_decisions.index(ContinuityDecision.BREAK) >= 5


def test_nested_twin_projection_is_bounded_copy_and_becomes_stale():
    data = frozen()["nested_projection"]
    source = snapshot()
    projection = bounded_projection(
        source,
        consumer_id=data["consumer_id"],
        allowed_paths=data["allowed_paths"],
    )

    assert projection_is_fresh(projection, source)
    assert projection.payload["principal"]["id"] == "person:synthetic-002"
    assert projection.payload["capabilities"]["role"] == "founder"
    assert "private" not in projection.payload
    assert "preferences" not in projection.payload

    if isinstance(projection.payload, dict):
        projection.payload["principal"]["id"] = "tampered-projection"
    assert source.state["principal"]["id"] == "person:synthetic-002"

    changed = TwinSnapshot(
        twin_id=source.twin_id,
        version=2,
        state={
            **deepcopy(source.state),
            "capabilities": {"role": "chair"},
        },
    )
    assert not projection_is_fresh(projection, changed)


def test_driver_layer_has_no_authority_or_execution_api():
    assert not hasattr(TwinDriverHarness, "authorize")
    assert not hasattr(TwinDriverHarness, "execute")
    assert not hasattr(TwinAwareRiskDriver, "authorize")
    assert not hasattr(TwinAwareRiskDriver, "execute")
