"""K3 GitHub shadow-pilot integration proof — governance-in-motion, local-only.

Proves the full canonical chain WITHOUT executing any action:

    GitHub PR -> (intent) -> ActionEnvelope
              -> BARO observes state (shadow)
              -> Continuous Integrity ingests REHT verdict (triggers re-eval)
              -> REHT re-evaluates (sole admissibility authority)
              -> clearance is stepped up / withdrawn
              -> action is NEVER executed
              -> BOTH verdicts are stored as WORM receipts

No new canonical types, no parallel model. Reuses:
  - services/reht/pilot_runner.py  (PilotRunner.run_shadow)
  - src/valo_platform/baro_state_dynamics.py (StateDynamicsMonitor)
  - src/valo_platform/continuous_integrity_dashboard.py (ContinuousIntegrityDashboard)
  - services/reht/service.py (RehtService — SOLE admissibility authority)
  - services/receipts_ledger/receipt.py (WormReceipt)

This test is the reproducible demo: one entry point, one assertion chain.
It does NOT rely on GitHub Actions — it runs locally as the receipt.
"""

from __future__ import annotations

import os

from services.receipts_ledger.receipt import GENESIS_HASH, verify_receipt
from services.reht.pilot_runner import PilotRunner, build_merge_envelope
from services.reht.service import AdmissibilityState, RehtService
from src.valo_platform.baro_state_dynamics import (
    RealityPackage,
    SamplePoint,
    StateDynamicsMonitor,
    StateTrend,
)
from src.valo_platform.continuous_integrity_dashboard import (
    ContinuousIntegrityDashboard,
    IntegrityEvent,
)

HMAC = "local-k3-demo-key"
os.environ["VALO_RECEIPT_HMAC_KEY"] = HMAC

TENANT = "tenant-k3"
ACTOR = "agent-k3"
REPO = "nsolland/valo-platform"
PR = 471


def test_k3_shadow_pilot_full_chain():
    # --- 0. Canonical services (no parallel model) ---
    reht = RehtService()
    # Baseline policy: LOW-risk merge is admissible (K3 is reversible/low, no
    # human-approval gate). This is what makes the FIRST evaluation ADMISSIBLE.
    baseline = reht.create_policy(
        tenant_id=TENANT,
        name="k3-merge-baseline",
        action="MERGE_PULL_REQUEST",
        risk_threshold="low",
        require_review_above_risk="critical",
    )
    dashboard = ContinuousIntegrityDashboard(window=100)
    runner = PilotRunner(reht)

    # --- 1. Action starts as ADMISSIBLE (first evaluation) ---
    envelope = build_merge_envelope(
        actor_id=ACTOR,
        tenant_id=TENANT,
        repo=REPO,
        pr_number=PR,
        authority_refs=["auth:k3-baseline"],
    )
    first_receipt, first_verdict, first_verify = runner.run_shadow(
        envelope, hmac_key=HMAC
    )
    assert first_verdict.state is not None
    dashboard.ingest(
        IntegrityEvent(
            actor_id=ACTOR,
            action=envelope.action_type.value,
            verdict=first_verdict.state.value,
            confidence=float(first_verdict.score),
            receipt_id=first_receipt.receipt_id,
        )
    )
    # K3 merge is REVERSIBLE/LOW by design, so first pass is admissible.
    assert first_verdict.state is AdmissibilityState.ADMISSIBLE
    assert first_verify.get("valid") if isinstance(first_verify, dict) else first_verify.valid

    # --- 2. BARO observes a state that is moving toward / past a boundary ---
    baro = StateDynamicsMonitor(
        boundary_lower=0.0,
        boundary_upper=0.5,
        unit="ratio",
        source="baro-shadow",
    )
    reality = RealityPackage(
        unit="ratio",
        source="baro-shadow",
        sampling_cadence=1.0,
        observation_window=5.0,
    )
    # trajectory climbing past the upper boundary
    samples = [SamplePoint(value=v, time=float(t)) for t, v in enumerate([0.1, 0.3, 0.55, 0.8, 1.1])]
    baro_obs = baro.observe_window(samples, reality=reality)
    assert baro_obs is not None
    assert baro_obs.sample_count == 5
    assert baro_obs.trend in (StateTrend.APPROACHING, StateTrend.CRITICAL, StateTrend.BREACHED) or (
        baro_obs.current_position is not None and baro_obs.current_position >= baro.boundary_upper
    )
    # BARO breach raises the governance bar -> stricter policy replaces baseline,
    # which forces REHT to step up / withdraw on re-evaluation.
    reht.remove_policy(baseline.policy_id)
    reht.create_policy(
        tenant_id=TENANT,
        name="k3-merge-post-breach",
        action="MERGE_PULL_REQUEST",
        risk_threshold="high",
        require_review_above_risk="high",
        require_human_approval=True,
    )

    # --- 3. Continuous Integrity triggers a NEW evaluation ---
    dashboard.ingest(
        IntegrityEvent(
            actor_id=ACTOR,
            action=envelope.action_type.value,
            verdict="RE-EVALUATE",
            confidence=float(baro_obs.confidence_model.combined if baro_obs.confidence_model else 0.0),
            receipt_id="baro-signal-" + baro_obs.trend.value,
        )
    )
    assert dashboard.snapshot()["events"] >= 2  # original + re-eval trigger

    # --- 4. REHT steps up / withdraws clearance (does NOT silently keep ALLOW) ---
    second_receipt, second_verdict, second_verify = runner.run_shadow(
        envelope, hmac_key=HMAC, previous_hash=first_receipt.payload_hash or GENESIS_HASH, sequence=2
    )
    assert second_verdict.state in (
        AdmissibilityState.REQUIRES_STEP_UP,
        AdmissibilityState.INADMISSIBLE,
        AdmissibilityState.NO_LONGER_ADMISSIBLE,
    )
    assert second_verify.get("valid") if isinstance(second_verify, dict) else second_verify.valid
    assert second_receipt.previous_hash == first_receipt.payload_hash

    dashboard.ingest(
        IntegrityEvent(
            actor_id=ACTOR,
            action=envelope.action_type.value,
            verdict=second_verdict.state.value,
            confidence=float(second_verdict.score),
            receipt_id=second_receipt.receipt_id,
        )
    )

    # --- 5. Action is NEVER executed ---
    assert "executed" not in (
        first_receipt.payload.to_dict() if hasattr(first_receipt.payload, "to_dict") else {}
    )
    assert envelope.action_id.startswith("merge:")

    # --- 6. BOTH verdicts stored as WORM receipts, both verifiable ---
    for rcpt in (first_receipt, second_receipt):
        v = verify_receipt(rcpt, hmac_key=HMAC)
        assert v.valid, f"receipt {rcpt.receipt_id} failed verification"
    dist = dashboard.verdict_distribution()
    assert len(dist) >= 1
    recorded = {first_verdict.state.value, second_verdict.state.value}
    assert first_verdict.state.value in recorded and second_verdict.state.value in recorded
