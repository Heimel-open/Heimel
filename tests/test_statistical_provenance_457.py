"""Targeted tests for valo-platform #457 (Statistical Provenance + BARO weights).

Run from the repo root with:
    uv run pytest tests/unit/test_statistical_provenance_457.py -q --noconftest -p no:cacheprovider

Single import root (src.valo_platform.*) to avoid the dual-class trap.
"""

import sys
from pathlib import Path

# Repo root (parent of src/) so `import src.valo_platform...` resolves as a
# namespace package. Nothing imports bare `valo_platform` in this run.
ROOT = str(Path(__file__).resolve().parent.parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.valo_platform.models.core_receipt import ExecutionDecision, Receipt
from src.valo_platform.statistical_provenance import (
    CommissioningActor,
    ConflictRecord,
    DecomposedStatisticalSignals,
    EvidenceStrength,
    FunderLink,
    FundingType,
    NodeType,
    ProvenanceGraph,
    RelationshipEdge,
    EdgeType,
    SponsorRoleRecord,
    StatisticalProvenanceEvaluator,
    StatisticalProvenanceRecord,
    StatisticalSignal,
    StudyDesignRiskRecord,
)
from src.valo_platform.baro_weight_profile import (
    BaroWeightProfile,
    HardRule,
    PLATFORM_INVARIANTS,
    PolicyPrecedenceResolver,
    ProfileScope,
    simulate,
    SimulationReport,
    ThreeLayerControl,
    WeightKind,
)


# --------------------------------------------------------------------------
# Section1 — domain models
# --------------------------------------------------------------------------
def _bad_record() -> StatisticalProvenanceRecord:
    return StatisticalProvenanceRecord(
        commissioning_actor=CommissioningActor(
            actor_id="sponsor_acme", role="sponsor",
            funder_ids=["fund_alpha"],
        ),
        funders=[FunderLink(funder_id="fund_alpha",
                          funding_type=FundingType.INDIRECT, vehicle="venture")],
        sponsor_roles=SponsorRoleRecord(design=True, data=True,
                                     analysis=True, publication=True),
        conflicts=ConflictRecord(author_conflict=True, panel_conflict=True),
        study_risks=StudyDesignRiskRecord(
            endpoint_switching=True, multiple_testing=True,
            denominator_omission=True, relative_vs_absolute=True,
            causal_overclaim=True, publication_bias=True,
            guideline_capture=True,
        ),
        sample_size=12,
        population_representative=False,
        funding_changes_review_requirements=True,
    )


def test_domain_models_instantiate():
    r = _bad_record()
    assert r.commissioning_actor.actor_id == "sponsor_acme"
    assert r.sponsor_roles.publication is True
    assert r.funders[0].funding_type == FundingType.INDIRECT


# --------------------------------------------------------------------------
# Section3 — VAIG decomposed signals (NO opaque score, NEVER decides)
# --------------------------------------------------------------------------
def test_evaluator_returns_decomposed_signals():
    ev = StatisticalProvenanceEvaluator()
    out = ev.evaluate(_bad_record())
    assert isinstance(out, DecomposedStatisticalSignals)
    # Decomposed: every risk class visible on its own.
    for sig in (
        StatisticalSignal.SPONSOR_CONTROL_RISK,
        StatisticalSignal.CONFLICT_RISK,
        StatisticalSignal.ENDPOINT_SWITCHING_RISK,
        StatisticalSignal.MULTIPLE_TESTING_RISK,
        StatisticalSignal.PRESENTATION_MANIPULATION_RISK,
        StatisticalSignal.CAUSAL_OVERCLAIM_RISK,
        StatisticalSignal.PUBLICATION_BIAS_RISK,
        StatisticalSignal.POLICY_CAPTURE_RISK,
        StatisticalSignal.SAMPLING_RISK,
        StatisticalSignal.REPRESENTATIVENESS_RISK,
        StatisticalSignal.UNRESOLVED_UNCERTAINTY,
    ):
        assert sig in out.signals, f"missing decomposed signal {sig}"
        assert 0.0 <= out.signals[sig] <= 1.0


def test_evaluator_has_no_opaque_aggregate():
    out = StatisticalProvenanceEvaluator().evaluate(_bad_record())
    # Deliberately no single score field.
    assert not hasattr(out, "aggregate_score")
    assert not hasattr(out, "overall_risk")
    assert out.unresolved_uncertainty > 0.0


def test_vaig_evaluator_never_decides():
    # VAIG evaluates risk; it is NOT an admissibility authority.
    ev = StatisticalProvenanceEvaluator()
    assert ev.decides() is False
    out = ev.evaluate(_bad_record())
    assert not hasattr(out, "decision")
    assert not hasattr(out, "verdict")


# --------------------------------------------------------------------------
# Section2 — relationship graph
# --------------------------------------------------------------------------
def test_graph_indirect_funding_path():
    g = ProvenanceGraph()
    g.add_node("sponsor_acme", NodeType.SPONSOR)
    g.add_node("fund_alpha", NodeType.FUNDING_VEHICLE)
    g.add_edge(RelationshipEdge(
        source="fund_alpha", target="sponsor_acme",
        relationship_type=EdgeType.FUNDS,
        direct_or_indirect="indirect",
        evidence_strength=EvidenceStrength.PLAUSIBLE,
    ))
    paths = g.indirect_paths_to("sponsor_acme")
    assert len(paths) == 1
    assert paths[0].direct_or_indirect == "indirect"
    s = g.summary()
    assert s["indirect_edges"] == 1


# --------------------------------------------------------------------------
# Section4 — customer BARO weight profiles (advisory only)
# --------------------------------------------------------------------------
def _clean_profile() -> BaroWeightProfile:
    return BaroWeightProfile(
        profile_id="p1", version="1.0.0", owner="acme",
        weights={
            WeightKind.EVIDENCE_QUALITY: 0.5,
            WeightKind.INFLUENCE_RISK: 0.5,
            WeightKind.CONSEQUENCE: 0.4,
            WeightKind.CONTEXT: 0.3,
        },
        scope={ProfileScope.ORGANISATION: "acme"},
    )


def test_weight_profile_defaults_carry_all_invariants():
    p = _clean_profile()
    assert set(p.hard_rules) == set(PLATFORM_INVARIANTS)
    assert HardRule.BARO_CANNOT_DECIDE in p.hard_rules
    assert HardRule.REHT_DECISION_AUTHORITY in p.hard_rules


def test_baro_profile_is_advisory_not_authority():
    p = _clean_profile()
    # The profile is a config record; it has no decision method.
    assert not hasattr(p, "decide")
    assert not hasattr(p, "admit")


# --------------------------------------------------------------------------
# Section5 — three-layer control (invariants + regulatory floors)
# --------------------------------------------------------------------------
def test_three_layer_rejects_removed_invariant():
    p = _clean_profile()
    p.hard_rules = [h for h in p.hard_rules
                     if h != HardRule.PROVENANCE_RECORDED]
    ok, violations, conflicts = ThreeLayerControl().validate(p)
    assert ok is False
    assert any("provenance_recorded" in v for v in violations)


def test_three_layer_rejects_zeroed_protected_weight():
    p = _clean_profile()
    p.weights[WeightKind.INFLUENCE_RISK] = 0.0  # try to zero out
    ok, violations, conflicts = ThreeLayerControl().validate(p)
    assert ok is False
    assert any("influence_risk" in c for c in conflicts)


def test_three_layer_accepts_valid_profile():
    ok, violations, conflicts = ThreeLayerControl().validate(_clean_profile())
    assert ok is True
    assert violations == [] and conflicts == []


# --------------------------------------------------------------------------
# Section6 — deterministic policy precedence (explicit conflicts)
# --------------------------------------------------------------------------
def test_policy_precedence_reports_conflicts_explicitly():
    p = _clean_profile()
    resolved, conflicts = PolicyPrecedenceResolver().resolve(
        p, jurisdiction="EU", action_class="supplier_payment")
    assert resolved[WeightKind.INFLUENCE_RISK.value] >= 0.5
    # Scope selections are surfaced for audit, never silently merged.
    joined = " ".join(conflicts)
    assert "jurisdiction=EU" in joined
    assert "action_class=supplier_payment" in joined


# --------------------------------------------------------------------------
# Section7 — simulation before activation (dry run, never a real decision)
# --------------------------------------------------------------------------
def test_simulation_dry_run_no_real_decision():
    p = _clean_profile()
    baseline = lambda case: ExecutionDecision.DENY
    profile_fn = lambda case, prof: ExecutionDecision.ALLOW
    rep = simulate(p, ["study_x"], baseline, profile_fn)
    assert isinstance(rep, SimulationReport)
    assert rep.rejected is False
    assert "study_x" in rep.changed_decisions
    assert "study_x" in rep.reduced_controls


def test_simulation_rejects_weakened_invariant():
    p = _clean_profile()
    p.hard_rules = []  # removed all invariants -> weaker control
    rep = simulate(p, ["x"],
                   lambda c: ExecutionDecision.DENY,
                   lambda c, prof: ExecutionDecision.ALLOW)
    assert rep.rejected is True
    assert rep.reject_reason and "invariant" in rep.reject_reason


def test_simulation_rejects_expired_profile():
    p = _clean_profile()
    p.expiry_or_review_date = "2020-01-01"
    rep = simulate(p, ["x"],
                   lambda c: ExecutionDecision.DENY,
                   lambda c, prof: ExecutionDecision.ALLOW)
    assert rep.rejected is True
    assert rep.reject_reason == "profile expired"


# --------------------------------------------------------------------------
# Section8 — ACS receipt extension completeness
# --------------------------------------------------------------------------
def _full_stat_package() -> dict:
    ev = StatisticalProvenanceEvaluator()
    sig = ev.evaluate(_bad_record())
    g = ProvenanceGraph()
    g.add_node("sponsor_acme", NodeType.SPONSOR)
    return {
        "profile_id": "p1",
        "profile_version": "1.0.0",
        "profile_owner": "acme",
        "profile_approver": "human-owner",
        "applied_weights": {k.value: 0.5 for k in WeightKind},
        "hard_rules_triggered": [h.value for h in PLATFORM_INVARIANTS],
        "regulatory_minimums_applied": {"influence_risk": 0.1},
        "statistical_findings": {s.value: round(v, 3) for s, v in sig.signals.items()},
        "relationship_graph_summary": g.summary(),
        "vaig_decomposed_scores": {s.value: round(v, 3) for s, v in sig.signals.items()},
        "reht_decision": ExecutionDecision.DENY.value,
        "uncertainty": round(sig.unresolved_uncertainty, 3),
    }


def test_receipt_carries_statistical_provenance():
    r = Receipt(
        receipt_type="governance_decision",
        request_id="req-1", decision=ExecutionDecision.DENY,
        actor_id="acme", actor_role="system",
        statistical_provenance=_full_stat_package(),
    )
    d = r.to_dict()
    assert d["statistical_provenance"]["profile_id"] == "p1"
    assert d["statistical_provenance"]["reht_decision"] == "deny"
    # Round-trips through pydantic.
    r2 = Receipt(**d)
    assert r2.statistical_provenance["profile_owner"] == "acme"


def test_receipt_without_statistical_provenance_is_valid():
    # Backward compatible: field is optional.
    r = Receipt(
        receipt_type="governance_decision",
        request_id="req-2", decision=ExecutionDecision.ALLOW,
        actor_id="x", actor_role="system",
    )
    assert r.statistical_provenance is None
    assert r.to_dict()["statistical_provenance"] is None


# --------------------------------------------------------------------------
# Section9 — adversarial tests (research-capture manipulation)
# --------------------------------------------------------------------------
def test_adversarial_sponsor_owned_as_independent():
    # Sponsor controls publication + indirect funding presented as independent.
    r = _bad_record()
    out = StatisticalProvenanceEvaluator().evaluate(r)
    assert out.signals[StatisticalSignal.SPONSOR_CONTROL_RISK] >= 0.6
    assert StatisticalSignal.SPONSOR_CONTROL_RISK in out.flagged


def test_adversarial_indirect_foundation_funding():
    r = _bad_record()
    g = ProvenanceGraph()
    g.add_node("sponsor_acme", NodeType.SPONSOR)
    g.add_edge(RelationshipEdge(
        source="foundation_unknown", target="sponsor_acme",
        relationship_type=EdgeType.FUNDS, direct_or_indirect="indirect"))
    out = StatisticalProvenanceEvaluator().evaluate(r, g)
    assert out.signals[StatisticalSignal.SPONSOR_CONTROL_RISK] >= 0.6
    assert "graph" in out.notes


def test_adversarial_undisclosed_conflict():
    r = _bad_record()
    out = StatisticalProvenanceEvaluator().evaluate(r)
    assert out.signals[StatisticalSignal.CONFLICT_RISK] >= 0.6
    assert "author" in out.notes.get("conflict_risk", "")


def test_adversarial_endpoint_switching():
    r = StatisticalProvenanceRecord(
        commissioning_actor=CommissioningActor(actor_id="a"),
        study_risks=StudyDesignRiskRecord(endpoint_switching=True))
    out = StatisticalProvenanceEvaluator().evaluate(r)
    assert out.signals[StatisticalSignal.ENDPOINT_SWITCHING_RISK] >= 0.6


def test_adversarial_multiple_testing():
    r = StatisticalProvenanceRecord(
        commissioning_actor=CommissioningActor(actor_id="a"),
        study_risks=StudyDesignRiskRecord(multiple_testing=True))
    out = StatisticalProvenanceEvaluator().evaluate(r)
    assert out.signals[StatisticalSignal.MULTIPLE_TESTING_RISK] >= 0.6


def test_adversarial_publication_bias():
    r = StatisticalProvenanceRecord(
        commissioning_actor=CommissioningActor(actor_id="a"),
        study_risks=StudyDesignRiskRecord(publication_bias=True))
    out = StatisticalProvenanceEvaluator().evaluate(r)
    assert out.signals[StatisticalSignal.PUBLICATION_BIAS_RISK] >= 0.6


def test_adversarial_relative_risk_exaggeration():
    r = StatisticalProvenanceRecord(
        commissioning_actor=CommissioningActor(actor_id="a"),
        study_risks=StudyDesignRiskRecord(relative_vs_absolute=True))
    out = StatisticalProvenanceEvaluator().evaluate(r)
    assert out.signals[StatisticalSignal.PRESENTATION_MANIPULATION_RISK] >= 0.6


def test_adversarial_omitted_denominator():
    r = StatisticalProvenanceRecord(
        commissioning_actor=CommissioningActor(actor_id="a"),
        study_risks=StudyDesignRiskRecord(denominator_omission=True))
    out = StatisticalProvenanceEvaluator().evaluate(r)
    assert out.signals[StatisticalSignal.REPRESENTATIVENESS_RISK] >= 0.6


def test_adversarial_causal_from_correlation():
    r = StatisticalProvenanceRecord(
        commissioning_actor=CommissioningActor(actor_id="a"),
        study_risks=StudyDesignRiskRecord(causal_overclaim=True))
    out = StatisticalProvenanceEvaluator().evaluate(r)
    assert out.signals[StatisticalSignal.CAUSAL_OVERCLAIM_RISK] >= 0.6


def test_adversarial_panel_capture():
    r = StatisticalProvenanceRecord(
        commissioning_actor=CommissioningActor(actor_id="a"),
        conflicts=ConflictRecord(panel_conflict=True),
        study_risks=StudyDesignRiskRecord(guideline_capture=True))
    out = StatisticalProvenanceEvaluator().evaluate(r)
    assert out.signals[StatisticalSignal.POLICY_CAPTURE_RISK] >= 0.6


def test_adversarial_profile_zeroes_sponsor_control():
    # Customer tries to zero out sponsor-control risk weight.
    p = _clean_profile()
    p.weights[WeightKind.INFLUENCE_RISK] = 0.0
    ok, _, conflicts = ThreeLayerControl().validate(p)
    assert ok is False
    assert any("influence_risk" in c for c in conflicts)


def test_adversarial_profile_disables_provenance():
    p = _clean_profile()
    p.hard_rules = [h for h in p.hard_rules
                     if h != HardRule.PROVENANCE_RECORDED]
    ok, violations, _ = ThreeLayerControl().validate(p)
    assert ok is False
    assert any("provenance_recorded" in v for v in violations)


def test_adversarial_conflicting_org_and_action_class():
    p = _clean_profile()
    resolved, conflicts = PolicyPrecedenceResolver().resolve(
        p, jurisdiction=None, action_class="supplier_payment")
    joined = " ".join(conflicts)
    # Both scopes surfaced; no silent merge.
    assert "action_class=supplier_payment" in joined


def test_adversarial_expired_profile():
    p = _clean_profile()
    p.expiry_or_review_date = "2021-05-05"
    assert p.is_expired() is True
    rep = simulate(p, ["x"],
                   lambda c: ExecutionDecision.DENY,
                   lambda c, prof: ExecutionDecision.ALLOW)
    assert rep.rejected is True


def test_adversarial_rollback_target_recorded():
    p = _clean_profile()
    p.rollback_target = "1.0.0"
    p.change_reason = "quarterly review"
    assert p.rollback_target == "1.0.0"


def test_baro_never_issues_admissibility_decision():
    # BARO may weigh; it may never decide admissibility.
    p = _clean_profile()
    assert not hasattr(p, "decide")
    ev = StatisticalProvenanceEvaluator()
    assert ev.decides() is False


# --------------------------------------------------------------------------
# Section10/11 — end-to-end worked example (funded study -> signals -> profile -> receipt)
# --------------------------------------------------------------------------
def test_end_to_end_funded_study_to_receipt():
    record = _bad_record()
    graph = ProvenanceGraph()
    graph.add_node("sponsor_acme", NodeType.SPONSOR)
    graph.add_node("fund_alpha", NodeType.FUNDING_VEHICLE)
    graph.add_edge(RelationshipEdge(
        source="fund_alpha", target="sponsor_acme",
        relationship_type=EdgeType.FUNDS, direct_or_indirect="indirect"))

    sig = StatisticalProvenanceEvaluator().evaluate(record, graph)
    assert StatisticalSignal.SPONSOR_CONTROL_RISK in sig.flagged

    profile = _clean_profile()
    rep = simulate(profile, ["study_x"],
                   lambda c: ExecutionDecision.DENY,
                   lambda c, prof: ExecutionDecision.STEP_UP)
    assert "study_x" in rep.new_step_ups

    pkg = _full_stat_package()
    pkg["vaig_decomposed_scores"] = {
        s.value: round(v, 3) for s, v in sig.signals.items()}
    receipt = Receipt(
        receipt_type="governance_decision", request_id="req-e2e",
        decision=ExecutionDecision.DENY, actor_id="acme",
        actor_role="system", statistical_provenance=pkg)
    out = receipt.to_dict()
    assert out["statistical_provenance"]["profile_id"] == "p1"
    assert "vaig_decomposed_scores" in out["statistical_provenance"]
