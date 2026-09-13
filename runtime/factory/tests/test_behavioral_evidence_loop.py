import hashlib
import unittest

from lib.behavioral_evidence_loop import (
    AuthorizationBindingV1,
    AuthorityBindingError,
    BehaviorFindingV1,
    BehaviorTraceV1,
    BehavioralAction,
    BehavioralEvidenceError,
    BehavioralEvidenceLoop,
    BehavioralSensorAdapter,
    ClaimKind,
    EvidenceRefV1,
    ExecutionReceiptV1,
    ImprovementCandidateV1,
    LearningAdmissionError,
    ObservationMode,
    OutcomeBindingError,
    OutcomeEvidenceV1,
    OutcomeStatus,
    PrivacyClass,
    PrivacyEnvelopeV1,
    RedactionState,
    authority_boundary,
    classify_outcome,
)

DIGEST = hashlib.sha256(b"payload").hexdigest()
ACTION_DIGEST = hashlib.sha256(b"exact-action").hexdigest()
OTHER_DIGEST = hashlib.sha256(b"different-action").hexdigest()


def privacy(tenant_id="tenant-a", scope="product-a"):
    return PrivacyEnvelopeV1(
        tenant_id=tenant_id,
        scope=scope,
        collection_purpose="product_improvement",
        classification=PrivacyClass.CONFIDENTIAL,
        redaction_state=RedactionState.REDACTED,
        retention_class="30d",
        residency="eu-no",
        rights_basis_ref="contract:customer-dpa",
    )


def evidence(source="logrocket_galileo", tenant_id="tenant-a", scope="product-a"):
    return EvidenceRefV1(
        evidence_id=f"evidence:{source}",
        source_type=source,
        source_ref=f"{source}:session-42",
        payload_digest=DIGEST,
        captured_at="2026-08-10T20:10:01Z",
        observed_at="2026-08-10T20:10:00Z",
        privacy=privacy(tenant_id, scope),
        provenance_ref=f"{source}:export-7",
        actor_ref="user:pseudonymous-7",
        resource_ref="checkout",
    )


def candidate(digest=ACTION_DIGEST):
    return ImprovementCandidateV1(
        candidate_id="candidate-1",
        finding_refs=("finding-1",),
        hypothesis="preserving state reduces checkout abandonment",
        proposed_change_type="code",
        target_ref="repo:checkout",
        expected_outcome="checkout conversion increases",
        action_payload_digest=digest,
        requested_actions=(BehavioralAction.DEPLOY,),
        risk_class="B",
        required_evaluation_refs=("test:checkout-state", "shadow:conversion"),
        owner_ref="team:product",
    )


def authorization(digest=ACTION_DIGEST):
    return AuthorizationBindingV1(
        authorization_id="auth-1",
        candidate_id="candidate-1",
        action_payload_digest=digest,
        principal_ref="agent:factory-worker-7",
        mandate_ref="mandate:product-improvement",
        reht_decision_ref="reht:allow-700",
        authorized_state_ref="state:checkout-v3",
        authorized_at="2026-08-10T20:20:00Z",
        expires_at="2026-08-10T20:30:00Z",
    )


def receipt(digest=ACTION_DIGEST):
    return ExecutionReceiptV1(
        receipt_id="receipt-1",
        candidate_id="candidate-1",
        action_payload_digest=digest,
        authorization_id="auth-1",
        executed_at="2026-08-10T20:25:00Z",
        result_artifact_ref="commit:abc123",
        deployment_ref="deploy:prod-55",
        veritas_receipt_ref="veritas:receipt-1",
    )


def outcome(digest=ACTION_DIGEST, status=OutcomeStatus.VERIFIED_IMPROVED, receipt_id="receipt-1"):
    return OutcomeEvidenceV1(
        outcome_id="outcome-1",
        candidate_id="candidate-1",
        action_payload_digest=digest,
        authorization_id="auth-1",
        execution_receipt_id=receipt_id,
        pre_evidence_refs=("metric:before",),
        post_evidence_refs=("metric:after",),
        expected_outcome="checkout conversion increases",
        observed_outcome="checkout conversion increased by 4 points",
        comparison_method="controlled_release_cohort",
        window_start="2026-08-10T20:30:00Z",
        window_end="2026-08-11T20:30:00Z",
        metric_name="checkout_conversion",
        baseline_value=0.61,
        observed_value=0.65,
        causal_caveats=("weekend traffic mix",),
        status=status,
    )


class BehavioralEvidenceLoopTests(unittest.TestCase):
    def test_vendor_neutral_sources_share_one_contract(self):
        logrocket = evidence("logrocket_galileo")
        sentry = evidence("sentry")
        self.assertEqual(logrocket.privacy.tenant_id, sentry.privacy.tenant_id)
        self.assertNotEqual(logrocket.integrity_digest, sentry.integrity_digest)

    def test_observation_cannot_cross_tenant_or_scope(self):
        adapter = BehavioralSensorAdapter("fullstory")
        with self.assertRaises(BehavioralEvidenceError):
            adapter.normalize_observation(
                observation_id="obs-1",
                event_type="journey_friction",
                observed_condition="users loop between two steps",
                evidence_refs=(
                    evidence("fullstory", "tenant-a", "product-a"),
                    evidence("fullstory", "tenant-b", "product-a"),
                ),
                mode=ObservationMode.LIVE,
            )

    def test_replay_and_shadow_mode_remain_explicit(self):
        adapter = BehavioralSensorAdapter("human_behavior")
        observation = adapter.normalize_observation(
            observation_id="obs-2",
            event_type="rage_click",
            observed_condition="repeated click on disabled control",
            evidence_refs=(evidence("human_behavior"),),
            mode=ObservationMode.SHADOW,
        )
        self.assertEqual(observation.mode, ObservationMode.SHADOW)

    def test_trace_cannot_claim_complete_with_gaps(self):
        with self.assertRaises(BehavioralEvidenceError):
            BehaviorTraceV1(
                trace_id="trace-1",
                observation_ids=("obs-1",),
                mode=ObservationMode.REPLAY,
                session_or_run_ref="session-1",
                start_position_ref="event-1",
                end_position_ref="event-9",
                unresolved_gaps=("event-4",),
                complete=True,
            )

    def test_finding_requires_resolvable_evidence(self):
        with self.assertRaises(BehavioralEvidenceError):
            BehaviorFindingV1(
                finding_id="finding-1",
                trace_refs=(),
                evidence_refs=(),
                claim_kind=ClaimKind.MODEL_EXPLANATION,
                observed_condition="conversion fell",
                expected_condition_ref="slo:conversion",
                confidence=0.7,
                contradictory_evidence_refs=(),
                materiality="high",
                generated_by="agent:analysis",
                reproducibility_ref="query:123",
            )

    def test_sensor_may_propose_but_not_authorize_consequential_action(self):
        adapter = BehavioralSensorAdapter("posthog_replay_vision")
        bounded = adapter.propose_candidate(
            candidate_id="candidate-bounded",
            finding_refs=("finding-1",),
            hypothesis="copy is unclear",
            proposed_change_type="code",
            target_ref="repo:web",
            expected_outcome="completion increases",
            action_payload_digest=ACTION_DIGEST,
            requested_actions=(BehavioralAction.OPEN_PR,),
            risk_class="A",
            required_evaluation_refs=("test:ui",),
            owner_ref="team:web",
        )
        self.assertEqual(authority_boundary(bounded), "FACTORY_VALIDATE")
        with self.assertRaises(PermissionError):
            adapter.propose_candidate(
                candidate_id="candidate-forbidden",
                finding_refs=("finding-1",),
                hypothesis="copy is unclear",
                proposed_change_type="code",
                target_ref="repo:web",
                expected_outcome="completion increases",
                action_payload_digest=ACTION_DIGEST,
                requested_actions=(BehavioralAction.DEPLOY,),
                risk_class="B",
                required_evaluation_refs=("test:ui",),
                owner_ref="team:web",
            )

    def test_consequential_candidate_routes_to_reht(self):
        self.assertEqual(authority_boundary(candidate()), "REHT_REQUIRED")

    def test_authorization_must_bind_exact_action(self):
        with self.assertRaises(AuthorityBindingError):
            BehavioralEvidenceLoop.validate_authorization(
                candidate(), authorization(OTHER_DIGEST), at_time="2026-08-10T20:25:00Z"
            )

    def test_expired_authorization_cannot_execute(self):
        expired = ExecutionReceiptV1(
            receipt_id="receipt-expired",
            candidate_id="candidate-1",
            action_payload_digest=ACTION_DIGEST,
            authorization_id="auth-1",
            executed_at="2026-08-10T20:31:00Z",
            result_artifact_ref="commit:abc123",
            deployment_ref="deploy:prod-55",
            veritas_receipt_ref="veritas:receipt-expired",
        )
        with self.assertRaises(AuthorityBindingError):
            BehavioralEvidenceLoop.record_execution(candidate(), authorization(), expired)

    def test_outcome_must_bind_execution_receipt(self):
        with self.assertRaises(OutcomeBindingError):
            BehavioralEvidenceLoop.verify_outcome(
                candidate(), authorization(), receipt(), outcome(receipt_id="receipt-other")
            )

    def test_verified_outcome_closes_exact_receipt_bound_loop(self):
        verified = BehavioralEvidenceLoop.verify_outcome(
            candidate(), authorization(), receipt(), outcome()
        )
        self.assertEqual(verified.status, OutcomeStatus.VERIFIED_IMPROVED)

    def test_no_success_claim_without_pre_post_evidence(self):
        self.assertEqual(
            classify_outcome(
                baseline_value=0.61,
                observed_value=0.65,
                pre_evidence_refs=(),
                post_evidence_refs=("metric:after",),
            ),
            OutcomeStatus.INSUFFICIENT_EVIDENCE,
        )

    def test_model_learning_requires_dataset_admission(self):
        with self.assertRaises(LearningAdmissionError):
            BehavioralEvidenceLoop.propose_learning(
                outcome(), proposal_id="learning-1", purpose="model_training"
            )
        proposal = BehavioralEvidenceLoop.propose_learning(
            outcome(),
            proposal_id="learning-2",
            purpose="model_training",
            dataset_admission_ref="dataset-admission:44",
        )
        self.assertEqual(proposal.authority_effect, "none")


if __name__ == "__main__":
    unittest.main()
