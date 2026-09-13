import copy
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib import parallel_rl as prl

D = {
    "base": "1" * 64,
    "dataset1": "2" * 64,
    "dataset2": "3" * 64,
    "reward1": "4" * 64,
    "reward2": "5" * 64,
    "delta1": "6" * 64,
    "delta2": "7" * 64,
    "eval1": "8" * 64,
    "eval2": "9" * 64,
    "neg1": "a" * 64,
    "neg2": "b" * 64,
    "compat1": "c" * 64,
    "compat2": "d" * 64,
    "plan": "e" * 64,
}


def capability(capability_id, version, dataset, reward, delta, evaluation, negative, compatibility):
    return {
        "capability_id": capability_id,
        "version": version,
        "base_model_digest": D["base"],
        "dataset_digest": dataset,
        "reward_spec_digest": reward,
        "delta_digest": delta,
        "evaluation_receipt_digests": [evaluation],
        "negative_test_receipt_digest": negative,
        "compatibility_receipt_digest": compatibility,
        "status": "EVALUATED_CANDIDATE",
    }


def base_request():
    return {
        "strategy": "parallel_rl",
        "composition_id": "compose-42",
        "purpose_id": "purpose:model-specialization",
        "target_model_name": "candidate-multiskill-v1",
        "composition_evaluation_plan_digest": D["plan"],
        "capabilities": [
            capability("skill:a", "1", D["dataset1"], D["reward1"], D["delta1"], D["eval1"], D["neg1"], D["compat1"]),
            capability("skill:b", "1", D["dataset2"], D["reward2"], D["delta2"], D["eval2"], D["neg2"], D["compat2"]),
        ],
        "auto_promote": False,
    }


class ParallelRLTests(unittest.TestCase):
    def test_valid_request_emits_candidate_only_manifest(self):
        out = prl.build_composition_candidate(base_request())
        self.assertEqual(out["contract"], prl.CONTRACT)
        self.assertEqual(out["composition_status"], "CANDIDATE_REQUIRES_EVALUATION")
        self.assertEqual(out["promotion"]["mode"], "candidate_only")
        self.assertFalse(out["authority"]["granted"])

    def test_requires_two_capabilities(self):
        req = base_request()
        req["capabilities"] = req["capabilities"][:1]
        with self.assertRaises(prl.ParallelRLError):
            prl.build_composition_candidate(req)

    def test_requires_same_base(self):
        req = base_request()
        req["capabilities"][1]["base_model_digest"] = "f" * 64
        with self.assertRaises(prl.ParallelRLError):
            prl.build_composition_candidate(req)

    def test_capability_ids_must_be_unique(self):
        req = base_request()
        req["capabilities"][1]["capability_id"] = req["capabilities"][0]["capability_id"]
        with self.assertRaises(prl.ParallelRLError):
            prl.build_composition_candidate(req)

    def test_delta_digests_must_be_unique(self):
        req = base_request()
        req["capabilities"][1]["delta_digest"] = req["capabilities"][0]["delta_digest"]
        with self.assertRaises(prl.ParallelRLError):
            prl.build_composition_candidate(req)

    def test_evaluation_receipts_are_required(self):
        req = base_request()
        req["capabilities"][0]["evaluation_receipt_digests"] = []
        with self.assertRaises(prl.ParallelRLError):
            prl.build_composition_candidate(req)

    def test_negative_test_receipt_is_required(self):
        req = base_request()
        req["capabilities"][0]["negative_test_receipt_digest"] = ""
        with self.assertRaises(prl.ParallelRLError):
            prl.build_composition_candidate(req)

    def test_compatibility_receipt_is_required(self):
        req = base_request()
        req["capabilities"][0]["compatibility_receipt_digest"] = ""
        with self.assertRaises(prl.ParallelRLError):
            prl.build_composition_candidate(req)

    def test_authority_fields_are_rejected(self):
        req = base_request()
        req["capabilities"][0]["grants_authority"] = True
        with self.assertRaises(prl.ParallelRLError):
            prl.build_composition_candidate(req)

    def test_automatic_promotion_is_rejected(self):
        req = base_request()
        req["auto_promote"] = True
        with self.assertRaises(prl.ParallelRLError):
            prl.build_composition_candidate(req)

    def test_individual_evaluation_does_not_mark_composition_admitted(self):
        out = prl.build_composition_candidate(base_request())
        self.assertNotEqual(out["composition_status"], "ADMITTED")
        self.assertTrue(out["promotion"]["requires_new_admission"])

    def test_manifest_digest_is_deterministic(self):
        first = prl.build_composition_candidate(base_request())
        second = prl.build_composition_candidate(copy.deepcopy(base_request()))
        self.assertEqual(first["composition_digest"], second["composition_digest"])


if __name__ == "__main__":
    unittest.main()
