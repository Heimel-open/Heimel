"""Tests for embedded micro-admissibility, approval and consent."""

import pytest

from valo_edge.governance import (
    AdmissibilityVerdict,
    ApprovalChain,
    MicroAdmissibilityEngine,
    MicroConsentLedger,
    MicroSignal,
    SignalDisposition,
)


class TestMicroAdmissibility:
    def test_admit_when_all_ok(self):
        engine = MicroAdmissibilityEngine()
        d = engine.decide(signals=[
            MicroSignal("sensor", SignalDisposition.OK, confidence=0.9),
        ])
        assert d.verdict is AdmissibilityVerdict.ADMIT
        assert d.governance_confidence == pytest.approx(0.9)

    def test_block_forces_deny(self):
        engine = MicroAdmissibilityEngine()
        d = engine.decide(signals=[
            MicroSignal("safety", SignalDisposition.BLOCK, confidence=0.9),
            MicroSignal("sensor", SignalDisposition.OK, confidence=0.8),
        ])
        assert d.verdict is AdmissibilityVerdict.DENY
        assert d.governance_confidence == 0.0
        assert "safety" in d.blocking_sources

    def test_escalate_defers(self):
        engine = MicroAdmissibilityEngine()
        d = engine.decide(signals=[
            MicroSignal("risk", SignalDisposition.ESCALATE, confidence=0.7),
        ])
        assert d.verdict is AdmissibilityVerdict.DEFER

    def test_no_evidence_denies(self):
        engine = MicroAdmissibilityEngine()
        d = engine.decide(signals=[])
        assert d.verdict is AdmissibilityVerdict.DENY
        assert "evidence" in d.blocking_sources

    def test_no_delegate_high_risk_denies(self):
        engine = MicroAdmissibilityEngine()
        d = engine.decide(signals=[
            MicroSignal("sensor", SignalDisposition.OK, confidence=0.9),
        ], risk_tier="L3", has_human_delegate=False)
        assert d.verdict is AdmissibilityVerdict.DENY


class TestApprovalChain:
    def test_quorum_required(self):
        chain = ApprovalChain("act-1", required_approvals=2)
        chain.add_vote("a", "approve")
        assert not chain.is_approved
        chain.add_vote("b", "approve")
        assert chain.is_approved
        assert chain.verify()

    def test_reject_does_not_count(self):
        chain = ApprovalChain("act-1", required_approvals=1)
        chain.add_vote("a", "reject")
        assert not chain.is_approved

    def test_tamper_detected(self):
        chain = ApprovalChain("act-1", required_approvals=1)
        chain.add_vote("a", "approve")
        chain._records[0].decision = "reject"
        assert not chain.verify()

    def test_invalid_decision(self):
        chain = ApprovalChain("act-1")
        with pytest.raises(ValueError):
            chain.add_vote("a", "maybe")


class TestMicroConsent:
    def test_grant_and_withdraw(self):
        ledger = MicroConsentLedger()
        ledger.grant("user1", "capture", "camera", "2026-08-06T00:00:00Z")
        assert ledger.is_active("user1", "capture")
        assert ledger.verify()
        ledger.withdraw("user1", "capture", "2026-08-06T01:00:00Z")
        assert not ledger.is_active("user1", "capture")
        assert ledger.verify()

    def test_tamper_detected(self):
        ledger = MicroConsentLedger()
        ledger.grant("user1", "capture", "camera", "2026-08-06T00:00:00Z")
        ledger._records[0].status = "withdrawn"
        assert not ledger.verify()

    def test_chain_binds_records(self):
        ledger = MicroConsentLedger()
        r1 = ledger.grant("a", "p1", "s1", "2026-08-06T00:00:00Z")
        r2 = ledger.grant("b", "p2", "s2", "2026-08-06T00:01:00Z")
        assert r2.prev_hash == r1.record_hash
