import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from execution_profile_routing import (  # noqa: E402
    ExecutionProfile,
    ExecutionProfileRoutingError,
    ProfileObservation,
    ProfileRoutingRequest,
    UNVERIFIED,
    VERIFIED_COMPLETE,
    VERIFIED_INCOMPLETE,
    request_from_dict,
    route_execution_profiles,
)


def profile(profile_id, *, provider="p", runtime="vllm", capabilities=("code",)):
    return ExecutionProfile(
        profile_id=profile_id,
        handler="worker",
        provider_id=provider,
        harness_id="native",
        runtime_id=runtime,
        model_id="qwen-27b",
        sandbox_id="firecracker",
        quantization="int4",
        cache_strategy="prefix",
        capabilities=capabilities,
    )


def obs(
    observation_id,
    profile_id,
    outcome,
    *,
    latency=100,
    cost=10,
    verifier="veritas:r1",
    task_class="coding",
):
    return ProfileObservation(
        observation_id=observation_id,
        profile_id=profile_id,
        task_class=task_class,
        outcome=outcome,
        execution_receipt_ref=f"receipt:{observation_id}",
        verifier_ref=verifier,
        latency_ms=latency,
        cost_microunits=cost,
    )


class ExecutionProfileRoutingTests(unittest.TestCase):
    def test_verified_completion_dominates_latency_and_cost(self):
        slow_good = profile("slow-good")
        fast_bad = profile("fast-bad")
        req = ProfileRoutingRequest(
            task_id="t1",
            task_class="coding",
            candidates=(slow_good, fast_bad),
            observations=(
                obs("1", "slow-good", VERIFIED_COMPLETE, latency=1000, cost=1000),
                obs("2", "fast-bad", VERIFIED_INCOMPLETE, latency=10, cost=1),
            ),
        )
        receipt = route_execution_profiles(req)
        self.assertEqual(receipt.suggestions[0].profile.profile_id, "slow-good")
        self.assertGreater(receipt.suggestions[0].completion_score, 0.5)

    def test_unverified_success_cannot_improve_completion_score(self):
        candidate = profile("candidate")
        req = ProfileRoutingRequest(
            task_id="t2",
            task_class="coding",
            candidates=(candidate,),
            observations=(
                ProfileObservation(
                    observation_id="u1",
                    profile_id="candidate",
                    task_class="coding",
                    outcome=UNVERIFIED,
                    execution_receipt_ref="receipt:u1",
                    latency_ms=5,
                    cost_microunits=1,
                ),
            ),
        )
        suggestion = route_execution_profiles(req).suggestions[0]
        self.assertEqual(suggestion.verified_attempts, 0)
        self.assertEqual(suggestion.verified_completions, 0)
        self.assertEqual(suggestion.completion_score, 0.5)
        self.assertIsNone(suggestion.avg_latency_ms)
        self.assertIsNone(suggestion.avg_cost_microunits)

    def test_verified_outcome_requires_verifier(self):
        candidate = profile("candidate")
        req = ProfileRoutingRequest(
            task_id="t3",
            task_class="coding",
            candidates=(candidate,),
            observations=(obs("1", "candidate", VERIFIED_COMPLETE, verifier=None),),
        )
        with self.assertRaises(ExecutionProfileRoutingError):
            route_execution_profiles(req)

    def test_required_capability_filters_before_ranking(self):
        code = profile("code", capabilities=("code", "shell"))
        research = profile("research", capabilities=("research",))
        req = ProfileRoutingRequest(
            task_id="t4",
            task_class="coding",
            candidates=(research, code),
            required_capabilities=("shell",),
        )
        receipt = route_execution_profiles(req)
        self.assertEqual([s.profile.profile_id for s in receipt.suggestions], ["code"])

    def test_provider_and_runtime_constraints_are_hard_filters(self):
        a = profile("a", provider="provider-a", runtime="sglang")
        b = profile("b", provider="provider-b", runtime="vllm")
        req = ProfileRoutingRequest(
            task_id="t5",
            task_class="coding",
            candidates=(a, b),
            allowed_providers=("provider-b",),
            allowed_runtimes=("vllm",),
        )
        receipt = route_execution_profiles(req)
        self.assertEqual(receipt.suggestions[0].profile.profile_id, "b")

    def test_full_profile_identity_is_preserved(self):
        candidate = profile("candidate")
        output = route_execution_profiles(ProfileRoutingRequest(
            task_id="t6",
            task_class="coding",
            candidates=(candidate,),
        )).as_dict()
        stored = output["suggestions"][0]["profile"]
        self.assertEqual(stored["provider_id"], "p")
        self.assertEqual(stored["harness_id"], "native")
        self.assertEqual(stored["runtime_id"], "vllm")
        self.assertEqual(stored["model_id"], "qwen-27b")
        self.assertEqual(stored["quantization"], "int4")
        self.assertEqual(stored["cache_strategy"], "prefix")
        self.assertEqual(stored["sandbox_id"], "firecracker")
        self.assertNotIn("gpu", stored)
        self.assertNotIn("hardware", stored)

    def test_authority_bearing_profile_fails_closed(self):
        candidate = ExecutionProfile(
            profile_id="bad",
            handler="worker",
            provider_id="p",
            harness_id="native",
            runtime_id="runtime",
            model_id="model",
            sandbox_id="sandbox",
            authority_effect="allow",
        )
        with self.assertRaises(ExecutionProfileRoutingError):
            route_execution_profiles(ProfileRoutingRequest(
                task_id="t7", task_class="coding", candidates=(candidate,)
            ))

    def test_task_class_isolation(self):
        a = profile("a")
        b = profile("b")
        req = ProfileRoutingRequest(
            task_id="t8",
            task_class="coding",
            candidates=(a, b),
            observations=(
                obs("1", "a", VERIFIED_INCOMPLETE, task_class="coding"),
                obs("2", "b", VERIFIED_COMPLETE, task_class="research"),
            ),
        )
        receipt = route_execution_profiles(req)
        self.assertEqual(receipt.suggestions[0].profile.profile_id, "b")
        self.assertEqual(receipt.suggestions[0].completion_score, 0.5)

    def test_unknown_profile_beats_one_verified_failure(self):
        failed = profile("failed")
        unseen = profile("unseen")
        req = ProfileRoutingRequest(
            task_id="t9",
            task_class="coding",
            candidates=(failed, unseen),
            observations=(obs("1", "failed", VERIFIED_INCOMPLETE),),
        )
        receipt = route_execution_profiles(req)
        self.assertEqual(receipt.suggestions[0].profile.profile_id, "unseen")

    def test_replay_is_deterministic(self):
        candidate = profile("candidate")
        req = ProfileRoutingRequest(
            task_id="t10",
            task_class="coding",
            candidates=(candidate,),
            observations=(obs("1", "candidate", VERIFIED_COMPLETE),),
        )
        a = route_execution_profiles(req).as_dict()
        b = route_execution_profiles(req).as_dict()
        self.assertEqual(a, b)
        self.assertTrue(a["request_digest"].startswith("sha256:"))
        self.assertEqual(a["authority_effect"], "none")

    def test_json_parser_preserves_authority_boundary(self):
        raw = {
            "task_id": "t11",
            "task_class": "coding",
            "candidates": [{
                "profile_id": "p1",
                "handler": "worker",
                "provider_id": "provider",
                "harness_id": "native",
                "runtime_id": "sglang",
                "model_id": "model",
                "sandbox_id": "sandbox",
                "capabilities": ["code"],
            }],
            "observations": [],
            "required_capabilities": ["code"],
        }
        receipt = route_execution_profiles(request_from_dict(raw))
        self.assertEqual(receipt.authority_effect, "none")
        self.assertEqual(receipt.suggestions[0].authority_effect, "none")

    def test_parser_rejects_non_string_capability(self):
        raw = {
            "task_id": "t12",
            "task_class": "coding",
            "candidates": [{
                "profile_id": "p1",
                "handler": "worker",
                "provider_id": "provider",
                "harness_id": "native",
                "runtime_id": "sglang",
                "model_id": "model",
                "sandbox_id": "sandbox",
                "capabilities": [123],
            }],
        }
        with self.assertRaises(ExecutionProfileRoutingError):
            request_from_dict(raw)

    def test_parser_rejects_boolean_metrics_and_k(self):
        base = {
            "task_id": "t13",
            "task_class": "coding",
            "candidates": [{
                "profile_id": "p1",
                "handler": "worker",
                "provider_id": "provider",
                "harness_id": "native",
                "runtime_id": "sglang",
                "model_id": "model",
                "sandbox_id": "sandbox",
            }],
            "observations": [{
                "observation_id": "o1",
                "profile_id": "p1",
                "task_class": "coding",
                "outcome": "UNVERIFIED",
                "execution_receipt_ref": "receipt:o1",
                "latency_ms": True,
            }],
        }
        with self.assertRaises(ExecutionProfileRoutingError):
            request_from_dict(base)
        base["observations"] = []
        base["k"] = True
        with self.assertRaises(ExecutionProfileRoutingError):
            request_from_dict(base)


if __name__ == "__main__":
    unittest.main()
