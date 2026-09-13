import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parent.parent


class EcosystemAdoptionTests(unittest.TestCase):
    def test_all_signals_are_adopted_without_authority(self):
        registry = json.loads(
            (ROOT / "config" / "ecosystem-adoptions.json").read_text(encoding="utf-8")
        )
        signals = {item["id"]: item for item in registry["signals"]}
        self.assertEqual(
            set(signals),
            {
                "meta-muse-code",
                "copilotkit-channels",
                "shieldstral",
                "rippling-ai-spend-console",
                "annotate-screen-recording-prompts",
                "bland-conversational-operations",
                "lifeos-work-os",
                "sidekick-frontline-operations",
                "deja-vu-experience-memory",
                "google-adk-long-horizon",
            },
        )
        self.assertTrue(all(item["authority_effect"] == "none" for item in signals.values()))
        self.assertIn(
            "REHT remains the sole final authorization boundary for consequence-bearing execution.",
            registry["global_invariants"],
        )

    def test_muse_code_is_a_replaceable_worker_provider(self):
        registry = json.loads(
            (ROOT / "config" / "ecosystem-adoptions.json").read_text(encoding="utf-8")
        )
        muse = next(item for item in registry["signals"] if item["id"] == "meta-muse-code")
        self.assertEqual(muse["adopt_as"], "provider_neutral_execution_worker_pattern")
        self.assertIn("independent_qc", muse["requirements"])
        self.assertIn("no_self_attestation", muse["requirements"])

        receipt = json.loads(
            (ROOT / "schemas" / "worker-provider-receipt.schema.json").read_text(
                encoding="utf-8"
            )
        )
        required = set(receipt["required"])
        self.assertTrue(
            {
                "provider_id",
                "mission_digest",
                "event_log_digest",
                "result_digest",
                "parallel_worker_count",
                "resumed",
                "authority_effect",
            }.issubset(required)
        )
        self.assertEqual(receipt["properties"]["authority_effect"]["const"], "none")

    def test_bland_operations_are_learning_and_rollout_patterns_only(self):
        registry = json.loads(
            (ROOT / "config" / "ecosystem-adoptions.json").read_text(encoding="utf-8")
        )
        bland = next(
            item for item in registry["signals"] if item["id"] == "bland-conversational-operations"
        )
        self.assertEqual(bland["adopt_as"], "governed_conversational_operations_pattern")
        self.assertEqual(bland["authority_effect"], "none")
        for requirement in (
            "production_failures_become_digest_bound_regression_fixtures",
            "provider_test_pass_is_evidence_not_activation",
            "fixing_worker_cannot_self_attest_success",
            "independent_qc_required_before_promotion",
            "persistent_memory_is_context_not_mandate",
            "memory_never_revives_expired_authority",
            "channel_projection_never_widens_authority",
        ):
            self.assertIn(requirement, bland["requirements"])

    def test_lifeos_is_adopted_as_governed_work_os_pattern_only(self):
        registry = json.loads(
            (ROOT / "config" / "ecosystem-adoptions.json").read_text(encoding="utf-8")
        )
        lifeos = next(item for item in registry["signals"] if item["id"] == "lifeos-work-os")
        self.assertEqual(lifeos["adopt_as"], "governed_work_os_convergence_pattern")
        self.assertEqual(lifeos["authority_effect"], "none")
        self.assertEqual(
            lifeos["dependency_policy"],
            "pattern_adoption_no_required_lifeos_runtime_dependency",
        )
        for requirement in (
            "current_state_and_ideal_state_are_explicit_artifacts",
            "convergence_is_measured_not_assumed",
            "persistent_memory_is_context_and_evidence_not_mandate",
            "capability_routing_is_provider_neutral",
            "high_impact_judgment_prefers_independent_provider",
            "harvest_discovery_outputs_proposals_not_changes",
            "verify_and_learn_require_observed_outcome",
            "self_improvement_enters_factory_as_new_build_order_or_observation",
            "reht_remains_final_authorization_boundary",
        ):
            self.assertIn(requirement, lifeos["requirements"])
        self.assertIn(
            "Persistent Work OS memory, ideal-state definitions and self-improvement proposals never grant authority.",
            registry["global_invariants"],
        )

    def test_sidekick_is_adopted_as_governed_frontline_pattern_only(self):
        registry = json.loads(
            (ROOT / "config" / "ecosystem-adoptions.json").read_text(encoding="utf-8")
        )
        sidekick = next(
            item for item in registry["signals"] if item["id"] == "sidekick-frontline-operations"
        )
        self.assertEqual(sidekick["adopt_as"], "governed_frontline_work_os_pattern")
        self.assertEqual(sidekick["owner_repo"], "nsolland/valo-operator")
        self.assertEqual(sidekick["authority_effect"], "none")
        self.assertEqual(
            sidekick["dependency_policy"],
            "pattern_adoption_no_required_sidekick_runtime_dependency",
        )
        for requirement in (
            "frontline_channel_identity_is_evidence_only",
            "text_photo_voice_normalize_to_provider_neutral_intake",
            "read_answers_require_provenance_and_freshness",
            "insufficient_evidence_escalates_or_abstains",
            "captured_human_answer_is_knowledge_candidate_not_truth",
            "consequence_bearing_work_routes_to_registered_function",
            "existing_system_credentials_are_transport_not_authority",
            "plc_scada_write_requires_fresh_reht_or_micro_reht_at_execution_boundary",
            "execution_success_requires_observed_postcondition_and_receipt",
            "reht_remains_final_authorization_boundary",
        ):
            self.assertIn(requirement, sidekick["requirements"])
        self.assertIn(
            "Frontline channel identity, captured tribal knowledge and provider credentials never grant authority.",
            registry["global_invariants"],
        )

    def test_deja_vu_is_optional_experience_memory_only(self):
        registry = json.loads(
            (ROOT / "config" / "ecosystem-adoptions.json").read_text(encoding="utf-8")
        )
        deja = next(
            item for item in registry["signals"] if item["id"] == "deja-vu-experience-memory"
        )
        self.assertEqual(deja["adopt_as"], "factory_experience_memory_retrieval_pattern")
        self.assertEqual(deja["authority_effect"], "none")
        self.assertEqual(
            deja["dependency_policy"],
            "optional_local_adapter_no_required_deja_vu_runtime_dependency",
        )
        for requirement in (
            "canonical_experience_record_is_provider_neutral",
            "transcript_is_context_not_truth",
            "freshness_and_supersession_are_explicit",
            "stale_or_superseded_memory_is_not_injected",
            "cross_repo_memory_requires_independent_verification",
            "memory_never_creates_or_revives_authority",
            "reht_remains_final_authorization_boundary",
        ):
            self.assertIn(requirement, deja["requirements"])
        self.assertIn(
            "Recalled agent transcripts are context/evidence only and must yield to current code, tests, policy, receipts, freshness and supersession state.",
            registry["global_invariants"],
        )


    def test_google_long_horizon_is_pattern_only(self):
        registry = json.loads(
            (ROOT / "config" / "ecosystem-adoptions.json").read_text(encoding="utf-8")
        )
        signal = next(
            item for item in registry["signals"] if item["id"] == "google-adk-long-horizon"
        )
        self.assertEqual(
            signal["adopt_as"], "provider_neutral_long_horizon_harness_pattern"
        )
        self.assertEqual(signal["authority_effect"], "none")
        self.assertEqual(
            signal["dependency_policy"],
            "pattern_adoption_no_google_adk_or_vertex_dependency",
        )
        self.assertIn(
            "every_consequence_bearing_action_requires_fresh_vaig_reht_racs_binding",
            signal["requirements"],
        )
        self.assertIn(
            "ambiguous_prepared_actions_require_reconciliation",
            signal["requirements"],
        )

    def test_economics_expands_beyond_token_spend(self):
        policy = json.loads(
            (ROOT / "config" / "tokenomics-policy.json").read_text(encoding="utf-8")
        )
        for dimension in (
            "human_time",
            "technical_debt",
            "cleanup_cost",
            "agent_monitoring_cost",
            "opportunity_cost",
            "cancelled_opportunity_cost",
        ):
            self.assertIn(dimension, policy["cost_of_cognition"])
        for value in (
            "time_saved",
            "enabled_opportunity_value",
            "verified_business_outcome",
        ):
            self.assertIn(value, policy["value_of_cognition"])
        self.assertTrue(policy["economic_observability"]["bind_cost_to_verified_outcome"])

        receipt = json.loads(
            (ROOT / "schemas" / "ace-economics-receipt.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(receipt["properties"]["authority_effect"]["const"], "none")
        self.assertIn("outcome_ref", receipt["allOf"][0]["then"]["required"])
        cost_fields = receipt["properties"]["cost_of_cognition"]["properties"]
        self.assertIn("opportunity_cost", cost_fields)
        self.assertIn("technical_debt_cost", cost_fields)
        self.assertIn("cancelled_opportunity_cost", cost_fields)

    def test_visual_intake_is_evidence_only(self):
        schema = json.loads(
            (ROOT / "schemas" / "work-intake-artifact.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("authority_effect", schema["required"])
        self.assertEqual(schema["properties"]["authority_effect"]["const"], "none")
        self.assertIn("expected_behavior", schema["required"])
        self.assertIn("observed_behavior", schema["required"])


if __name__ == "__main__":
    unittest.main()
