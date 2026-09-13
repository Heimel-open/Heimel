import unittest

from connectors.logrocket import (
    AuthorizationBindingV1,
    BehavioralAction,
    ImprovementCandidateV1,
    LogRocketGalileoAdapter,
    ObservationMode,
    OutcomeStatus,
    PrivacyClass,
    PrivacyEnvelopeV1,
    RedactionState,
    ExecutionReceiptV1,
    execution_boundary,
)


ACTION_DIGEST = "b" * 64
PAYLOAD_DIGEST = "a" * 64


def privacy() -> PrivacyEnvelopeV1:
    return PrivacyEnvelopeV1(
        tenant_id="tenant-a",
        scope="checkout",
        collection_purpose="product_improvement",
        classification=PrivacyClass.CONFIDENTIAL,
        redaction_state=RedactionState.REDACTED,
        retention_class="30d",
        residency="eu",
        rights_basis_ref="contract:tenant-a",
    )


def observation():
    return LogRocketGalileoAdapter().normalize_funnel_insight(
        evidence_id="beh-001",
        insight_id="galileo-42",
        summary="Users repeatedly abandon checkout after returning to shipping",
        session_refs=("session-1", "session-2", "session-1"),
        payload_digest=PAYLOAD_DIGEST,
        observed_at="2026-08-11T04:00:00Z",
        captured_at="2026-08-11T04:01:00Z",
        privacy=privacy(),
        provenance_ref="logrocket:galileo:funnel-insight",
        mode=ObservationMode.SHADOW,
        funnel_ref="checkout",
        step_ref="payment",
    )


def finding():
    return LogRocketGalileoAdapter().build_finding(
        finding_id="finding-001",
        observation=observation(),
        expected_condition_ref="slo:checkout-completion",
        confidence=0.82,
        materiality="high",
        reproducibility_ref="query:galileo-42",
    )


def candidate(actions=(BehavioralAction.PROPOSE_BUILD_ORDER,)):
    return LogRocketGalileoAdapter().build_candidate(
        candidate_id="candidate-001",
        finding=finding(),
        hypothesis="Shipping return path creates checkout friction",
        candidate_change="simplify_checkout_return_path",
        target_ref="repo:checkout/web",
        expected_outcome="checkout_completion_rate_increases",
        action_payload_digest=ACTION_DIGEST,
        validation_refs=("test:payment-state", "shadow:checkout-conversion"),
        owner_ref="team:factory",
        requested_actions=actions,
    )


class LogRocketGalileoAdapterTests(unittest.TestCase):
    def test_normalizes_into_shared_observation_contract(self):
        normalized = observation()
        self.assertEqual(normalized.mode, ObservationMode.SHADOW)
        self.assertEqual(len(normalized.evidence_refs), 1)
        evidence = normalized.evidence_refs[0]
        self.assertEqual(evidence.source_type, "logrocket_galileo")
        self.assertEqual(evidence.privacy.tenant_id, "tenant-a")
        self.assertEqual(evidence.metadata["session_refs"], "session-1,session-2")

    def test_rejects_insight_without_supporting_sessions(self):
        with self.assertRaises(ValueError):
            LogRocketGalileoAdapter().normalize_funnel_insight(
                evidence_id="beh-002",
                insight_id="galileo-43",
                summary="Drop-off pattern",
                session_refs=(),
                payload_digest=PAYLOAD_DIGEST,
                observed_at="2026-08-11T04:00:00Z",
                captured_at="2026-08-11T04:01:00Z",
                privacy=privacy(),
                provenance_ref="logrocket:galileo:funnel-insight",
            )

    def test_galileo_explanation_remains_derived_claim(self):
        derived = finding()
        self.assertEqual(derived.generated_by, "logrocket_galileo")
        self.assertEqual(derived.claim_kind.value, "model_explanation")
        self.assertEqual(derived.evidence_refs, ("beh-001",))

    def test_can_propose_bounded_factory_work(self):
        proposed = candidate(
            (BehavioralAction.ANALYZE, BehavioralAction.PROPOSE_BUILD_ORDER)
        )
        self.assertFalse(proposed.requires_execution_authorization())
        self.assertEqual(execution_boundary(proposed), "FACTORY_VALIDATE")

    def test_adapter_cannot_request_merge_or_deploy(self):
        for action in (
            BehavioralAction.MERGE,
            BehavioralAction.DEPLOY,
            BehavioralAction.MUTATE_PRODUCTION,
        ):
            with self.subTest(action=action):
                with self.assertRaises(PermissionError):
                    candidate((action,))

    def test_external_consequential_candidate_routes_to_reht(self):
        external = ImprovementCandidateV1(
            candidate_id="candidate-external",
            finding_refs=("finding-001",),
            hypothesis="known",
            proposed_change_type="deploy_patch",
            target_ref="prod:checkout",
            expected_outcome="checkout_completion_rate_increases",
            action_payload_digest=ACTION_DIGEST,
            requested_actions=(BehavioralAction.DEPLOY,),
            risk_class="high",
            required_evaluation_refs=("test:green",),
            owner_ref="team:release",
        )
        self.assertEqual(execution_boundary(external), "REHT_REQUIRED")

    def test_post_deploy_outcome_is_bound_to_reht_and_veritas_receipt(self):
        proposed = candidate()
        authorization = AuthorizationBindingV1(
            authorization_id="auth-001",
            candidate_id=proposed.candidate_id,
            action_payload_digest=ACTION_DIGEST,
            principal_ref="human:njaal",
            mandate_ref="mandate:checkout-release",
            reht_decision_ref="reht:decision-001",
            authorized_state_ref="state:checkout-123",
            authorized_at="2026-08-11T05:00:00Z",
            expires_at="2026-08-11T07:00:00Z",
        )
        receipt = ExecutionReceiptV1(
            receipt_id="receipt-001",
            candidate_id=proposed.candidate_id,
            action_payload_digest=ACTION_DIGEST,
            authorization_id=authorization.authorization_id,
            executed_at="2026-08-11T06:00:00Z",
            result_artifact_ref="deploy:checkout-456",
            veritas_receipt_ref="veritas:receipt-001",
            deployment_ref="deploy:checkout-456",
        )
        outcome = LogRocketGalileoAdapter().build_outcome_evidence(
            outcome_id="outcome-001",
            candidate=proposed,
            authorization=authorization,
            receipt=receipt,
            pre_evidence_refs=("beh-before",),
            post_evidence_refs=("beh-after",),
            observed_outcome="checkout completion increased",
            comparison_method="conversion_rate_before_after",
            window_start="2026-08-11T06:00:00Z",
            window_end="2026-08-11T07:00:00Z",
            metric_name="checkout_completion_rate",
            baseline_value=0.40,
            observed_value=0.55,
            causal_caveats=("traffic_mix_changed",),
        )
        self.assertEqual(outcome.status, OutcomeStatus.VERIFIED_IMPROVED)
        self.assertEqual(outcome.authorization_id, "auth-001")
        self.assertEqual(outcome.execution_receipt_id, "receipt-001")
        self.assertEqual(outcome.action_payload_digest, ACTION_DIGEST)

    def test_missing_post_evidence_cannot_be_claimed_as_success(self):
        proposed = candidate()
        authorization = AuthorizationBindingV1(
            authorization_id="auth-002",
            candidate_id=proposed.candidate_id,
            action_payload_digest=ACTION_DIGEST,
            principal_ref="human:njaal",
            mandate_ref="mandate:checkout-release",
            reht_decision_ref="reht:decision-002",
            authorized_state_ref="state:checkout-123",
            authorized_at="2026-08-11T05:00:00Z",
            expires_at="2026-08-11T07:00:00Z",
        )
        receipt = ExecutionReceiptV1(
            receipt_id="receipt-002",
            candidate_id=proposed.candidate_id,
            action_payload_digest=ACTION_DIGEST,
            authorization_id=authorization.authorization_id,
            executed_at="2026-08-11T06:00:00Z",
            result_artifact_ref="deploy:checkout-457",
            veritas_receipt_ref="veritas:receipt-002",
        )
        outcome = LogRocketGalileoAdapter().build_outcome_evidence(
            outcome_id="outcome-002",
            candidate=proposed,
            authorization=authorization,
            receipt=receipt,
            pre_evidence_refs=("beh-before",),
            post_evidence_refs=(),
            observed_outcome="unknown",
            comparison_method="conversion_rate_before_after",
            window_start="2026-08-11T06:00:00Z",
            window_end="2026-08-11T07:00:00Z",
            metric_name="checkout_completion_rate",
            baseline_value=0.40,
            observed_value=0.55,
        )
        self.assertEqual(outcome.status, OutcomeStatus.INSUFFICIENT_EVIDENCE)


if __name__ == "__main__":
    unittest.main()
