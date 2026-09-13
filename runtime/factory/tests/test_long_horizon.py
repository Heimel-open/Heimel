"""Tests for long-horizon harness patterns (#52)."""

import unittest

from lib.long_horizon import (
    CheckpointRef,
    JudgeForkReview,
    LongHorizonHarness,
    MemoryChunk,
)


class LongHorizonHarnessTest(unittest.TestCase):
    def test_checkpoint_and_resume(self):
        h = LongHorizonHarness()
        cp = h.checkpoint("run-1", step=3, state={"progress": 0.6})
        assert isinstance(cp, CheckpointRef)
        resumed = h.resume_from("run-1", 3)
        assert resumed is not None
        assert resumed.checkpoint_id == cp.checkpoint_id
        assert resumed.step == 3

    def test_checkpoint_digest_deterministic(self):
        h1 = LongHorizonHarness()
        h2 = LongHorizonHarness()
        a = h1.checkpoint("r", 1, {"x": 1})
        b = h2.checkpoint("r", 1, {"x": 1})
        assert a.state_digest == b.state_digest

    def test_spawn_child_isolated(self):
        h = LongHorizonHarness()
        child = h.spawn_child("parent-1", "analysis", "ws-a")
        assert child.parent_id == "parent-1"
        assert child.workspace_ref == "ws-a"
        assert h.child(child.context_id) is child

    def test_memory_compaction_versioned(self):
        h = LongHorizonHarness()
        c1 = h.compact_memory("scope-1", "digest-a")
        c2 = h.compact_memory("scope-1", "digest-b")
        assert isinstance(c1, MemoryChunk)
        assert c2.version == 2
        assert c2.supersedes == c1.chunk_id
        assert len(h.memory_for("scope-1")) == 2

    def test_sandbox_lifecycle(self):
        h = LongHorizonHarness()
        sb = h.create_sandbox("ws-a")
        assert sb.state == "created"
        h.transition_sandbox(sb.sandbox_id, "active")
        h.transition_sandbox(sb.sandbox_id, "sealed")
        h.transition_sandbox(sb.sandbox_id, "reaped")
        assert sb.reaped_at is not None

    def test_sandbox_illegal_transition(self):
        h = LongHorizonHarness()
        sb = h.create_sandbox("ws-a")
        with self.assertRaises(ValueError):
            h.transition_sandbox(sb.sandbox_id, "reaped")

    def test_judge_fork_review(self):
        h = LongHorizonHarness()
        h.record_review(JudgeForkReview("rev-1", "cand-1", "judge-a", "pass",
                                        ("ev-1",)))
        reviews = h.reviews_for("cand-1")
        assert len(reviews) == 1
        assert reviews[0].verdict == "pass"

    def test_never_grants_authority(self):
        h = LongHorizonHarness()
        assert h.has_authority_surface is False
        assert not hasattr(h, "clear")
        assert not hasattr(h, "permit")
        assert not hasattr(h, "authorize")
        assert not hasattr(h, "execute")

    def test_no_adk_runtime_dependency(self):
        # Pure stdlib: no external runtime import.
        import lib.long_horizon as m

        source = open(m.__file__).read()
        assert "adk" not in source.lower().replace("adk", "ADK")


if __name__ == "__main__":
    unittest.main()
