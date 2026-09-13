import unittest

from lib import model_lifecycle as ml


D = {
    "workspace": "1" * 64,
    "state": "2" * 64,
    "prov1": "3" * 64,
    "prov2": "4" * 64,
    "dataset": "5" * 64,
    "runtime": "6" * 64,
    "vaig": "7" * 64,
    "reht": "8" * 64,
    "racs": "9" * 64,
    "pep": "a" * 64,
    "artifact": "c" * 64,
    "execution": "d" * 64,
    "eval": "e" * 64,
}


def rebind(value):
    core = dict(value)
    core.pop("pep_handoff", None)
    value["pep_handoff"]["handoff_digest"] = ml.digest(core)
    return value


def handoff():
    value = {
        "contract": "valo.governed-model-factory.v1",
        "workspace": {
            "workspace_id": "workspace-42",
            "workspace_digest": D["workspace"],
        },
        "state_admission": {
            "status": "ADMITTED",
            "state_digest": D["state"],
            "provenance": [D["prov1"], D["prov2"]],
        },
        "engine": {
            "engine_id": "unsloth",
            "commit": "f" * 40,
            "runtime_digest": D["runtime"],
        },
        "governance": [
            {"stage": "VAIG", "decision": "ALLOW", "receipt_digest": D["vaig"]},
            {"stage": "reht", "decision": "ALLOW", "receipt_digest": D["reht"]},
            {"stage": "RACS", "decision": "ALLOW", "receipt_digest": D["racs"]},
            {"stage": "PEP", "decision": "ALLOW", "receipt_digest": D["pep"]},
        ],
        "training_spec": {
            "dataset_digest": D["dataset"],
            "objective": "bounded specialization",
            "output_name": "candidate-v1",
        },
        "promotion": {
            "mode": "candidate_only",
            "automatic": False,
            "requires_new_admission": True,
        },
        "pep_handoff": {
            "may_execute": True,
            "max_attempts": 1,
            "handoff_digest": "0" * 64,
        },
    }
    return rebind(value)


def candidate():
    return ml.CandidateModelReceipt.issue(
        handoff(),
        candidate_id="candidate:1",
        artifact_digest=D["artifact"],
        execution_receipt_digest=D["execution"],
    )


def evaluation(value, passed=True, candidate_digest=None):
    return ml.HonestEvaluationEvidence.from_mapping(
        {
            "evaluation_ref": "honest-eval:1",
            "candidate_id": value.candidate_id,
            "candidate_receipt_digest": candidate_digest or value.receipt_digest,
            "evidence_digest": D["eval"],
            "evaluator_id": "principal:evaluator",
            "passed": passed,
        }
    )


def mal(value, decision="ADMIT", candidate_digest=None):
    return ml.MALDecision.from_mapping(
        {
            "decision_ref": "mal:1",
            "candidate_id": value.candidate_id,
            "candidate_receipt_digest": candidate_digest or value.receipt_digest,
            "decision": decision,
            "domain": "customer-support",
            "exclusions": ["payments"],
            "owner": "owner:model",
            "risk_owner": "risk:model",
            "review_date": "2026-09-15",
        }
    )


class ModelLifecycleTests(unittest.TestCase):
    def test_training_output_is_candidate_only(self):
        value = candidate()
        self.assertEqual(value.state, "CANDIDATE")
        self.assertEqual(value.contract, "valo.model-candidate-receipt.v1")

    def test_candidate_requires_executable_pep_handoff(self):
        value = handoff()
        value["pep_handoff"]["may_execute"] = False
        with self.assertRaisesRegex(ml.ModelLifecycleError, "NULL_EFFECT_ON_DENY"):
            ml.CandidateModelReceipt.issue(
                value,
                candidate_id="candidate:1",
                artifact_digest=D["artifact"],
                execution_receipt_digest=D["execution"],
            )

    def test_non_allow_governance_cannot_create_candidate(self):
        value = handoff()
        value["governance"][2]["decision"] = "DENY"
        rebind(value)
        with self.assertRaisesRegex(ml.ModelLifecycleError, "NULL_EFFECT_ON_DENY"):
            ml.CandidateModelReceipt.issue(
                value,
                candidate_id="candidate:1",
                artifact_digest=D["artifact"],
                execution_receipt_digest=D["execution"],
            )

    def test_candidate_requires_single_attempt_lineage(self):
        value = handoff()
        value["pep_handoff"]["max_attempts"] = 2
        with self.assertRaisesRegex(ml.ModelLifecycleError, "max_attempts=1"):
            ml.CandidateModelReceipt.issue(
                value,
                candidate_id="candidate:1",
                artifact_digest=D["artifact"],
                execution_receipt_digest=D["execution"],
            )

    def test_candidate_cannot_inherit_automatic_admission(self):
        value = handoff()
        value["promotion"]["automatic"] = True
        rebind(value)
        with self.assertRaisesRegex(ml.ModelLifecycleError, "CANDIDATE_NOT_ADMITTED"):
            ml.CandidateModelReceipt.issue(
                value,
                candidate_id="candidate:1",
                artifact_digest=D["artifact"],
                execution_receipt_digest=D["execution"],
            )

    def test_tampered_handoff_core_is_rejected(self):
        value = handoff()
        value["training_spec"]["dataset_digest"] = "0" * 64
        with self.assertRaisesRegex(ml.ModelLifecycleError, "does not bind"):
            ml.CandidateModelReceipt.issue(
                value,
                candidate_id="candidate:1",
                artifact_digest=D["artifact"],
                execution_receipt_digest=D["execution"],
            )

    def test_provenance_continuity_survives_candidate_creation(self):
        source = handoff()
        value = ml.CandidateModelReceipt.issue(
            source,
            candidate_id="candidate:1",
            artifact_digest=D["artifact"],
            execution_receipt_digest=D["execution"],
        )
        self.assertEqual(value.workspace_digest, D["workspace"])
        self.assertEqual(value.state_digest, D["state"])
        self.assertEqual(value.dataset_digest, D["dataset"])
        self.assertEqual(value.provenance, (D["prov1"], D["prov2"]))
        self.assertEqual(value.pep_handoff_digest, source["pep_handoff"]["handoff_digest"])
        self.assertEqual(value.execution_receipt_digest, D["execution"])

    def test_candidate_is_not_runtime_eligible(self):
        with self.assertRaisesRegex(ml.ModelLifecycleError, "CANDIDATE_NOT_ADMITTED"):
            ml.require_runtime_admitted(candidate())

    def test_failed_honest_evaluation_blocks_admission(self):
        value = candidate()
        with self.assertRaisesRegex(ml.ModelLifecycleError, "Honest Evaluation did not pass"):
            ml.promote_candidate(
                value,
                model_id="model:1",
                evaluation=evaluation(value, passed=False),
                mal=mal(value),
            )

    def test_mal_defer_blocks_admission(self):
        value = candidate()
        with self.assertRaisesRegex(ml.ModelLifecycleError, "MAL decision is DEFER"):
            ml.promote_candidate(
                value,
                model_id="model:1",
                evaluation=evaluation(value),
                mal=mal(value, decision="DEFER"),
            )

    def test_evaluation_must_bind_exact_candidate_receipt(self):
        value = candidate()
        with self.assertRaisesRegex(ml.ModelLifecycleError, "evaluation evidence is not bound"):
            ml.promote_candidate(
                value,
                model_id="model:1",
                evaluation=evaluation(value, candidate_digest="0" * 64),
                mal=mal(value),
            )

    def test_mal_must_bind_exact_candidate_receipt(self):
        value = candidate()
        with self.assertRaisesRegex(ml.ModelLifecycleError, "mal evidence is not bound"):
            ml.promote_candidate(
                value,
                model_id="model:1",
                evaluation=evaluation(value),
                mal=mal(value, candidate_digest="0" * 64),
            )

    def test_admitted_record_is_runtime_eligible_and_preserves_lineage(self):
        value = candidate()
        admitted = ml.promote_candidate(
            value,
            model_id="model:1",
            evaluation=evaluation(value),
            mal=mal(value),
        )
        self.assertEqual(ml.require_runtime_admitted(admitted), admitted)
        self.assertEqual(admitted.state, "ADMITTED")
        self.assertEqual(admitted.artifact_digest, D["artifact"])
        self.assertEqual(admitted.dataset_digest, D["dataset"])
        self.assertEqual(admitted.provenance, (D["prov1"], D["prov2"]))
        self.assertEqual(admitted.exclusions, ("payments",))
        self.assertEqual(admitted.risk_owner, "risk:model")


if __name__ == "__main__":
    unittest.main()
