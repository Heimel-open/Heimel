import unittest

from connectors.superlog import (
    IncidentEvidence,
    RepairAction,
    RepairProposal,
    SuperlogRepairAdapter,
    execution_boundary,
)


def incident():
    return IncidentEvidence(
        alert_id="sentry-123",
        source="sentry",
        summary="500s after checkout deploy",
        trace_refs=("trace-abc",),
        repository_ref="nsolland/example@abc123",
    )


class SuperlogAdapterTests(unittest.TestCase):
    def test_adapter_can_investigate_and_propose_patch(self):
        proposal = SuperlogRepairAdapter().build_proposal(
            incident=incident(),
            root_cause="nil checkout session",
            patch_ref="refs/heads/repair/checkout",
            validation_refs=("pytest:green",),
            requested_actions=(RepairAction.INVESTIGATE, RepairAction.PROPOSE_PATCH),
        )

        self.assertEqual(proposal.patch_ref, "refs/heads/repair/checkout")
        self.assertEqual(execution_boundary(proposal), "FACTORY_VALIDATE")

    def test_adapter_cannot_claim_consequential_authority(self):
        for action in [RepairAction.MERGE, RepairAction.DEPLOY, RepairAction.MUTATE_DATA]:
            with self.subTest(action=action):
                with self.assertRaises(PermissionError):
                    SuperlogRepairAdapter().build_proposal(
                        incident=incident(),
                        root_cause="known",
                        patch_ref="patch-1",
                        requested_actions=(action,),
                    )

    def test_external_proposal_requesting_execution_routes_to_reht(self):
        proposal = RepairProposal(
            incident=incident(),
            root_cause="known",
            patch_ref="patch-1",
            requested_actions=(RepairAction.DEPLOY,),
        )

        self.assertTrue(proposal.requires_execution_authorization())
        self.assertEqual(execution_boundary(proposal), "REHT_REQUIRED")


if __name__ == "__main__":
    unittest.main()

