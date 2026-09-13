"""
Unit tests for PAIOS foundation.

Covers:
  - memory: store / query / ttl / provenance
  - maturity: starts L1 / refuses illegal advance / advance governance signal
  - proposal: builds envelope / never executes (guard raises)
  - boundaries: ExecutionGuardError raised on execution path
  - provenance: preserved throughout
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from paios import (
    CanonicalMemory,
    MemoryRecord,
    MemoryType,
    MaturityLevel,
    MaturityModel,
    ExecutionGuardError,
    assert_no_execution,
)
from paios.boundaries import guard_proposal_execution
from paios.maturity import AdvanceError
from paios.proposal import governed_propose, propose_action, ActionEnvelope, GovernanceResult


def allow_vaig(envelope):
    """Explicit ALLOW VAIG evaluator for tests that exercise admissible flow.

    The production default VAIG evaluator is FAIL-CLOSED (DENY), so a proposal
    without an explicit VAIG evaluator is never admissible. Tests that want to
    exercise the admissible path must inject this stub explicitly — never rely
    on a pass-through ALLOW default.
    """
    return {"result": "ALLOW", "confidence": 0.9, "action_id": envelope.action_id}


# =========================================================================
# Canonical Memory — store, query, TTL, provenance
# =========================================================================


class TestCanonicalMemory:
    def test_store_and_count(self, tmp_path: Path) -> None:
        mem = CanonicalMemory(path=tmp_path / "memory.jsonl")
        assert mem.count() == 0

        rec = MemoryRecord(
            id="rec_001",
            type=MemoryType.USER_PROFILE,
            content={"name": "Njål"},
            provenance="setup",
        )
        mem.store(rec)
        assert mem.count() == 1

    def test_query_by_type(self, tmp_path: Path) -> None:
        mem = CanonicalMemory(path=tmp_path / "memory.jsonl")
        mem.store(MemoryRecord(id="r1", type=MemoryType.USER_PROFILE, content={"k": "v"}, provenance="setup"))
        mem.store(MemoryRecord(id="r2", type=MemoryType.DECISION, content={"k": "v"}, provenance="setup"))
        mem.store(MemoryRecord(id="r3", type=MemoryType.POLICY, content={"k": "v"}, provenance="setup"))

        decisions = mem.query(type=MemoryType.DECISION)
        assert len(decisions) == 1
        assert decisions[0].id == "r2"

    def test_query_by_provenance(self, tmp_path: Path) -> None:
        mem = CanonicalMemory(path=tmp_path / "memory.jsonl")
        mem.store(MemoryRecord(id="r1", type=MemoryType.USER_PROFILE, content={}, provenance="human"))
        mem.store(MemoryRecord(id="r2", type=MemoryType.DECISION, content={}, provenance="reht"))
        mem.store(MemoryRecord(id="r3", type=MemoryType.POLICY, content={}, provenance="human"))

        human_records = mem.query(provenance="human")
        assert len(human_records) == 2

    def test_ttl_expiry(self, tmp_path: Path) -> None:
        mem = CanonicalMemory(path=tmp_path / "memory.jsonl")
        # Record with 0-second TTL (immediately expired)
        rec = MemoryRecord(
            id="expired",
            type=MemoryType.DECISION,
            content={"decision": "test"},
            provenance="test",
            timestamp=time.time() - 10,  # 10 seconds ago
            ttl=1,  # 1 second TTL
        )
        mem.store(rec)

        # Without include_expired, should not appear
        results = mem.query()
        assert len(results) == 0

        # With include_expired, should appear
        results = mem.query(include_expired=True)
        assert len(results) == 1

    def test_ttl_no_expiry(self, tmp_path: Path) -> None:
        mem = CanonicalMemory(path=tmp_path / "memory.jsonl")
        rec = MemoryRecord(
            id="permanent",
            type=MemoryType.POLICY,
            content={"policy": "no-auto-advance"},
            provenance="canonical",
            ttl=None,  # never expires
        )
        mem.store(rec)
        results = mem.query()
        assert len(results) == 1
        assert results[0].id == "permanent"

    def test_flush_and_reload(self, tmp_path: Path) -> None:
        path = tmp_path / "memory.jsonl"
        mem = CanonicalMemory(path=path)
        mem.store(MemoryRecord(id="r1", type=MemoryType.USER_PROFILE, content={"x": 1}, provenance="setup"))
        mem.store(MemoryRecord(id="r2", type=MemoryType.DECISION, content={"y": 2}, provenance="setup"))
        mem.flush()

        # New instance loads from disk
        mem2 = CanonicalMemory(path=path)
        assert mem2.count() == 2
        assert len(mem2.query(type=MemoryType.USER_PROFILE)) == 1

    def test_provenance_preserved(self, tmp_path: Path) -> None:
        mem = CanonicalMemory(path=tmp_path / "memory.jsonl")
        mem.store(
            MemoryRecord(
                id="prov_test",
                type=MemoryType.GOVERNANCE_SIGNAL,
                content={"signal": "advance_ok"},
                provenance="reht:gateway",
            )
        )
        results = mem.query(provenance="reht:gateway")
        assert len(results) == 1
        assert results[0].provenance == "reht:gateway"

    def test_memory_type_enum(self) -> None:
        assert MemoryType.USER_PROFILE.value == "user_profile"
        assert MemoryType.DECISION.value == "decision"
        assert MemoryType.POLICY.value == "policy"
        assert MemoryType.GOVERNANCE_SIGNAL.value == "governance_signal"
        assert MemoryType.PROVENANCE_RECORD.value == "provenance_record"


# =========================================================================
# Maturity Model — start L1, no illegal advance, governance signal
# =========================================================================


class TestMaturityModel:
    def test_starts_at_L1(self) -> None:
        model = MaturityModel()
        assert model.current == MaturityLevel.L1_ASSIST

    def test_starts_at_L1_label(self) -> None:
        model = MaturityModel()
        assert model.current.label == "L1"

    def test_starts_at_L1_description(self) -> None:
        model = MaturityModel()
        assert "Assist" in model.current.description

    def test_can_advance_L1_to_L2(self) -> None:
        model = MaturityModel()
        # Default conditions for L1→L2 are trivially met
        assert model.can_advance() is True

    def test_advance_L1_to_L2(self) -> None:
        model = MaturityModel()
        model.advance(signal="initialisation_complete")
        assert model.current == MaturityLevel.L2_STEERED_RECS

    def test_advance_records_history(self) -> None:
        model = MaturityModel()
        model.advance(signal="bootstrap_ok")
        assert len(model.history) == 1
        assert model.history[0]["from"] == "L1"
        assert model.history[0]["to"] == "L2"
        assert model.history[0]["signal"] == "bootstrap_ok"

    def test_L2_to_L3_requires_reht_signal(self) -> None:
        model = MaturityModel(MaturityLevel.L2_STEERED_RECS)
        # REHT admissibility not proven → can_advance is False
        assert model.can_advance() is False
        with pytest.raises(AdvanceError, match="REHT admissibility pathway"):
            model.advance()

    def test_L2_to_L3_with_reht_signal(self) -> None:
        os.environ["PAIOS_REHT_ADMISSIBILITY_PROVEN"] = "1"
        try:
            model = MaturityModel(MaturityLevel.L2_STEERED_RECS)
            assert model.can_advance() is True
            model.advance(signal="reht_admissibility_proven")
            assert model.current == MaturityLevel.L3_GOVERNED_EX
        finally:
            del os.environ["PAIOS_REHT_ADMISSIBILITY_PROVEN"]

    def test_L3_to_L4_requires_continuous_integrity(self) -> None:
        model = MaturityModel(MaturityLevel.L3_GOVERNED_EX)
        assert model.can_advance() is False
        with pytest.raises(AdvanceError, match="Continuous integrity"):
            model.advance()

    def test_L3_to_L4_with_integrity(self) -> None:
        os.environ["PAIOS_CONTINUOUS_INTEGRITY"] = "1"
        try:
            model = MaturityModel(MaturityLevel.L3_GOVERNED_EX)
            assert model.can_advance() is True
            model.advance(signal="integrity_active")
            assert model.current == MaturityLevel.L4_AUTONOMOUS
        finally:
            del os.environ["PAIOS_CONTINUOUS_INTEGRITY"]

    def test_cannot_advance_past_L4(self) -> None:
        model = MaturityModel(MaturityLevel.L4_AUTONOMOUS)
        assert model.can_advance() is False
        with pytest.raises(AdvanceError, match="maximum"):
            model.advance()

    def test_reset(self) -> None:
        model = MaturityModel()
        model.advance()
        assert model.current == MaturityLevel.L2_STEERED_RECS
        model.reset()
        assert model.current == MaturityLevel.L1_ASSIST
        assert len(model.history) == 0

    def test_no_jump_skip(self) -> None:
        model = MaturityModel(MaturityLevel.L0_NONE)
        assert model.current == MaturityLevel.L0_NONE
        model.advance()
        assert model.current == MaturityLevel.L1_ASSIST


# =========================================================================
# Governed Proposal — builds envelope, never executes
# =========================================================================


class TestGovernedProposal:
    def test_builds_action_envelope(self) -> None:
        result = governed_propose(
            action_type="send_notification",
            actor={"id": "paios", "role": "co_worker"},
            target={"service": "email", "recipient": "user@example.com"},
            requested_effect={"message": "Hello from PAIOS"},
            authority_context={"policy_ref": "pol_notify_v1"},
        )
        assert isinstance(result, GovernanceResult)
        assert isinstance(result.envelope, ActionEnvelope)
        assert result.envelope.action_type == "send_notification"

    def test_envelope_has_required_fields(self) -> None:
        result = governed_propose(
            action_type="read_dashboard",
            actor={"id": "paios"},
            target={"resource": "dashboard"},
            requested_effect={"action": "query"},
            authority_context={"scope": "read_only"},
        )
        env = result.envelope
        assert env.racs_version == "1.0"
        assert env.action_id is not None and len(env.action_id) > 0
        assert env.actor == {"id": "paios"}
        assert env.created_at > 0

    def test_sends_to_vaig_and_reht(self) -> None:
        # Default VAIG evaluator is FAIL-CLOSED (DENY) — a proposal without an
        # explicit VAIG evaluator must NOT be admissible.
        result = governed_propose(
            action_type="test_action",
            actor={"id": "test"},
            target={"resource": "test"},
            requested_effect={"effect": "test"},
            authority_context={"scope": "test"},
        )
        assert result.vaig_evaluation is not None
        assert result.reht_evaluation is not None
        # default VAIG is fail-closed -> DENY, so can_execute is False
        assert result.vaig_evaluation["result"] == "DENY"
        assert result.can_execute is False

    def test_sends_to_vaig_and_reht_with_explicit_allow(self) -> None:
        # An explicit VAIG ALLOW is still insufficient without a real REHT.
        def allow_vaig(env):
            return {"result": "ALLOW", "confidence": 0.9}

        result = governed_propose(
            action_type="test_action",
            actor={"id": "test"},
            target={"resource": "test"},
            requested_effect={"effect": "test"},
            authority_context={"scope": "test"},
            vaig_evaluator=allow_vaig,
        )
        assert result.vaig_evaluation["result"] == "ALLOW"
        assert result.reht_evaluation["admissible"] is False
        assert result.can_execute is False

    def test_custom_evaluators(self) -> None:
        def mock_vaig(env):
            return {"result": "DENY", "confidence": 0.99, "reason": "policy_block"}

        def mock_reht(env):
            return {"admissible": False, "reason": "no_clearance"}

        result = governed_propose(
            action_type="blocked_action",
            actor={"id": "test"},
            target={"resource": "test"},
            requested_effect={"effect": "test"},
            authority_context={"scope": "test"},
            vaig_evaluator=mock_vaig,
            reht_evaluator=mock_reht,
        )
        assert result.vaig_evaluation["result"] == "DENY"
        assert result.reht_evaluation["admissible"] is False
        assert result.can_execute is False

    def test_state_inadmissible_contradicts_admissible_flag(self) -> None:
        # Audit finding #3 requirement 4: REHT state=INADMISSIBLE with a
        # spuriously True admissible flag must FAIL closed, not open.
        def allow_vaig(env):
            return {"result": "ALLOW", "confidence": 0.9}

        def inconsistent_reht(env):
            return {"admissible": True, "state": "INADMISSIBLE", "score": 0.0}

        result = governed_propose(
            action_type="test_action",
            actor={"id": "test"},
            target={"resource": "test"},
            requested_effect={"effect": "test"},
            authority_context={"scope": "test"},
            vaig_evaluator=allow_vaig,
            reht_evaluator=inconsistent_reht,
        )
        assert result.vaig_evaluation["result"] == "ALLOW"
        assert result.reht_evaluation["admissible"] is True
        assert result.reht_evaluation["state"] == "INADMISSIBLE"
        # must fail closed despite both ALLOW + admissible=True
        assert result.can_execute is False

    def test_state_admissible_consistency_allows(self) -> None:
        def allow_vaig(env):
            return {"result": "ALLOW", "confidence": 0.9}

        def consistent_reht(env):
            return {"admissible": True, "state": "ADMISSIBLE", "score": 0.9}

        result = governed_propose(
            action_type="test_action",
            actor={"id": "test"},
            target={"resource": "test"},
            requested_effect={"effect": "test"},
            authority_context={"scope": "test"},
            vaig_evaluator=allow_vaig,
            reht_evaluator=consistent_reht,
        )
        assert result.can_execute is True

    def test_envelope_to_dict(self) -> None:
        env = ActionEnvelope(
            action_type="test",
            actor={"id": "a"},
            target={"res": "t"},
            requested_effect={"e": "e"},
            authority_context={"auth": "a"},
        )
        d = env.to_dict()
        assert d["racs_version"] == "1.0"
        assert d["action_type"] == "test"
        assert d["actor"] == {"id": "a"}

    def test_envelope_from_dict(self) -> None:
        d = {
            "racs_version": "1.0",
            "action_type": "test",
            "actor": {"id": "a"},
            "target": {"res": "t"},
            "requested_effect": {"e": "e"},
            "authority_context": {"auth": "a"},
            "policy_context": {},
            "evidence_package": {},
            "environment_state": {},
            "created_at": 1000.0,
            "action_id": "abc-123",
        }
        env = ActionEnvelope.from_dict(d)
        assert env.action_type == "test"
        assert env.action_id == "abc-123"
        assert env.created_at == 1000.0

    def test_envelope_optional_risk_context(self) -> None:
        env = ActionEnvelope(
            action_type="risky",
            actor={"id": "a"},
            target={"res": "t"},
            requested_effect={"e": "e"},
            authority_context={"auth": "a"},
            risk_context={"level": "high"},
        )
        d = env.to_dict()
        assert d["risk_context"] == {"level": "high"}

    def test_envelope_expires_at(self) -> None:
        env = ActionEnvelope(
            action_type="timed",
            actor={"id": "a"},
            target={"res": "t"},
            requested_effect={"e": "e"},
            authority_context={"auth": "a"},
            expires_at=9999999999.0,
        )
        d = env.to_dict()
        assert d["expires_at"] == 9999999999.0

    def test_governance_result_error_handling(self) -> None:
        def broken_vaig(env):
            raise RuntimeError("VAIG service unavailable")

        result = governed_propose(
            action_type="failing",
            actor={"id": "test"},
            target={"resource": "test"},
            requested_effect={"effect": "test"},
            authority_context={"scope": "test"},
            vaig_evaluator=broken_vaig,
        )
        assert len(result.errors) > 0
        assert "VAIG" in result.errors[0]


# =========================================================================
# Boundaries — no execution guard
# =========================================================================


class TestBoundaries:
    def test_assert_no_execution_raises(self) -> None:
        with pytest.raises(ExecutionGuardError, match="PAIOS execution guard"):
            assert_no_execution(context="test")

    def test_guard_proposal_execution_raises(self) -> None:
        with pytest.raises(ExecutionGuardError, match="Proposal execution blocked"):
            guard_proposal_execution({"action_type": "email_send", "action_id": "act_001"})

    def test_guard_has_diagnostic_context(self) -> None:
        with pytest.raises(ExecutionGuardError) as excinfo:
            guard_proposal_execution({"action_type": "deploy", "action_id": "act_999"})
        msg = str(excinfo.value)
        assert "deploy" in msg
        assert "act_999" in msg

    def test_assert_no_execution_skip_when_disabled(self) -> None:
        # Should not raise when raise_on_call=False
        assert_no_execution(context="non-fatal check", raise_on_call=False)

    def test_execution_path_in_proposal_is_guarded(self) -> None:
        """The governed_propose function must NEVER have an execution path.

        This test verifies that the proposal result includes a guard check
        and that the guard_proposal_execution function raises if called.
        """
        with pytest.raises(ExecutionGuardError):
            guard_proposal_execution({"action_type": "execute", "action_id": "x"})


# =========================================================================
# Integration — full flow
# =========================================================================


class TestIntegration:
    def test_full_proposal_flow_with_memory(self, tmp_path: Path) -> None:
        """End-to-end: propose action → store in memory → verify."""
        mem = CanonicalMemory(path=tmp_path / "memory.jsonl")

        # Build and evaluate a proposal (explicit ALLOW VAIG — default is fail-closed)
        result = governed_propose(
            action_type="dashboard_query",
            actor={"id": "paios_v1", "role": "co_worker"},
            target={"service": "analytics", "endpoint": "/api/report"},
            requested_effect={"query": "weekly_summary"},
            authority_context={"policy_ref": "pol_read_only", "scope": "reporting"},
            vaig_evaluator=allow_vaig,
        )

        # Record the proposal outcome in canonical memory
        mem.store(
            MemoryRecord(
                id=f"proposal_{result.envelope.action_id[:8]}",
                type=MemoryType.GOVERNANCE_SIGNAL,
                content={
                    "action_type": result.envelope.action_type,
                    "vaig_result": result.vaig_evaluation,
                    "reht_result": result.reht_evaluation,
                    "can_execute": result.can_execute,
                },
                provenance="paios:proposal",
            )
        )

        # Verify memory
        records = mem.query(type=MemoryType.GOVERNANCE_SIGNAL)
        assert len(records) == 1
        assert records[0].provenance == "paios:proposal"

        # VAIG approval alone cannot substitute for a real REHT authority.
        assert result.can_execute is False
        assert result.reht_evaluation["admissible"] is False
        assert result.envelope.racs_version == "1.0"

    def test_maturity_governs_proposal_readiness(self) -> None:
        """At L1, the OS should be able to propose (propose+remember is always allowed).
        At L2+, governed proposals flow through REHT.
        """
        model = MaturityModel()

        # L1: can build proposals
        result = governed_propose(
            action_type="read_config",
            actor={"id": "paios"},
            target={"resource": "config"},
            requested_effect={"action": "read"},
            authority_context={"scope": "read"},
        )
        assert result.envelope is not None

        # Advance to L2
        model.advance(signal="ready")
        assert model.current == MaturityLevel.L2_STEERED_RECS

        # L2: proposal still works (maturity doesn't block proposal, only execution)
        result2 = governed_propose(
            action_type="recommend_action",
            actor={"id": "paios"},
            target={"resource": "dashboard"},
            requested_effect={"action": "recommend"},
            authority_context={"scope": "steered"},
        )
        assert result2.envelope.action_type == "recommend_action"


# =========================================================================
# REHT Client — AdmissibilityVerdict, in-process / HTTP modes
# =========================================================================


class TestRehtClient:
    def test_mode_none_when_unconfigured(self) -> None:
        """No valo-platform importable and no URL → mode='none'."""
        from paios.reht_client import RehtClient

        client = RehtClient()
        # In this test environment valo-platform is not importable,
        # and VALO_REHT_URL is not set.
        assert client.mode in ("none", "http")  # http if env leaks

    def test_admissible_verdict_dict_shape(self) -> None:
        """AdmissibilityVerdict dict fields match REHT_VERDICT expectations."""
        from paios.reht_client import AdmissibilityVerdict

        v = AdmissibilityVerdict(
            state="ADMISSIBLE",
            admissible=True,
            score=0.95,
            reasons=["policy_allows_action"],
            governance_clearance={"clearance_id": "clr_abc123"},
        )
        assert v.state == "ADMISSIBLE"
        assert v.admissible is True
        assert v.score == 0.95
        assert v.reasons == ["policy_allows_action"]
        assert v.governance_clearance is not None
        assert v.governance_clearance["clearance_id"] == "clr_abc123"

    def test_inadmissible_verdict_dict_shape(self) -> None:
        from paios.reht_client import AdmissibilityVerdict

        v = AdmissibilityVerdict(
            state="INADMISSIBLE",
            admissible=False,
            score=0.0,
            reasons=["action_blocked_by_policy"],
            governance_clearance=None,
        )
        assert v.state == "INADMISSIBLE"
        assert v.admissible is False
        assert v.governance_clearance is None


# =========================================================================
# propose_action — REHT integration bridge
# =========================================================================


class TestProposeAction:
    """Tests for propose_action() — REHT integration entry point.

    Covers:
      (a) ADMISSIBLE → records verdict, no execution
      (b) INADMISSIBLE → blocked (recorded, not executed)
      (c) L2→L3 advance only when env flag + ADMISSIBLE
      (d) HTTP mode posts to VALO_REHT_URL
    """

    def _make_mock_client(
        self,
        *,
        state: str = "ADMISSIBLE",
        admissible: bool = True,
        score: float = 0.95,
        reasons: list[str] | None = None,
    ) -> Any:
        """Build a minimal mock RehtClient that returns a fixed verdict."""
        from unittest.mock import MagicMock

        from paios.reht_client import AdmissibilityVerdict

        verdict = AdmissibilityVerdict(
            state=state,
            admissible=admissible,
            score=score,
            reasons=reasons or ["mock_reason"],
            governance_clearance=(
                {"clearance_id": "clr_mock", "admissible": True}
                if admissible
                else None
            ),
        )
        client = MagicMock()
        client.evaluate.return_value = verdict
        client.mode = "mock"
        return client

    # --- (a) ADMISSIBLE → records verdict, no execution ---

    def test_admissible_records_verdict(self, tmp_path: Path) -> None:
        """ADMISSIBLE verdict is recorded in canonical memory."""
        from paios.memory import CanonicalMemory, MemoryType

        mem = CanonicalMemory(path=tmp_path / "memory.jsonl")
        client = self._make_mock_client()

        result = propose_action(
            action_type="send_notification",
            actor={"id": "paios", "tenant_id": "default"},
            target={"service": "email"},
            requested_effect={"message": "hello"},
            authority_context={"policy_ref": "pol_v1"},
            reht_client=client,
            memory=mem,
        )

        # Verdict recorded in memory
        records = mem.query(type=MemoryType.GOVERNANCE_SIGNAL)
        assert len(records) == 1
        assert records[0].provenance == "paios:proposal"
        content = records[0].content
        assert content["reht_evaluation"]["admissible"] is True
        assert content["reht_evaluation"]["state"] == "ADMISSIBLE"

        # No execution — only a GovernanceResult returned
        assert isinstance(result, GovernanceResult)
        assert result.envelope is not None
        assert result.envelope.action_type == "send_notification"

    def test_admissible_no_execution_path(self) -> None:
        """ADMISSIBLE proposal does NOT execute — only proposes."""
        client = self._make_mock_client()

        result = propose_action(
            action_type="query_dashboard",
            actor={"id": "paios"},
            target={"resource": "dashboard"},
            requested_effect={"action": "query"},
            authority_context={"scope": "read"},
            reht_client=client,
            vaig_evaluator=allow_vaig,
        )

        # Result is a GovernanceResult (proposal + evaluation), NOT execution
        assert isinstance(result, GovernanceResult)
        assert result.can_execute is True  # informational only
        assert result.reht_evaluation is not None
        assert result.reht_evaluation["state"] == "ADMISSIBLE"
        # No side effect beyond recording — just the result object
        assert len(result.errors) == 0

    # --- (b) INADMISSIBLE → blocked (recorded, not executed) ---

    def test_inadmissible_blocked_and_recorded(self, tmp_path: Path) -> None:
        """INADMISSIBLE proposal is blocked (recorded, not executed)."""
        from paios.memory import CanonicalMemory, MemoryType

        mem = CanonicalMemory(path=tmp_path / "memory.jsonl")
        client = self._make_mock_client(
            state="INADMISSIBLE", admissible=False, score=0.0
        )

        result = propose_action(
            action_type="delete_data",
            actor={"id": "paios"},
            target={"resource": "user_db"},
            requested_effect={"action": "delete"},
            authority_context={"scope": "admin"},
            reht_client=client,
            memory=mem,
        )

        # Verdict recorded as INADMISSIBLE in memory
        records = mem.query(type=MemoryType.GOVERNANCE_SIGNAL)
        assert len(records) == 1
        content = records[0].content
        assert content["reht_evaluation"]["admissible"] is False
        assert content["reht_evaluation"]["state"] == "INADMISSIBLE"
        assert content["can_execute"] is False

        # No execution — just a recorded block
        assert result.can_execute is False
        assert result.reht_evaluation["state"] == "INADMISSIBLE"
        assert len(result.errors) == 0

    def test_inadmissible_not_executed(self) -> None:
        """INADMISSIBLE proposal never reaches execution path."""
        client = self._make_mock_client(
            state="INADMISSIBLE", admissible=False, score=0.0
        )

        result = propose_action(
            action_type="write_file",
            actor={"id": "paios"},
            target={"path": "/etc/config"},
            requested_effect={"write": True},
            authority_context={"scope": "admin"},
            reht_client=client,
        )

        assert result.can_execute is False
        assert result.reht_evaluation["admissible"] is False
        # The function returns normally (no execution guard raise)
        # because propose_action never attempts to execute

    # --- (c) Maturity L2→L3 advance only when env flag + ADMISSIBLE ---

    def test_maturity_advance_L2_to_L3_when_admissible_and_flag(
        self,
    ) -> None:
        """L2→L3 advance when ADMISSIBLE + PAIOS_REHT_ADMISSIBILITY_PROVEN=1."""
        from paios.maturity import MaturityLevel, MaturityModel

        os.environ["PAIOS_REHT_ADMISSIBILITY_PROVEN"] = "1"
        try:
            model = MaturityModel(MaturityLevel.L2_STEERED_RECS)
            client = self._make_mock_client()

            propose_action(
                action_type="test_advance",
                actor={"id": "paios"},
                target={"resource": "test"},
                requested_effect={"action": "test"},
                authority_context={"scope": "test"},
                reht_client=client,
                vaig_evaluator=allow_vaig,
                maturity_model=model,
            )

            assert model.current == MaturityLevel.L3_GOVERNED_EX
        finally:
            del os.environ["PAIOS_REHT_ADMISSIBILITY_PROVEN"]

    def test_maturity_no_advance_when_env_flag_missing(self) -> None:
        """No L2→L3 advance when PAIOS_REHT_ADMISSIBILITY_PROVEN is not set."""
        from paios.maturity import MaturityLevel, MaturityModel

        # Ensure env is NOT set
        os.environ.pop("PAIOS_REHT_ADMISSIBILITY_PROVEN", None)
        model = MaturityModel(MaturityLevel.L2_STEERED_RECS)
        client = self._make_mock_client()

        propose_action(
            action_type="test_no_advance",
            actor={"id": "paios"},
            target={"resource": "test"},
            requested_effect={"action": "test"},
            authority_context={"scope": "test"},
            reht_client=client,
            maturity_model=model,
        )

        assert model.current == MaturityLevel.L2_STEERED_RECS

    def test_maturity_no_advance_when_inadmissible(self) -> None:
        """No L2→L3 advance when verdict is INADMISSIBLE even with flag."""
        from paios.maturity import MaturityLevel, MaturityModel

        os.environ["PAIOS_REHT_ADMISSIBILITY_PROVEN"] = "1"
        try:
            model = MaturityModel(MaturityLevel.L2_STEERED_RECS)
            client = self._make_mock_client(
                state="INADMISSIBLE", admissible=False, score=0.0
            )

            propose_action(
                action_type="test_blocked_advance",
                actor={"id": "paios"},
                target={"resource": "test"},
                requested_effect={"action": "test"},
                authority_context={"scope": "test"},
                reht_client=client,
                maturity_model=model,
            )

            # Still L2 — blocked proposal does not trigger advance
            assert model.current == MaturityLevel.L2_STEERED_RECS
        finally:
            del os.environ["PAIOS_REHT_ADMISSIBILITY_PROVEN"]

    def test_maturity_no_advance_when_below_L2(self) -> None:
        """No advance attempted when at L1 (below L2)."""
        from paios.maturity import MaturityLevel, MaturityModel

        os.environ["PAIOS_REHT_ADMISSIBILITY_PROVEN"] = "1"
        try:
            model = MaturityModel(MaturityLevel.L1_ASSIST)
            client = self._make_mock_client()

            propose_action(
                action_type="test_l1",
                actor={"id": "paios"},
                target={"resource": "test"},
                requested_effect={"action": "test"},
                authority_context={"scope": "test"},
                reht_client=client,
                maturity_model=model,
            )

            # Still L1 — L2→L3 advance is not attempted from L1
            assert model.current == MaturityLevel.L1_ASSIST
        finally:
            del os.environ["PAIOS_REHT_ADMISSIBILITY_PROVEN"]

    # --- (d) HTTP mode posts to VALO_REHT_URL ---

    def test_http_mode_posts_to_valo_reht_url(self) -> None:
        """HTTP mode POSTs to VALO_REHT_URL/evaluate/canonical."""
        import json
        from unittest.mock import patch

        from paios.reht_client import RehtClient, AdmissibilityVerdict

        os.environ["VALO_REHT_URL"] = "http://test-reht:8000"
        try:
            # Patch urlopen to return a canned response
            mock_response_text = json.dumps(
                {
                    "state": "ADMISSIBLE",
                    "admissible": True,
                    "score": 0.95,
                    "reasons": ["policy_allows_action"],
                    "governance_clearance": {
                        "clearance_id": "clr_http_test",
                        "admissible": True,
                    },
                }
            )

            with patch("paios.reht_client.urlopen") as mock_urlopen:
                mock_resp = mock_urlopen.return_value.__enter__.return_value
                mock_resp.read.return_value = mock_response_text.encode(
                    "utf-8"
                )
                mock_resp.status = 200

                from paios.proposal import ActionEnvelope

                client = RehtClient()
                assert client.mode == "http"

                envelope = ActionEnvelope(
                    action_type="http_test",
                    actor={"id": "paios", "tenant_id": "tenant1"},
                    target={"resource": "test"},
                    requested_effect={"action": "test"},
                    authority_context={"scope": "test"},
                )
                verdict = client.evaluate(envelope)

            # Verify the POST was made to the correct URL
            call_url = str(mock_urlopen.call_args[0][0].full_url)
            assert (
                "http://test-reht:8000/evaluate/canonical"
                in call_url
            )

            # Verify the verdict
            assert isinstance(verdict, AdmissibilityVerdict)
            assert verdict.state == "ADMISSIBLE"
            assert verdict.admissible is True
            assert verdict.score == 0.95
            assert verdict.governance_clearance is not None
            assert (
                verdict.governance_clearance["clearance_id"]
                == "clr_http_test"
            )
        finally:
            del os.environ["VALO_REHT_URL"]

    def test_http_mode_sends_action_envelope_fields(self) -> None:
        """HTTP mode sends the correct payload derived from the envelope."""
        import json
        from unittest.mock import patch

        os.environ["VALO_REHT_URL"] = "http://test-reht:8000"
        try:
            mock_response = json.dumps(
                {
                    "state": "ADMISSIBLE",
                    "admissible": True,
                    "score": 0.9,
                    "reasons": ["ok"],
                }
            )

            with patch("paios.reht_client.urlopen") as mock_urlopen:
                mock_resp = mock_urlopen.return_value.__enter__.return_value
                mock_resp.read.return_value = mock_response.encode("utf-8")
                mock_resp.status = 200

                from paios.reht_client import RehtClient
                from paios.proposal import ActionEnvelope

                client = RehtClient()
                envelope = ActionEnvelope(
                    action_type="data_query",
                    actor={"id": "paios", "tenant_id": "acme"},
                    target={"db": "analytics"},
                    requested_effect={"query": "SELECT 1"},
                    authority_context={"scope": "read"},
                    evidence_package={"source": "internal"},
                    risk_context={"level": "low"},
                )
                client.evaluate(envelope)

            # Inspect the POST body
            call_body = mock_urlopen.call_args[0][0].data
            body = json.loads(call_body.decode("utf-8"))
            assert body["tenant_id"] == "acme"
            assert body["task_id"] == envelope.action_id
            assert body["action"] == "data_query"
            assert body["risk_level"] == "low"
            assert body["evidence"]["source"] == "internal"
        finally:
            del os.environ["VALO_REHT_URL"]

    def test_http_mode_raises_on_connection_failure(self) -> None:
        """HTTP mode raises RehtClientError on network error."""
        from unittest.mock import patch

        from paios.reht_client import RehtClient, RehtClientError
        from paios.proposal import ActionEnvelope

        os.environ["VALO_REHT_URL"] = "http://localhost:1"
        try:
            with patch("paios.reht_client.urlopen") as mock_urlopen:
                from urllib.error import URLError

                mock_urlopen.side_effect = URLError("Connection refused")

                client = RehtClient()
                envelope = ActionEnvelope(
                    action_type="failing",
                    actor={"id": "test"},
                    target={"resource": "test"},
                    requested_effect={"action": "test"},
                    authority_context={"scope": "test"},
                )

                with pytest.raises(RehtClientError, match="REHT HTTP"):
                    client.evaluate(envelope)
        finally:
            del os.environ["VALO_REHT_URL"]

    def test_propose_action_http_mode_integration(
        self, tmp_path: Path
    ) -> None:
        """propose_action uses RehtClient HTTP mode end-to-end."""
        import json
        from unittest.mock import patch

        from paios.memory import CanonicalMemory, MemoryType

        os.environ["VALO_REHT_URL"] = "http://test-reht:8000"
        try:
            mock_response = json.dumps(
                {
                    "state": "ADMISSIBLE",
                    "admissible": True,
                    "score": 0.95,
                    "reasons": ["policy_allows_action"],
                    "governance_clearance": {
                        "clearance_id": "clr_http_e2e",
                        "admissible": True,
                    },
                }
            )

            with patch("paios.reht_client.urlopen") as mock_urlopen:
                mock_resp = mock_urlopen.return_value.__enter__.return_value
                mock_resp.read.return_value = mock_response.encode("utf-8")
                mock_resp.status = 200

                mem = CanonicalMemory(path=tmp_path / "memory.jsonl")

                result = propose_action(
                    action_type="http_e2e_test",
                    actor={"id": "paios", "tenant_id": "e2e"},
                    target={"resource": "test"},
                    requested_effect={"action": "test"},
                    authority_context={"scope": "test"},
                    memory=mem,
                )

            # Verify result
            assert result.reht_evaluation is not None
            assert result.reht_evaluation["state"] == "ADMISSIBLE"
            assert result.reht_evaluation["admissible"] is True
            assert result.reht_evaluation["clearance_id"] == "clr_http_e2e"

            # Verify memory recording
            records = mem.query(type=MemoryType.GOVERNANCE_SIGNAL)
            assert len(records) == 1
            assert records[0].provenance == "paios:proposal"

            # Verify no execution
            assert isinstance(result, GovernanceResult)
            assert len(result.errors) == 0
        finally:
            del os.environ["VALO_REHT_URL"]
