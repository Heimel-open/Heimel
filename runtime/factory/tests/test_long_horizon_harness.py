import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from lib.long_horizon_harness import (
    AmbiguousSideEffect,
    AuthorizationDenied,
    HarnessError,
    InvalidTransition,
    JudgeFork,
    LongHorizonHarness,
    SandboxLifecycle,
    SideEffectGate,
    SqliteHarnessStore,
    compact_context,
    digest,
    judge_evidence,
    make_child_context,
)


class LongHorizonHarnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.store = SqliteHarnessStore(root / "harness.db")
        self.sandboxes = SandboxLifecycle(root / "sandboxes")
        self.harness = LongHorizonHarness(self.store, self.sandboxes)
        self.harness.start(
            mission_id="mission-1",
            owner_id="owner-1",
            worker_id="worker-1",
            worker_provider_id="provider-a",
            run_id="run-1",
        )

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def authorization(self, request):
        now = time.time_ns()
        action_digest = request["action_digest"]
        return {
            "action_digest": action_digest,
            "vaig": {
                "evaluation_id": "vaig-1",
                "action_digest": action_digest,
            },
            "reht": {
                "clearance_id": "reht-1",
                "action_digest": action_digest,
            },
            "racs": {
                "decision_id": "racs-1",
                "decision": "ALLOW",
                "action_digest": action_digest,
            },
            "issued_at_ns": now - 1_000,
            "expires_at_ns": now + 5_000_000_000,
            "authority_effect": "execution_clearance",
        }

    def test_checkpoint_resume_preserves_cursor_and_context(self):
        checkpoint = self.harness.checkpoint(
            "run-1",
            state="PAUSED",
            stage="IMPLEMENT",
            cursor="step-7",
            active_context=[{"kind": "fact", "value": "x"}],
            evidence_refs=["veritas:abc"],
        )
        resumed = self.harness.resume("run-1")
        self.assertEqual(resumed["cursor"], "step-7")
        self.assertEqual(resumed["stage"], "IMPLEMENT")
        self.assertEqual(resumed["active_context"], checkpoint["active_context"])
        self.assertEqual(resumed["sandbox_state"], "ACTIVE")
        self.assertEqual(resumed["authority_effect"], "none")

    def test_resume_survives_process_restart_with_durable_sandbox_state(self):
        root = self.sandboxes.root
        self.harness.checkpoint(
            "run-1",
            state="PAUSED",
            stage="DISCOVER",
            cursor="evidence-4",
            active_context=[],
        )
        restarted_sandboxes = SandboxLifecycle(root)
        restarted_harness = LongHorizonHarness(self.store, restarted_sandboxes)
        resumed = restarted_harness.resume("run-1")
        self.assertEqual(resumed["cursor"], "evidence-4")
        self.assertEqual(restarted_sandboxes.state("run-run-1"), "ACTIVE")

    def test_child_context_requires_isolated_owned_files(self):
        child = make_child_context(
            parent_run_id="run-1",
            child_id="child-1",
            role="execution",
            mission="implement bounded slice",
            owned_files=["lib/a.py", "tests/test_a.py"],
            worker_id="worker-2",
            provider_id="provider-a",
            sandbox_id="child-sandbox",
        )
        self.assertEqual(child["authority_effect"], "none")
        self.assertEqual(child["owned_files"], ["lib/a.py", "tests/test_a.py"])
        with self.assertRaises(HarnessError):
            make_child_context(
                parent_run_id="run-1",
                child_id="child-bad",
                role="execution",
                mission="escape",
                owned_files=["../secret"],
                worker_id="worker-2",
                provider_id="provider-a",
                sandbox_id="child-sandbox-2",
            )

    def test_spawn_child_gets_distinct_active_sandbox(self):
        child = self.harness.spawn_child(
            parent_run_id="run-1",
            child_id="child-2",
            role="discovery",
            mission="inspect evidence",
            owned_files=["docs/evidence.md"],
            worker_id="worker-2",
            provider_id="provider-b",
        )
        self.assertNotEqual(child["sandbox_id"], "run-run-1")
        self.assertEqual(self.sandboxes.state(child["sandbox_id"]), "ACTIVE")
        self.assertEqual(child["authority_effect"], "none")

    def test_sandbox_lifecycle_seals_before_release(self):
        path = self.sandboxes.root / "run-run-1"
        (path / "proof.txt").write_text("evidence", encoding="utf-8")
        sealed = self.sandboxes.seal("run-run-1")
        self.assertEqual(len(sealed), 64)
        restarted = SandboxLifecycle(self.sandboxes.root)
        self.assertEqual(restarted.state("run-run-1"), "SEALED")
        returned = restarted.release("run-run-1")
        self.assertEqual(returned, sealed)
        self.assertFalse(path.exists())
        self.assertEqual(restarted.state("run-run-1"), "RELEASED")
        with self.assertRaises(InvalidTransition):
            restarted.release("run-run-1")

    def test_judge_is_evidence_only_and_cannot_self_attest(self):
        evidence = judge_evidence(
            run_id="run-1",
            worker_id="worker-1",
            worker_provider_id="provider-a",
            judge_id="judge-1",
            judge_provider_id="provider-b",
            findings=[{"severity": "P1", "claim": "missing test"}],
            evidence_refs=["ci:123"],
        )
        self.assertTrue(evidence["provider_independent"])
        self.assertEqual(evidence["authority_effect"], "none")
        with self.assertRaises(HarnessError):
            judge_evidence(
                run_id="run-1",
                worker_id="worker-1",
                worker_provider_id="provider-a",
                judge_id="worker-1",
                judge_provider_id="provider-a",
                findings=[],
                evidence_refs=[],
            )

    def test_judge_fork_is_non_blocking_evidence_path(self):
        fork = JudgeFork(lambda subject: [{"claim": subject["claim"], "severity": "P2"}])
        try:
            future = fork.submit(
                run_id="run-1",
                worker_id="worker-1",
                worker_provider_id="provider-a",
                judge_id="judge-2",
                judge_provider_id="provider-b",
                subject={"claim": "review me"},
                evidence_refs=["receipt:1"],
            )
            evidence = future.result(timeout=2)
            self.assertEqual(evidence["authority_effect"], "none")
            self.assertTrue(evidence["provider_independent"])
        finally:
            fork.close()

    def test_compaction_bounds_context_and_preserves_evidence(self):
        events = [
            {"id": f"e{i}", "text": f"event {i}", "evidence_refs": [f"ref:{i}"]}
            for i in range(6)
        ]
        compacted = compact_context(events, max_items=3)
        self.assertEqual(len(compacted), 3)
        self.assertEqual(compacted[0]["kind"], "context_compaction")
        self.assertEqual(compacted[0]["compacted_count"], 4)
        self.assertEqual(compacted[0]["evidence_refs"], [f"ref:{i}" for i in range(4)])
        self.assertEqual(len(compacted[0]["source_digests"]), 4)
        self.assertEqual(compacted[0]["authority_effect"], "none")
        self.assertEqual([e["id"] for e in compacted[1:]], ["e4", "e5"])

    def test_side_effect_fails_closed_without_authorizer(self):
        gate = SideEffectGate(self.store, None)
        with self.assertRaises(AuthorizationDenied):
            gate.execute(
                run_id="run-1",
                action_id="push-1",
                action_type="git.push",
                payload={"branch": "x"},
                executor=lambda payload: "pushed",
            )

    def test_side_effect_rejects_unknown_run_before_authorization_or_execution(self):
        authorized = []
        executed = []

        def authorizer(request):
            authorized.append(request)
            return self.authorization(request)

        gate = SideEffectGate(self.store, authorizer)
        with self.assertRaises(HarnessError):
            gate.execute(
                run_id="not-registered",
                action_id="push-unknown",
                action_type="git.push",
                payload={"branch": "x"},
                executor=lambda payload: executed.append(payload),
            )
        self.assertEqual(authorized, [])
        self.assertEqual(executed, [])

    def test_side_effect_requires_authorization_bound_to_exact_action(self):
        def wrong(request):
            auth = self.authorization(request)
            auth["action_digest"] = "0" * 64
            return auth

        gate = SideEffectGate(self.store, wrong)
        with self.assertRaises(AuthorizationDenied):
            gate.execute(
                run_id="run-1",
                action_id="push-1",
                action_type="git.push",
                payload={"branch": "x"},
                executor=lambda payload: "pushed",
            )

    def test_each_governance_artifact_is_bound_to_exact_action(self):
        def wrong_reht(request):
            auth = self.authorization(request)
            auth["reht"]["action_digest"] = "0" * 64
            return auth

        gate = SideEffectGate(self.store, wrong_reht)
        with self.assertRaises(AuthorizationDenied):
            gate.execute(
                run_id="run-1",
                action_id="push-bound",
                action_type="git.push",
                payload={"branch": "x"},
                executor=lambda payload: "pushed",
            )

    def test_non_allow_racs_never_executes(self):
        calls = []

        def deny(request):
            auth = self.authorization(request)
            auth["racs"]["decision"] = "STEP_UP"
            return auth

        gate = SideEffectGate(self.store, deny)
        with self.assertRaises(AuthorizationDenied):
            gate.execute(
                run_id="run-1",
                action_id="deploy-1",
                action_type="deploy",
                payload={"target": "prod"},
                executor=lambda payload: calls.append(payload),
            )
        self.assertEqual(calls, [])

    def test_completed_side_effect_is_not_replayed_on_resume(self):
        calls = []
        gate = SideEffectGate(self.store, self.authorization)
        first = gate.execute(
            run_id="run-1",
            action_id="push-1",
            action_type="git.push",
            payload={"branch": "x"},
            executor=lambda payload: calls.append(payload) or {"ok": True},
        )
        second = gate.execute(
            run_id="run-1",
            action_id="push-1",
            action_type="git.push",
            payload={"branch": "x"},
            executor=lambda payload: calls.append(payload) or {"ok": True},
        )
        self.assertTrue(first["executed"])
        self.assertFalse(second["executed"])
        self.assertEqual(len(calls), 1)

    def test_prepared_action_blocks_ambiguous_replay(self):
        action = {
            "run_id": "run-1",
            "action_id": "push-2",
            "action_type": "git.push",
            "payload": {"branch": "y"},
        }
        self.store.prepare_action("run-1", "push-2", digest(action))
        gate = SideEffectGate(self.store, self.authorization)
        with self.assertRaises(AmbiguousSideEffect):
            gate.execute(
                run_id="run-1",
                action_id="push-2",
                action_type="git.push",
                payload={"branch": "y"},
                executor=lambda payload: {"ok": True},
            )


if __name__ == "__main__":
    unittest.main()
