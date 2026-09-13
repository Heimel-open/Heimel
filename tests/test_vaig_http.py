import json
from datetime import datetime, timedelta, timezone

import pytest

from src.valo_platform.decision_governance.continuity import (
    ContinuityBasisSnapshot,
    ContinuityImpactAssessment,
    ContinuityMateriality,
)
from src.valo_platform.operational_continuity.observers import ObservationBinding
from src.valo_platform.operational_continuity.revalidation import (
    build_revalidation_request,
)
from src.valo_platform.operational_continuity.source_adapters import (
    ContinuitySourceDomain,
    ContinuitySourceObservation,
    build_source_bundle,
)
from src.valo_platform.operational_continuity.source_baselines import (
    ContinuitySourceBaseline,
    ContinuitySourceBaselineEntry,
)
from src.valo_platform.operational_continuity.vaig_http import (
    ASSESSMENT_SCHEMA_VERSION,
    ASSESSOR_REF,
    SERVICE_ID,
    WIRE_SCHEMA_VERSION,
    VaigContinuityClientError,
    VaigHttpContinuityAssessmentPort,
)


NOW = datetime(2026, 8, 1, 15, 50, tzinfo=timezone.utc)
CURRENT = {
    "authority": "sha256:authority",
    "policy": "sha256:policy",
    "context": "sha256:context",
    "state": "sha256:case",
    "evidence": "sha256:evidence",
}


def request():
    binding = ObservationBinding(
        tenant_id="tenant-1",
        action_case_id="case-1",
        action_case_hash=CURRENT["state"],
        clearance_ref="clearance-1",
        observer_ref="runtime:commit-boundary",
    )
    basis = ContinuityBasisSnapshot(
        snapshot_id="basis-1",
        tenant_id="tenant-1",
        action_case_id="case-1",
        action_case_hash=CURRENT["state"],
        clearance_ref="clearance-1",
        observed_at=NOW - timedelta(minutes=5),
        authority_fingerprint=CURRENT["authority"],
        policy_fingerprint=CURRENT["policy"],
        evidence_fingerprint=CURRENT["evidence"],
        context_fingerprint=CURRENT["context"],
        state_fingerprint=CURRENT["state"],
        purpose_binding_ref="purpose-binding-1",
        valid_until=NOW + timedelta(hours=1),
    )
    entry = ContinuitySourceBaselineEntry(
        domain=ContinuitySourceDomain.POLICY,
        source_ref="policy:1",
        fingerprint="sha256:policy-source",
        evidence_refs=("evidence:policy",),
        captured_at=NOW - timedelta(minutes=5),
    )
    baseline = ContinuitySourceBaseline(
        binding=binding,
        captured_at=NOW - timedelta(minutes=5),
        entries=(entry,),
    )
    observation = ContinuitySourceObservation(
        domain=ContinuitySourceDomain.POLICY,
        source_ref="policy:1",
        expected_fingerprint=entry.fingerprint,
        current_fingerprint=entry.fingerprint,
        observed_at=NOW,
        evidence_refs=("evidence:policy",),
    )
    bundle = build_source_bundle(
        binding=binding,
        observed_at=NOW,
        observations=(observation,),
    )
    return build_revalidation_request(
        request_id="request-1",
        requester_ref="execution-gateway:content",
        basis=basis,
        source_baseline=baseline,
        source_bundle=bundle,
        current_fingerprints=CURRENT,
        requested_at=NOW,
    )


def assessment(req, *, assessed_at=NOW, assessor_refs=(ASSESSOR_REF,)):
    return ContinuityImpactAssessment(
        assessment_id="assessment-1",
        tenant_id=req.basis.tenant_id,
        trigger_refs=tuple(trigger.trigger_id for trigger in req.triggers),
        action_case_id=req.basis.action_case_id,
        action_case_hash=req.basis.action_case_hash,
        clearance_ref=req.basis.clearance_ref,
        materiality=ContinuityMateriality.NO_MATERIAL_CHANGE,
        impact_dimensions=("operational_continuity",),
        reason_codes=("all_sources_revalidated",),
        evidence_refs=(req.evidence_ref,),
        assessor_refs=assessor_refs,
        confidence=1.0,
        assessed_at=assessed_at,
    )


def response_payload(req, **changes):
    payload = {
        "schema_version": ASSESSMENT_SCHEMA_VERSION,
        "service_id": SERVICE_ID,
        "request_ref": req.evidence_ref,
        "request_digest": req.request_digest,
        "assessment": assessment(req).model_dump(mode="json"),
    }
    payload.update(changes)
    return payload


class FakeResponse:
    def __init__(
        self,
        payload,
        *,
        status_code=200,
        content_type="application/json",
        content=None,
        json_error=None,
    ):
        self.payload = payload
        self.status_code = status_code
        self.headers = {"content-type": content_type}
        self.content = (
            content
            if content is not None
            else json.dumps(payload, default=str).encode("utf-8")
        )
        self.json_error = json_error

    def json(self):
        if self.json_error is not None:
            raise self.json_error
        return self.payload


class FakeSession:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def post(self, url, *, json, headers, timeout):
        self.calls.append(
            {
                "url": url,
                "json": json,
                "headers": dict(headers),
                "timeout": timeout,
            }
        )
        if self.error is not None:
            raise self.error
        return self.response


def client(fake, **changes):
    config = {
        "base_url": "https://vaig.internal",
        "bearer_token": "token-1",
        "session": fake,
    }
    config.update(changes)
    return VaigHttpContinuityAssessmentPort(**config)


def test_valid_response_is_contract_and_digest_verified():
    req = request()
    fake = FakeSession(FakeResponse(response_payload(req)))
    port = client(fake)

    result = port.assess(req, assessed_at=NOW)

    assert result.assessment_id == "assessment-1"
    assert result.materiality is ContinuityMateriality.NO_MATERIAL_CHANGE
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call["url"] == "https://vaig.internal/api/v1/continuity/assess"
    assert call["json"] == {
        "schema_version": WIRE_SCHEMA_VERSION,
        "assessed_at": "2026-08-01T15:50:00Z",
        "request": req.model_dump(mode="json"),
    }
    assert call["headers"]["Authorization"] == "Bearer token-1"
    assert call["headers"]["X-Continuity-Request-Digest"] == req.request_digest
    assert call["timeout"] == 5.0


def test_https_is_required_except_explicit_localhost_development():
    with pytest.raises(VaigContinuityClientError, match="HTTPS_REQUIRED"):
        VaigHttpContinuityAssessmentPort(base_url="http://vaig.internal")

    local = VaigHttpContinuityAssessmentPort(
        base_url="http://127.0.0.1:8080/",
        allow_insecure_localhost=True,
        session=FakeSession(),
    )
    assert local.endpoint_url == "http://127.0.0.1:8080/api/v1/continuity/assess"

    with pytest.raises(VaigContinuityClientError, match="USERINFO_FORBIDDEN"):
        VaigHttpContinuityAssessmentPort(base_url="https://user:pass@vaig.internal")


def test_transport_and_http_failures_are_fail_closed():
    req = request()
    with pytest.raises(VaigContinuityClientError, match="TRANSPORT_FAILED"):
        client(FakeSession(error=OSError("down"))).assess(req, assessed_at=NOW)

    with pytest.raises(VaigContinuityClientError, match="HTTP_STATUS:503"):
        client(FakeSession(FakeResponse({}, status_code=503))).assess(
            req, assessed_at=NOW
        )


def test_non_json_invalid_json_and_oversize_responses_are_rejected():
    req = request()
    with pytest.raises(VaigContinuityClientError, match="RESPONSE_NOT_JSON"):
        client(
            FakeSession(
                FakeResponse(response_payload(req), content_type="text/html")
            )
        ).assess(req, assessed_at=NOW)

    with pytest.raises(VaigContinuityClientError, match="RESPONSE_JSON_INVALID"):
        client(
            FakeSession(
                FakeResponse(
                    None,
                    json_error=ValueError("bad json"),
                    content=b"{",
                )
            )
        ).assess(req, assessed_at=NOW)

    with pytest.raises(VaigContinuityClientError, match="RESPONSE_TOO_LARGE"):
        client(
            FakeSession(
                FakeResponse(
                    response_payload(req),
                    content=b"x" * 128,
                )
            ),
            max_response_bytes=64,
        ).assess(req, assessed_at=NOW)


def test_service_schema_request_and_exact_response_shape_are_bound():
    req = request()
    cases = [
        ({"schema_version": "other/1"}, "SCHEMA_UNSUPPORTED"),
        ({"service_id": "other-service"}, "SERVICE_ID_MISMATCH"),
        ({"request_ref": "other-ref"}, "REQUEST_REF_MISMATCH"),
        ({"request_digest": "sha256:other"}, "REQUEST_DIGEST_MISMATCH"),
    ]
    for changes, error in cases:
        with pytest.raises(VaigContinuityClientError, match=error):
            client(FakeSession(FakeResponse(response_payload(req, **changes)))).assess(
                req, assessed_at=NOW
            )

    extra = response_payload(req)
    extra["receipt"] = {}
    with pytest.raises(VaigContinuityClientError, match="RESPONSE_SCHEMA_INVALID"):
        client(FakeSession(FakeResponse(extra))).assess(req, assessed_at=NOW)


def test_authorization_or_execution_output_is_never_accepted():
    req = request()
    payload = response_payload(req)
    payload["assessment"]["authorization"] = {"decision": "ALLOW"}

    with pytest.raises(
        VaigContinuityClientError,
        match="AUTHORIZATION_OUTPUT_FORBIDDEN",
    ):
        client(FakeSession(FakeResponse(payload))).assess(req, assessed_at=NOW)


def test_assessment_digest_time_assessor_and_request_binding_are_verified():
    req = request()

    tampered = response_payload(req)
    tampered["assessment"]["materiality"] = "material_change"
    with pytest.raises(VaigContinuityClientError, match="CONTRACT_INVALID"):
        client(FakeSession(FakeResponse(tampered))).assess(req, assessed_at=NOW)

    wrong_time = response_payload(req)
    wrong_time["assessment"] = assessment(
        req, assessed_at=NOW + timedelta(seconds=1)
    ).model_dump(mode="json")
    with pytest.raises(VaigContinuityClientError, match="TIME_MISMATCH"):
        client(FakeSession(FakeResponse(wrong_time))).assess(req, assessed_at=NOW)

    wrong_assessor = response_payload(req)
    wrong_assessor["assessment"] = assessment(
        req, assessor_refs=("vaig:unknown",)
    ).model_dump(mode="json")
    with pytest.raises(VaigContinuityClientError, match="ASSESSOR_REF_MISSING"):
        client(FakeSession(FakeResponse(wrong_assessor))).assess(req, assessed_at=NOW)

    unbound = response_payload(req)
    unbound_assessment = assessment(req).model_copy(
        update={"evidence_refs": ("evidence:other",), "assessment_digest": ""}
    )
    unbound["assessment"] = ContinuityImpactAssessment(
        **unbound_assessment.model_dump(mode="python")
    ).model_dump(mode="json")
    with pytest.raises(VaigContinuityClientError, match="BINDING_INVALID"):
        client(FakeSession(FakeResponse(unbound))).assess(req, assessed_at=NOW)


def test_timeout_token_and_response_limit_configuration_fail_closed():
    with pytest.raises(VaigContinuityClientError, match="TIMEOUT_INVALID"):
        VaigHttpContinuityAssessmentPort(
            base_url="https://vaig.internal",
            timeout_seconds=0,
        )
    with pytest.raises(VaigContinuityClientError, match="BEARER_TOKEN_INVALID"):
        VaigHttpContinuityAssessmentPort(
            base_url="https://vaig.internal",
            bearer_token=" ",
        )
    with pytest.raises(VaigContinuityClientError, match="RESPONSE_LIMIT_INVALID"):
        VaigHttpContinuityAssessmentPort(
            base_url="https://vaig.internal",
            max_response_bytes=0,
        )
