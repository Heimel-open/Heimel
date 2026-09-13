from __future__ import annotations

from valo_operator import OperatorRequest, OperatorSession, build_public_runtime


def _register_request(cid="ev-1"):
    return OperatorRequest(
        correlation_id=cid, function_id="valo.public.register_case",
        inputs={"application": {"id": "app-1", "service_type": "PUBLIC_SERVICE_A"}},
    )


def test_receipts_captured_on_submit() -> None:
    runtime = build_public_runtime()
    result = runtime.submit(_register_request())
    assert result.instance_id
    kinds = {r["kind"] for r in result.receipts}
    assert "authorization" in kinds
    assert "execution" in kinds
    assert "effect_verified" in kinds
    effect = [r for r in result.receipts if r["kind"] == "effect_verified"][0]
    assert effect["receipt_ref"]


def test_ledger_records_evidence() -> None:
    runtime = build_public_runtime()
    runtime.submit(_register_request("corr-1"))
    entry = runtime.evidence_by_correlation("corr-1")
    assert entry is not None
    assert entry.function_id == "valo.public.register_case"
    assert entry.decision == "ALLOW"
    assert entry.effect_verified is True
    assert entry.baro_outcome == "ok"
    assert entry.instance_id


def test_ledger_denied_records_deny_and_diverged() -> None:
    from valo_kernel.contracts import CanonicalEvent, EventType, utcnow

    runtime = build_public_runtime()
    runtime.kernel.append(CanonicalEvent(
        event_id="revoke-admin", event_type=EventType.AUTHORITY_REVOKED,
        tenant_id="public", subject="system-1", source="kernel", effective_at=utcnow(),
        payload={"authority_id": "auth-system-ADMIN", "revocation_ref": "rev-admin"},
    ))
    runtime.submit(_register_request("corr-deny"))
    entry = runtime.evidence_by_correlation("corr-deny")
    assert entry.decision == "DENY"
    assert entry.effect_verified is False


def test_ledger_divergence_detected() -> None:
    """HTTP 200 but the decision was not delivered -> BARO diverged, and the
    evidence ledger records it."""
    from valo_operator import OperatorRequest
    from valo_operator.adapters import ExternalSystem, HttpGateway, HttpVeritas

    external = ExternalSystem(landing="DELIVERED", landing_by_action={"NOTIFY": "PENDING"})
    try:
        runtime = build_public_runtime(gateway=HttpGateway(external.base_url), veritas=HttpVeritas(external.base_url))
        for fid, inputs, cid in [
            ("valo.public.register_case", {"application": {"id": "app-1", "service_type": "PUBLIC_SERVICE_A"}}, "a1"),
            ("valo.public.mark_ready_for_review", {"case": {"id": "case-1"}}, "a2"),
            ("valo.public.mark_under_review", {"case": {"id": "case-1"}}, "a3"),
            ("valo.public.mark_ready_for_decision", {"case": {"id": "case-1"}}, "a4"),
            ("valo.public.issue_public_decision", {"context": {"case": "case-1"}}, "a5"),
        ]:
            runtime.submit(OperatorRequest(correlation_id=cid, function_id=fid, inputs=inputs))
        runtime.submit(OperatorRequest(
            correlation_id="corr-notify", function_id="valo.public.notify",
            inputs={"notification": {"recipient": "applicant-1", "message": "decision"}},
        ))
        entry = runtime.evidence_by_correlation("corr-notify")
        assert entry.status == "FAILED"
        assert entry.baro_outcome == "diverged"
        assert entry.effect_verified is False
    finally:
        external.stop()


def test_audit_queries() -> None:
    runtime = build_public_runtime()
    runtime.submit(_register_request("q1"))
    runtime.submit(_register_request("q2"))
    assert len(runtime.audit()) == 2
    assert len(runtime.audit(function_id="valo.public.register_case")) == 2
    assert len(runtime.audit(status="COMPLETED")) == 1
    assert len(runtime.audit(status="FAILED")) == 1
    assert runtime.evidence_by_correlation("missing") is None


def test_evidence_with_session() -> None:
    runtime = build_public_runtime()
    session = OperatorSession(tenant_id="public", actor="system-1", identity_id="id-system-1")
    runtime.submit(_register_request("corr-sess"), session=session)
    entry = runtime.evidence_by_correlation("corr-sess")
    assert entry.decision == "ALLOW"
    assert entry.receipts
