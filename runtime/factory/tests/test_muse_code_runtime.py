import json
import tempfile
import unittest
from pathlib import Path

from lib.harness_provider_adapters import (
    UnsupportedHarnessModeError,
    harness_ids,
    plan_harness_execution,
)
from lib.muse_code_runtime import (
    EventChainError,
    GoalDriftError,
    MuseRuntimeStore,
    SpecialistIdentityError,
)


ROOT = Path(__file__).parent.parent


class MuseCodeRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "muse-runtime.db"
        self.store = MuseRuntimeStore(self.db_path)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_goal_is_bound_and_silent_goal_drift_fails_closed(self):
        goal = self.store.bind_goal(
            "run-84",
            "Implement bounded long-horizon runtime improvements",
            ("tests green", "authority boundary unchanged"),
            goal_id="goal-84",
        )
        same = self.store.bind_goal(
            "run-84",
            "Implement bounded long-horizon runtime improvements",
            ("tests green", "authority boundary unchanged"),
        )
        self.assertEqual(goal, same)
        with self.assertRaises(GoalDriftError):
            self.store.bind_goal(
                "run-84",
                "Replace the objective silently",
                ("tests green",),
            )

    def test_persistent_specialist_is_reused_instead_of_respawned(self):
        first = self.store.ensure_specialist(
            "run-84",
            "repo-research",
            "meta_muse_spark_1_2",
            "worktree://run-84/research",
            specialist_id="specialist-research",
        )
        second = self.store.ensure_specialist(
            "run-84",
            "repo-research",
            "meta_muse_spark_1_2",
            "worktree://run-84/research",
        )
        self.assertEqual(first.specialist_id, second.specialist_id)
        starts = [
            event
            for event in self.store.events("run-84")
            if event.event_type == "specialist.started"
        ]
        self.assertEqual(len(starts), 1)

        with self.assertRaises(SpecialistIdentityError):
            self.store.ensure_specialist(
                "run-84",
                "repo-research",
                "openai_codex",
                "worktree://run-84/research",
            )

    def test_event_log_is_hash_chained_and_restart_safe(self):
        self.store.bind_goal("run-84", "Finish mission", ("verified",))
        self.store.append_event(
            "run-84",
            "model.call",
            actor_id="worker-main",
            payload={"model_id": "muse-spark-1.2", "prompt_digest": "sha256:p"},
        )
        self.store.append_event(
            "run-84",
            "tool.run",
            actor_id="worker-main",
            payload={"tool": "tests", "result_digest": "sha256:r"},
        )
        self.store.append_event(
            "run-84",
            "approval",
            actor_id="human",
            payload={"approval_ref": "approval-1"},
        )
        self.store.append_event(
            "run-84",
            "edit",
            actor_id="worker-main",
            payload={"path": "lib/x.py", "content_digest": "sha256:c"},
        )
        self.assertTrue(self.store.verify_chain("run-84"))
        before = self.store.events("run-84")
        last_hash = before[-1].event_hash
        self.store.close()

        reopened = MuseRuntimeStore(self.db_path)
        try:
            after = reopened.events("run-84")
            recovered = reopened.recover("run-84")
            self.assertEqual(before, after)
            self.assertEqual(recovered["last_event_hash"], last_hash)
            self.assertTrue(recovered["chain_valid"])
            self.assertEqual(recovered["authority_effect"], "none")
        finally:
            reopened.close()
        self.store = MuseRuntimeStore(self.db_path)

    def test_context_compaction_preserves_source_provenance(self):
        self.store.bind_goal("run-84", "Finish mission", ("verified",))
        event = self.store.append_event(
            "run-84",
            "tool.run",
            actor_id="worker-main",
            payload={"tool": "repo.read", "result_digest": "sha256:r"},
        )
        compaction = self.store.compact_context(
            "run-84",
            through_seq=event.seq,
            summary="Goal is fixed; repository inspection completed.",
        )
        self.assertEqual(compaction.source_chain_hash, event.event_hash)
        self.assertNotEqual(compaction.compacted_digest, compaction.source_chain_hash)
        self.store.append_event(
            "run-84",
            "edit",
            actor_id="worker-main",
            payload={"path": "lib/muse_code_runtime.py"},
        )
        recovered = self.store.recover("run-84")
        self.assertEqual(recovered["latest_compaction"], compaction)
        self.assertGreaterEqual(len(recovered["events_after_compaction"]), 2)
        self.assertTrue(self.store.verify_chain("run-84"))

    def test_tampering_breaks_replay_integrity(self):
        self.store.bind_goal("run-84", "Finish mission", ("verified",))
        self.store.append_event(
            "run-84",
            "edit",
            actor_id="worker-main",
            payload={"path": "lib/x.py"},
        )
        with self.store.conn:
            self.store.conn.execute(
                "UPDATE events SET payload_json=? WHERE run_id=? AND seq=?",
                (json.dumps({"path": "tampered.py"}), "run-84", 2),
            )
        self.assertFalse(self.store.verify_chain("run-84"))
        with self.assertRaises(EventChainError):
            self.store.recover("run-84")

    def test_runtime_state_never_grants_authority(self):
        self.assertFalse(self.store.has_authority_surface)
        goal = self.store.bind_goal("run-84", "Finish mission", ("verified",))
        specialist = self.store.ensure_specialist(
            "run-84",
            "review",
            "meta_muse_spark_1_2",
            "worktree://run-84/review",
        )
        event = self.store.append_event(
            "run-84",
            "approval",
            actor_id="human",
            payload={"approval_ref": "human-review"},
        )
        self.assertEqual(goal.authority_effect, "none")
        self.assertEqual(specialist.authority_effect, "none")
        self.assertEqual(event.authority_effect, "none")

    def test_muse_code_identity_is_registered_but_execution_fails_closed(self):
        self.assertIn("muse_code", harness_ids())
        registry = json.loads(
            (ROOT / "config" / "harness-providers.json").read_text(encoding="utf-8")
        )
        providers = {item["harness_id"]: item for item in registry["providers"]}
        muse = providers["muse_code"]
        self.assertEqual(muse["authority_effect"], "none")
        self.assertFalse(muse["self_development_allowed"])
        self.assertEqual(muse["status"], "observed_optional_fail_closed")
        self.assertIn("persistent_specialist_pool", muse["adopted_patterns"])
        with self.assertRaises(UnsupportedHarnessModeError):
            plan_harness_execution(
                "muse_code",
                "openai_codex",
                "implement bounded change",
                execution_mode="workspace_write",
            )


if __name__ == "__main__":
    unittest.main()
