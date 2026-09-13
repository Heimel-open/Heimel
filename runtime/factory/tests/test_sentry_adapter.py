import unittest

from connectors.sentry import (
    OutcomeStatus,
    PostDeployEvidence,
    SentryCodingAgentAdapter,
    SentryIncidentEvidence,
    SentryRepairAction,
    next_boundary,
)


class TestSentryCodingAgentAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = SentryCodingAgentAdapter()
        self.incident = SentryIncidentEvidence(
            issue_id="12345",
            event_id="evt-1",
            project_slug="payments-api",
            summary="Checkout returns 500",
            trace_refs=("trace:abc",),
            repository_ref="nsolland/example@deadbeef",
        )

    def test_builds_coding_agent_handoff_without_authority(self):
        request = self.adapter.build_coding_agent_handoff(
            organization="valo",
            incident=self.incident,
            integration_id=42,
            repo_name="nsolland/example",
            user_context="Investigate only the failing checkout path",
        )

        self.assertEqual(request.method, "POST")
        self.assertEqual(
            request.path,
            "/api/0/organizations/valo/issues/12345/autofix/",
        )
        self.assertEqual(request.body["step"], "coding_agent_handoff")
        self.assertEqual(request.body["stopping_point"], "code_changes")
        self.assertEqual(request.body["integration_id"], 42)
        self.assertEqual(request.authority_effect, "none")

    def test_requires_coding_agent_provider_or_integration(self):
        with self.assertRaises(ValueError):
            self.adapter.build_coding_agent_handoff(
                organization="valo",
                incident=self.incident,
            )

    def test_rejects_unknown_stopping_point(self):
        with self.assertRaises(ValueError):
            self.adapter.build_coding_agent_handoff(
                organization="valo",
                incident=self.incident,
                integration_id=42,
                stopping_point="merge",
            )

    def test_allows_patch_and_open_pr_but_not_merge_or_deploy(self):
        proposal = self.adapter.build_proposal(
            incident=self.incident,
            sentry_run_id="run-1",
            root_cause="Null cart reaches checkout",
            patch_ref="patch:sha256:abc",
            validation_refs=("test:unit", "test:integration"),
            requested_actions=(
                SentryRepairAction.PROPOSE_PATCH,
                SentryRepairAction.OPEN_PR,
            ),
        )
        self.assertEqual(next_boundary(proposal), "FACTORY_VALIDATE")

        for action in (
            SentryRepairAction.MERGE,
            SentryRepairAction.DEPLOY,
            SentryRepairAction.MUTATE_DATA,
        ):
            with self.subTest(action=action):
                with self.assertRaises(PermissionError):
                    self.adapter.build_proposal(
                        incident=self.incident,
                        sentry_run_id="run-1",
                        root_cause="Null cart reaches checkout",
                        patch_ref="patch:sha256:abc",
                        requested_actions=(action,),
                    )

    def test_verifies_no_recurrence_after_deploy(self):
        result = self.adapter.verify_post_deploy(
            PostDeployEvidence(
                issue_id="12345",
                deployment_ref="deploy:2026-08-10.1",
                verification_window_seconds=3600,
                before_event_count=17,
                after_event_count=0,
                trace_refs=("trace:post-deploy",),
            )
        )
        self.assertEqual(result.status, OutcomeStatus.VERIFIED_NO_RECURRENCE)

    def test_detects_regression_and_insufficient_baseline(self):
        regression = self.adapter.verify_post_deploy(
            PostDeployEvidence(
                issue_id="12345",
                deployment_ref="deploy:bad",
                verification_window_seconds=600,
                before_event_count=2,
                after_event_count=5,
            )
        )
        self.assertEqual(regression.status, OutcomeStatus.REGRESSION)

        insufficient = self.adapter.verify_post_deploy(
            PostDeployEvidence(
                issue_id="12345",
                deployment_ref="deploy:unknown",
                verification_window_seconds=600,
                before_event_count=0,
                after_event_count=0,
            )
        )
        self.assertEqual(insufficient.status, OutcomeStatus.INSUFFICIENT_EVIDENCE)


if __name__ == "__main__":
    unittest.main()
