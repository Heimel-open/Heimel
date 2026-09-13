"""Tests for GOS-001E: Governance OS to REHT/RACS runtime binding (#25)."""

import unittest

from lib.gos_reht_binding import (
    ActiveProfile,
    Assumption,
    BoardIntent,
    ClearanceReceipt,
    DelegationNode,
    EnterpriseMandate,
    EvidenceItem,
    ExecutionReceipt,
    GATE_ASSUMPTIONS_VALID,
    GATE_AUTHORITY_PATH_ACTIVE,
    GATE_CUMULATIVE_EXPOSURE,
    GATE_EVIDENCE_VALID,
    GATE_FAIL_CLOSED,
    GATE_MANDATE_VALID,
    GATE_PURPOSE_BOUND,
    GATE_RESERVED_ACTION,
    GATE_REVALIDATION,
    GosRehtBindingEngine,
    GovernancePurpose,
    HumanRatification,
    MissingClearanceError,
    MissingExecutionError,
    OutcomeReceipt,
    REVALIDATED_STALE,
    RehtContext,
    ReceiptChainOrderError,
    digest,
)


def _purpose(**overrides) -> GovernancePurpose:
    data = {
        "purpose_id": "purpose-1",
        "content_digest": "purpose-content-1",
        "version": 1,
    }
    data.update(overrides)
    return GovernancePurpose(**data)


def _intent(**overrides) -> BoardIntent:
    data = {
        "intent_id": "intent-1",
        "purpose_ref": "purpose-1",
        "description": "procure and pay suppliers",
        "reserved_actions": (),
        "assumptions": ("assumption-1",),
        "scope_actions": ("procure", "pay"),
    }
    data.update(overrides)
    return BoardIntent(**data)


def _mandate(**overrides) -> EnterpriseMandate:
    data = {
        "mandate_id": "mandate-1",
        "principal": "nsolland",
        "grantee": "agent-1",
        "scope_actions": ("procure", "pay"),
        "assumptions": ("assumption-1",),
        "state": "active",
    }
    data.update(overrides)
    return EnterpriseMandate(**data)


def _delegations(*nodes: dict) -> tuple[DelegationNode, ...]:
    return tuple(DelegationNode(**node) for node in nodes)


def _delegation(**overrides) -> DelegationNode:
    data = {
        "delegation_id": "deleg-1",
        "granter": "nsolland",
        "grantee": "agent-1",
        "authority_scope": ("procure", "pay"),
        "weight_pct": 100,
        "exposure_units": 10,
        "state": "active",
    }
    data.update(overrides)
    return DelegationNode(**data)


def _evidence(**overrides) -> tuple[EvidenceItem, ...]:
    data = {
        "evidence_id": "ev-1",
        "state": "valid",
        "content_digest": "evidence-content-1",
        "mandatory": True,
    }
    data.update(overrides)
    return (EvidenceItem(**data),)


def _assumptions(**overrides) -> tuple[Assumption, ...]:
    data = {
        "assumption_id": "assumption-1",
        "state": "valid",
        "content_digest": "assumption-content-1",
        "mandatory": True,
    }
    data.update(overrides)
    return (Assumption(**data),)


def _profiles() -> tuple[ActiveProfile, ...]:
    return (ActiveProfile("profile-a", "profile-content-1",
                          weights=(("risk_weight", 20),)),)


def _context(**overrides) -> RehtContext:
    data = {
        "purpose": _purpose(),
        "intent": _intent(),
        "mandate": _mandate(),
        "delegation_path": (_delegation(),),
        "evidence": _evidence(),
        "assumptions": _assumptions(),
        "active_profiles": _profiles(),
        "ratifications": (),
        "exposure_limit_units": 50,
        "elevation_enabled": False,
        "agent": "agent-1",
    }
    data.update(overrides)
    return GosRehtBindingEngine.assemble_context(**data)


def _action(**overrides) -> dict:
    data = {"action": "procure", "item": "widgets", "value_minor": 100}
    data.update(overrides)
    return data


PROVENANCE = ("purpose-1", "intent-1", "mandate-1", "deleg-1", "agent-1")


class ContextAssemblyTest(unittest.TestCase):
    def test_provenance_chain(self):
        ctx = _context()
        self.assertEqual(ctx.provenance_chain, PROVENANCE)

    def test_cumulative_exposure_weighted(self):
        ctx = _context(
            delegation_path=_delegations(
                {"delegation_id": "d-1", "granter": "nsolland",
                 "grantee": "mid-1", "authority_scope": ("procure", "pay"),
                 "weight_pct": 100, "exposure_units": 40},
                {"delegation_id": "d-2", "granter": "mid-1",
                 "grantee": "agent-1", "authority_scope": ("procure", "pay"),
                 "weight_pct": 50, "exposure_units": 40},
            ),
            agent="agent-1",
        )
        self.assertEqual(ctx.cumulative_exposure_units, 60)

    def test_context_digest_deterministic(self):
        a = _context()
        b = _context()
        self.assertEqual(a.context_digest(), b.context_digest())

    def test_engine_has_no_authority_surface(self):
        engine = GosRehtBindingEngine()
        self.assertFalse(engine.has_authority_surface)
        self.assertFalse(engine.has_execution_surface)
        for attr in ("authorize", "execute", "clear"):
            self.assertFalse(hasattr(engine, attr))


class AllowTest(unittest.TestCase):
    def test_allow_issues_clearance_and_receipt(self):
        engine = GosRehtBindingEngine()
        result = engine.evaluate(_action(), _context())
        self.assertEqual(result.racs_outcome, "ALLOW")
        self.assertTrue(result.clearance_receipt_ref.startswith("clr-"))
        self.assertEqual(engine.clearance_count, 1)

    def test_allow_decisive_gates(self):
        engine = GosRehtBindingEngine()
        result = engine.evaluate(_action(), _context())
        self.assertIn(GATE_PURPOSE_BOUND, result.decisive_gates)
        self.assertIn(GATE_MANDATE_VALID, result.decisive_gates)
        self.assertIn(GATE_AUTHORITY_PATH_ACTIVE, result.decisive_gates)
        self.assertIn(GATE_EVIDENCE_VALID, result.decisive_gates)
        self.assertIn(GATE_ASSUMPTIONS_VALID, result.decisive_gates)
        self.assertIn(GATE_CUMULATIVE_EXPOSURE, result.decisive_gates)

    def test_action_outside_mandate_scope_denied(self):
        engine = GosRehtBindingEngine()
        result = engine.evaluate(_action(action="hire"), _context())
        self.assertEqual(result.racs_outcome, "DENY")
        self.assertEqual(result.decisive_gates, (GATE_MANDATE_VALID,))

    def test_revoked_delegation_denied(self):
        engine = GosRehtBindingEngine()
        ctx = _context(delegation_path=(_delegation(state="revoked"),))
        result = engine.evaluate(_action(), ctx)
        self.assertEqual(result.racs_outcome, "DENY")
        self.assertEqual(result.decisive_gates, (GATE_AUTHORITY_PATH_ACTIVE,))

    def test_delegation_only_narrows(self):
        engine = GosRehtBindingEngine()
        ctx = _context(
            delegation_path=_delegations(
                {"delegation_id": "d-1", "granter": "nsolland",
                 "grantee": "mid-1", "authority_scope": ("procure", "pay"),
                 "weight_pct": 100, "exposure_units": 0},
                {"delegation_id": "d-2", "granter": "mid-1",
                 "grantee": "agent-1",
                 "authority_scope": ("procure", "pay", "hire"),
                 "weight_pct": 100, "exposure_units": 0},
            ),
            agent="agent-1",
        )
        result = engine.evaluate(_action(), ctx)
        self.assertEqual(result.racs_outcome, "DENY")
        self.assertEqual(result.decisive_gates, (GATE_AUTHORITY_PATH_ACTIVE,))


class StaleClearanceInvalidationTest(unittest.TestCase):
    def _cleared(self, engine):
        result = engine.evaluate(_action(), _context())
        self.assertEqual(result.racs_outcome, "ALLOW")
        return result

    def test_changed_mandate_invalidates_prior_clearance(self):
        engine = GosRehtBindingEngine()
        result = self._cleared(engine)
        new_ctx = _context(mandate=_mandate(scope_actions=("procure",)))
        recheck = engine.evaluate(
            _action(), new_ctx, prior_clearance_id=result.clearance_receipt_ref
        )
        self.assertEqual(recheck.racs_outcome, "DEFER")
        self.assertEqual(recheck.decisive_gates, (GATE_REVALIDATION,))
        self.assertIn("mandate", recheck.revalidation.changed)
        self.assertEqual(recheck.revalidation.status, REVALIDATED_STALE)

    def test_changed_evidence_invalidates_prior_clearance(self):
        engine = GosRehtBindingEngine()
        result = self._cleared(engine)
        new_ctx = _context(
            evidence=_evidence(content_digest="evidence-content-2")
        )
        recheck = engine.evaluate(
            _action(), new_ctx, prior_clearance_id=result.clearance_receipt_ref
        )
        self.assertEqual(recheck.racs_outcome, "DEFER")
        self.assertIn("evidence", recheck.revalidation.changed)

    def test_changed_assumptions_invalidate_prior_clearance(self):
        engine = GosRehtBindingEngine()
        result = self._cleared(engine)
        new_ctx = _context(
            assumptions=_assumptions(content_digest="assumption-content-2")
        )
        recheck = engine.evaluate(
            _action(), new_ctx, prior_clearance_id=result.clearance_receipt_ref
        )
        self.assertEqual(recheck.racs_outcome, "DEFER")
        self.assertIn("assumptions", recheck.revalidation.changed)

    def test_unchanged_clearance_remains_cleared(self):
        engine = GosRehtBindingEngine()
        result = self._cleared(engine)
        recheck = engine.evaluate(
            _action(), _context(), prior_clearance_id=result.clearance_receipt_ref
        )
        self.assertEqual(recheck.racs_outcome, "ALLOW")

    def test_stale_clearance_tracked(self):
        engine = GosRehtBindingEngine()
        result = self._cleared(engine)
        engine.evaluate(
            _action(),
            _context(mandate=_mandate(scope_actions=("procure",))),
            prior_clearance_id=result.clearance_receipt_ref,
        )
        stale = engine.stale_clearances
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0].clearance_ref, result.clearance_receipt_ref)


class ReservedActionTest(unittest.TestCase):
    def test_reserved_action_steps_up_with_elevation(self):
        engine = GosRehtBindingEngine()
        ctx = _context(
            intent=_intent(reserved_actions=("contract_signature",)),
            elevation_enabled=True,
        )
        result = engine.evaluate(_action(action="contract_signature"), ctx)
        self.assertEqual(result.racs_outcome, "STEP_UP")
        self.assertEqual(result.decisive_gates, (GATE_RESERVED_ACTION,))
        self.assertEqual(engine.clearance_count, 0)

    def test_reserved_action_denied_without_elevation(self):
        engine = GosRehtBindingEngine()
        ctx = _context(intent=_intent(reserved_actions=("contract_signature",)))
        result = engine.evaluate(_action(action="contract_signature"), ctx)
        self.assertEqual(result.racs_outcome, "DENY")
        self.assertEqual(result.decisive_gates, (GATE_RESERVED_ACTION,))

    def test_reserved_action_human_ratified_allows(self):
        engine = GosRehtBindingEngine()
        action = _action(action="contract_signature")
        ctx = _context(
            intent=_intent(reserved_actions=("contract_signature",)),
            mandate=_mandate(scope_actions=("procure", "pay", "contract_signature")),
            ratifications=(HumanRatification(
                "rat-1", digest(action), "nsolland", "purpose-1"
            ),),
        )
        result = engine.evaluate(action, ctx)
        self.assertEqual(result.racs_outcome, "ALLOW")
        self.assertEqual(result.decisive_gates[0], GATE_RESERVED_ACTION)


class CumulativeExposureTest(unittest.TestCase):
    def test_exposure_within_limit_allows(self):
        engine = GosRehtBindingEngine()
        ctx = _context(
            delegation_path=_delegations(
                {"delegation_id": "d-1", "granter": "nsolland",
                 "grantee": "mid-1", "authority_scope": ("procure", "pay"),
                 "weight_pct": 100, "exposure_units": 40},
                {"delegation_id": "d-2", "granter": "mid-1",
                 "grantee": "agent-1", "authority_scope": ("procure", "pay"),
                 "weight_pct": 100, "exposure_units": 40},
            ),
            exposure_limit_units=80,
            agent="agent-1",
        )
        result = engine.evaluate(_action(), ctx)
        self.assertEqual(result.racs_outcome, "ALLOW")

    def test_cumulative_exposure_exceeded_denies(self):
        engine = GosRehtBindingEngine()
        ctx = _context(
            delegation_path=_delegations(
                {"delegation_id": "d-1", "granter": "nsolland",
                 "grantee": "mid-1", "authority_scope": ("procure", "pay"),
                 "weight_pct": 100, "exposure_units": 40},
                {"delegation_id": "d-2", "granter": "mid-1",
                 "grantee": "agent-1", "authority_scope": ("procure", "pay"),
                 "weight_pct": 100, "exposure_units": 40},
            ),
            exposure_limit_units=50,
            agent="agent-1",
        )
        result = engine.evaluate(_action(), ctx)
        self.assertEqual(result.racs_outcome, "DENY")
        self.assertEqual(result.decisive_gates, (GATE_CUMULATIVE_EXPOSURE,))
        self.assertEqual(result.cumulative_exposure_units, 80)


class UnknownStateFailClosedTest(unittest.TestCase):
    def test_unknown_evidence_state_never_allows(self):
        engine = GosRehtBindingEngine()
        ctx = _context(evidence=_evidence(state="mystery"))
        result = engine.evaluate(_action(), ctx)
        self.assertNotEqual(result.racs_outcome, "ALLOW")
        self.assertIn(result.racs_outcome, ("DEFER", "STEP_UP"))
        self.assertEqual(result.decisive_gates, (GATE_FAIL_CLOSED,))

    def test_unknown_assumption_state_never_allows(self):
        engine = GosRehtBindingEngine()
        ctx = _context(assumptions=_assumptions(state="mystery"))
        result = engine.evaluate(_action(), ctx)
        self.assertNotEqual(result.racs_outcome, "ALLOW")
        self.assertEqual(result.decisive_gates, (GATE_FAIL_CLOSED,))

    def test_unknown_mandate_state_never_allows(self):
        engine = GosRehtBindingEngine()
        ctx = _context(mandate=_mandate(state="mystery"))
        result = engine.evaluate(_action(), ctx)
        self.assertNotEqual(result.racs_outcome, "ALLOW")
        self.assertEqual(result.decisive_gates, (GATE_FAIL_CLOSED,))

    def test_unknown_state_steps_up_when_elevation_enabled(self):
        engine = GosRehtBindingEngine()
        ctx = _context(
            evidence=_evidence(state="mystery"), elevation_enabled=True
        )
        result = engine.evaluate(_action(), ctx)
        self.assertEqual(result.racs_outcome, "STEP_UP")
        self.assertEqual(engine.clearance_count, 0)

    def test_stale_evidence_defers(self):
        engine = GosRehtBindingEngine()
        ctx = _context(evidence=_evidence(state="stale"))
        result = engine.evaluate(_action(), ctx)
        self.assertEqual(result.racs_outcome, "DEFER")
        self.assertEqual(result.decisive_gates, (GATE_EVIDENCE_VALID,))

    def test_expired_mandate_defers(self):
        engine = GosRehtBindingEngine()
        ctx = _context(mandate=_mandate(state="expired"))
        result = engine.evaluate(_action(), ctx)
        self.assertEqual(result.racs_outcome, "DEFER")
        self.assertEqual(result.decisive_gates, (GATE_MANDATE_VALID,))


class ReceiptSeparationTest(unittest.TestCase):
    def _receipt_chain(self):
        engine = GosRehtBindingEngine()
        result = engine.evaluate(_action(), _context())
        self.assertEqual(result.racs_outcome, "ALLOW")
        clearance = engine._clearance_receipts[result.clearance_receipt_ref]
        execution = engine.record_execution(
            result.action_digest, result.clearance_receipt_ref
        )
        outcome = engine.record_outcome(
            execution.receipt_id, realized="success"
        )
        return engine, result, clearance, execution, outcome

    def test_clearance_execution_outcome_receipts_stay_separate(self):
        _, _, clearance, execution, outcome = self._receipt_chain()
        refs = {clearance.receipt_id, execution.receipt_id, outcome.receipt_id}
        self.assertEqual(len(refs), 3)
        kinds = {clearance.receipt_kind, execution.receipt_kind,
                 outcome.receipt_kind}
        self.assertEqual(kinds, {"clearance", "execution", "outcome"})

    def test_receipts_chain_by_reference(self):
        _, _, clearance, execution, outcome = self._receipt_chain()
        self.assertEqual(execution.clearance_receipt_ref, clearance.receipt_id)
        self.assertEqual(outcome.execution_receipt_ref, execution.receipt_id)
        self.assertEqual(outcome.clearance_receipt_ref, clearance.receipt_id)

    def test_receipt_digests_distinct(self):
        _, _, clearance, execution, outcome = self._receipt_chain()
        digests = {clearance.digest(), execution.digest(), outcome.digest()}
        self.assertEqual(len(digests), 3)

    def test_receipts_identify_gates_profiles_provenance(self):
        _, _, clearance, execution, outcome = self._receipt_chain()
        for receipt in (clearance, execution, outcome):
            self.assertEqual(receipt.active_profiles, ("profile-a",))
            self.assertEqual(receipt.provenance_chain, PROVENANCE)
            self.assertIn(GATE_CUMULATIVE_EXPOSURE, receipt.decisive_gates)
        self.assertIsInstance(clearance, ClearanceReceipt)
        self.assertIsInstance(execution, ExecutionReceipt)
        self.assertIsInstance(outcome, OutcomeReceipt)

    def test_execution_requires_clearance(self):
        engine = GosRehtBindingEngine()
        with self.assertRaises(MissingClearanceError):
            engine.record_execution(digest(_action()), "clr-nope")

    def test_execution_must_match_cleared_action(self):
        engine = GosRehtBindingEngine()
        result = engine.evaluate(_action(), _context())
        with self.assertRaises(ReceiptChainOrderError):
            engine.record_execution(
                digest(_action(action="other")), result.clearance_receipt_ref
            )

    def test_outcome_requires_execution(self):
        engine = GosRehtBindingEngine()
        with self.assertRaises(MissingExecutionError):
            engine.record_outcome("exe-nope", realized="success")

    def test_no_receipt_without_allow(self):
        engine = GosRehtBindingEngine()
        result = engine.evaluate(_action(action="hire"), _context())
        self.assertEqual(result.racs_outcome, "DENY")
        self.assertEqual(result.clearance_receipt_ref, "")
        self.assertEqual(engine.clearance_count, 0)

    def test_counts_track_separate_receipts(self):
        engine, _, _, _, _ = self._receipt_chain()
        self.assertEqual(engine.clearance_count, 1)
        self.assertEqual(engine.execution_count, 1)
        self.assertEqual(engine.outcome_count, 1)


class DeterministicDigestTest(unittest.TestCase):
    def test_result_digest_deterministic(self):
        engine_a = GosRehtBindingEngine()
        engine_b = GosRehtBindingEngine()
        a = engine_a.evaluate(_action(), _context())
        b = engine_b.evaluate(_action(), _context())
        self.assertEqual(a.digest(), b.digest())
        self.assertEqual(len(a.digest()), 64)

    def test_result_digest_differs_for_different_action(self):
        engine = GosRehtBindingEngine()
        a = engine.evaluate(_action(), _context())
        b = engine.evaluate(_action(value_minor=999), _context())
        self.assertNotEqual(a.digest(), b.digest())

    def test_result_digest_differs_for_different_context(self):
        engine = GosRehtBindingEngine()
        a = engine.evaluate(_action(), _context())
        b = engine.evaluate(
            _action(), _context(mandate=_mandate(scope_actions=("procure",)))
        )
        self.assertNotEqual(a.digest(), b.digest())


if __name__ == "__main__":
    unittest.main()
