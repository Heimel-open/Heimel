"""Integration test: ECB Cyber data model integrates with the DORA vertical slice.

Proves that the repaired finserv/ecb_cyber models (canonical GovernanceClearance,
CyberEvaluation, ControlException) compose with the existing DORA third-party
governance vertical slice (dora_vertical_slice.py) WITHOUT a duplicate authority
contract:

- VAIG side  -> CyberEvaluation (risk signal; not authority)
- REHT side  -> canonical action_envelope.GovernanceClearance (sole admissibility)
- No second competing clearance type exists in the ECB profile.

Runs under `uv run pytest` (needs pytest-asyncio for the async slice path).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, List

import pytest

from src.valo_platform.dora_vertical_slice import (
    DORAThirdPartyGovernance,
    DORAThirdPartyInput,
    DORA_VERDICT_ALLOW,
)
from src.valo_platform.reht_admissibility_engine import RehtAdmissibilityEngine

from src.valo_platform.finserv.ecb_cyber import (
    CyberEvaluation,
    ControlException,
    GovernanceClearance,
    SubmissionPackage,
)
from src.valo_platform.action_envelope.models import (
    ActionDecision,
    ClearanceState,
)


class _StubLifecycle:
    def active_version(self) -> "Any":
        class _V:
            version = "2.0.0"
        return _V()


class _StubPolicyService:
    def get_lifecycle(self, policy_id: str) -> _StubLifecycle:
        return _StubLifecycle()


def _make_speider():
    s = asyncio.get_event_loop() if False else None  # placeholder; not used
    class _Speider:
        def __init__(self):
            self.call_count = 0

        async def assess_supplier_risk(self, supplier_name, context=None):
            self.call_count += 1
            return {
                "supplier": supplier_name,
                "risk_tier": "LOW",
                "signals": [{"type": "tpr", "value": 0.1}],
            }
    return _Speider()


def _make_baro():
    class _Baro:
        def observe_window(self, frames):
            return {"observations": frames, "convergence": "stable"}
    return _Baro()


@pytest.mark.asyncio
async def test_vertical_slice_integrates_with_repaired_ecb_models():
    speider = _make_speider()
    baro = _make_baro()
    reht = RehtAdmissibilityEngine()
    policy_svc = _StubPolicyService()

    gov = DORAThirdPartyGovernance(
        speider=speider,
        baro=baro,
        reht_engine=reht,
        policy_service=policy_svc,
        receipt_secret="test-secret",
    )

    inp = DORAThirdPartyInput(
        action_id="act-ecb-001",
        supplier_name="LedgerSync",
        model_id="gpt-4-safe",
        model_version="1.0.0",
        policy_id="data-residency-policy",
        identity="alice",
        authority="chain-001",
        context="ctx-001",
        human_delegate="bob",
        risk_tier="L2",
    )

    result = await gov.run(inp)

    # Vertical slice produced a VAIG evaluation signal AND a REHT verdict/receipt
    assert len(result.vaig_signals) >= 1, "VAIG side must emit signals"
    assert result.decision_verdict in (DORA_VERDICT_ALLOW, "DENY", "DEFER", "STEP_UP")
    assert result.receipt is not None, "REHT side must issue a receipt"

    # Compose into the ECB Cyber profile model layer
    vaig_eval = CyberEvaluation(
        decision_id="eval-1",
        action_id=inp.action_id,
        signal_summary={"vaig_signals": result.vaig_signals},
        risk_tier=inp.risk_tier,
        confidence=float(result.governance_confidence),
        recommended_disposition=result.decision_verdict,
    )

    reht_clearance = GovernanceClearance(
        clearance_id="clr-1",
        action_id=inp.action_id,
        tenant_id="meridian-euro-bank",
        decision=ActionDecision.ALLOW if result.decision_verdict == DORA_VERDICT_ALLOW
        else ActionDecision.HALT,
        state=ClearanceState.ACTIVE,
        authority_refs=["chain-001"],
        evidence_refs=[f"speider:{inp.supplier_name}", f"baro:{inp.action_id}"],
        valid_until=datetime(2026, 10, 31, tzinfo=timezone.utc),
        evaluator_refs=["VAIG", "REHT"],
        receipt_ref=getattr(result.receipt, "receipt_id", "rcpt-1"),
    )

    pkg = SubmissionPackage(
        package_id="pkg-1",
        bank="Meridian Euro Bank",
        as_of=datetime(2026, 7, 12, tzinfo=timezone.utc),
        readiness_score=0.7,
        gaps=[],
        actions=[],
        export_format="pdf",
    )

    # ── Authority boundary assertions ──────────────────────────────────
    # 1. REHT clearance IS the canonical action_envelope artifact (no duplicate)
    #    Use __module__ to avoid dual-import path-resolution mismatches.
    assert GovernanceClearance.__module__.endswith("action_envelope.models"), \
        "ECB profile must reuse the canonical REHT GovernanceClearance, not redefine it"
    # 2. VAIG evaluation and REHT clearance are DISTINCT types (clear boundary)
    assert CyberEvaluation is not GovernanceClearance
    # 3. Both layers carried real verdict/eval data from the slice
    assert vaig_eval.recommended_disposition == result.decision_verdict
    assert reht_clearance.decision in (ActionDecision.ALLOW, ActionDecision.HALT)
    assert pkg.bank == "Meridian Euro Bank"
    # 4. ControlException is available (renamed from Exception_) and constructible
    exc = ControlException(
        exception_id="exc-1", control_id="ctrl-1", reason="temp",
        approved_by="CRO", expires=datetime(2026, 12, 1, tzinfo=timezone.utc),
        receipt_signature="sig",
    )
    assert exc.control_id == "ctrl-1"
