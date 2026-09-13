import unittest

from lib.jcode_swarm_runtime import (
    ForbiddenDelegatedCapabilityError,
    OwnedFileScopeError,
    ParallelFileCollisionError,
    bind_persistent_memory,
    find_file_collisions,
    plan_child_delegation,
    plan_coordination_message,
    validate_parallel_delegations,
)


PARENT_SCOPE = (
    "lib/alpha.py",
    "lib/beta.py",
    "tests/test_alpha.py",
    "tests/test_beta.py",
)


class JcodeSwarmRuntimeTests(unittest.TestCase):
    def test_child_delegation_is_bounded_and_non_authoritative(self):
        child = plan_child_delegation(
            "coordinator-1",
            "worker-alpha",
            "Implement alpha path and its tests.",
            parent_owned_files=PARENT_SCOPE,
            child_owned_files=("lib/alpha.py", "tests/test_alpha.py"),
            delegated_capabilities=("repo.read", "repo.write", "test.run"),
        )
        self.assertEqual(child.parent_worker_id, "coordinator-1")
        self.assertEqual(child.child_worker_id, "worker-alpha")
        self.assertEqual(child.authority_effect, "none")
        self.assertFalse(child.inherits_parent_authority)
        self.assertTrue(child.requires_fresh_reht_clearance)
        self.assertFalse(child.self_development_allowed)
        self.assertEqual(
            child.owned_files,
            ("lib/alpha.py", "tests/test_alpha.py"),
        )

    def test_child_cannot_expand_parent_owned_file_scope(self):
        with self.assertRaises(OwnedFileScopeError):
            plan_child_delegation(
                "coordinator-1",
                "worker-alpha",
                "Touch an unclaimed governance file.",
                parent_owned_files=PARENT_SCOPE,
                child_owned_files=("lib/alpha.py", "lib/unclaimed.py"),
            )

    def test_child_cannot_receive_authority_or_promotion_capability(self):
        for capability in (
            "reht.authorize",
            "authority.delegate",
            "merge",
            "deploy.production",
            "governance.modify",
            "external.execute",
        ):
            with self.subTest(capability=capability):
                with self.assertRaises(ForbiddenDelegatedCapabilityError):
                    plan_child_delegation(
                        "coordinator-1",
                        "worker-alpha",
                        "Attempt forbidden delegation.",
                        parent_owned_files=PARENT_SCOPE,
                        child_owned_files=("lib/alpha.py",),
                        delegated_capabilities=(capability,),
                    )

    def test_parallel_workers_with_disjoint_files_are_valid(self):
        alpha = plan_child_delegation(
            "coordinator-1",
            "worker-alpha",
            "Implement alpha.",
            parent_owned_files=PARENT_SCOPE,
            child_owned_files=("lib/alpha.py", "tests/test_alpha.py"),
        )
        beta = plan_child_delegation(
            "coordinator-1",
            "worker-beta",
            "Implement beta.",
            parent_owned_files=PARENT_SCOPE,
            child_owned_files=("lib/beta.py", "tests/test_beta.py"),
        )
        self.assertEqual(find_file_collisions((alpha, beta)), {})
        self.assertEqual(validate_parallel_delegations((alpha, beta)), (alpha, beta))

    def test_parallel_file_collision_fails_closed(self):
        alpha = plan_child_delegation(
            "coordinator-1",
            "worker-alpha",
            "Implement alpha.",
            parent_owned_files=PARENT_SCOPE,
            child_owned_files=("lib/alpha.py", "tests/test_alpha.py"),
        )
        beta = plan_child_delegation(
            "coordinator-1",
            "worker-beta",
            "Refactor shared alpha code.",
            parent_owned_files=PARENT_SCOPE,
            child_owned_files=("lib/alpha.py", "lib/beta.py"),
        )
        self.assertEqual(
            find_file_collisions((alpha, beta)),
            {"lib/alpha.py": ("worker-alpha", "worker-beta")},
        )
        with self.assertRaises(ParallelFileCollisionError):
            validate_parallel_delegations((alpha, beta))

    def test_direct_and_broadcast_messages_are_coordination_only(self):
        direct = plan_coordination_message(
            "worker-alpha",
            "beta.py changed under your branch",
            recipient_refs=("worker-beta",),
            mode="direct",
            message_type="file_change_notice",
        )
        broadcast = plan_coordination_message(
            "coordinator-1",
            "pause writes until collision is resolved",
            mode="broadcast",
            message_type="coordination",
        )
        self.assertEqual(direct.authority_effect, "none")
        self.assertFalse(direct.creates_mandate)
        self.assertNotIn("beta.py changed", direct.as_dict().values())
        self.assertEqual(broadcast.recipient_refs, ("*",))
        self.assertEqual(broadcast.authority_effect, "none")

    def test_persistent_memory_requires_provenance_and_freshness_and_cannot_authorize(self):
        memory = bind_persistent_memory(
            "repo-patterns",
            "The adapter uses fail-closed read-only semantics.",
            provenance_ref="commit:f763de5",
            freshness_ref="base_sha:f763de5",
        )
        self.assertEqual(memory.status, "context_only")
        self.assertEqual(memory.authority_effect, "none")
        self.assertFalse(memory.can_authorize)
        self.assertEqual(memory.provenance_ref, "commit:f763de5")
        self.assertEqual(memory.freshness_ref, "base_sha:f763de5")
        self.assertNotIn("fail-closed", memory.as_dict().values())


if __name__ == "__main__":
    unittest.main()
