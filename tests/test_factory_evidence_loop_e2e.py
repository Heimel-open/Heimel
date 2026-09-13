import unittest

from lib.factory_evidence_loop import (
    FactoryEvidenceLoop,
    NEEDS_HUMAN,
    NORMAL,
    PASS,
    REQUIRED_REVIEW_TYPES,
    SCHEMA_VERSION,
)

REPO = "nsolland/valo-factory"
RUN = "run-e2e-2026-08-08"
BASE = "0f7cb61755df2b33cbf81ec68f70e35268da4bd7"
CANDIDATE = "c0ffee0000000000000000000000000000000001"
HEAD = BASE  # current head equals the exact base -> no target drift


class FactoryEvidenceLoopE2ETest(unittest.TestCase):

    def test_full_loop_observation_to_post_merge(self):
        loop = FactoryEvidenceLoop()

        # ---- 1. Observation (append-only evidence) -------------------------
        obs = loop.observe(
            repository=REPO, run_id=RUN, base_sha=BASE,
            actor="observer-oracle", summary="governed evidence loop needed",
            evidence="nsolland/Index#611")
        self.assertEqual(loop.projection.work_items, {})
        self.assertEqual(loop.projection.execution_queue(), [])
        self.assertEqual(loop.projection.human_queue(), [])

        # ---- 2. Shaping (separated layers + authority envelope) ------------
        shaped = loop.shape(
            repository=REPO, run_id=RUN, base_sha=BASE, actor="shaper-oracle",
            source_observation_id=obs.observation_id,
            objective="governed evidence loop vertical slice",
            acceptance_criteria=["loop lands only with evidence",
                                 "no self-attestation"],
            behavior_rules=["append-only observations",
                            "separate queues for human and executable"],
            approach="event-sourced evidence loop",
            steps=["build contract", "build runtime", "test"],
            authority_basis="founder-order#40",
            authority_scope=["lib/factory_evidence_loop.py"],
            expires_at="2099-01-01T00:00:00+00:00",
            work_item_id="wi-e2e")
        self.assertEqual(shaped.work_item.status, "SHAPED")
        artifacts = [shaped.brief, shaped.behavior, shaped.approach,
                     shaped.plan, shaped.authority]
        self.assertEqual(len(artifacts), 5)
        for artifact in artifacts:
            self.assertEqual(artifact.schema_version, SCHEMA_VERSION)
            self.assertEqual(artifact.repository, REPO)
            self.assertEqual(artifact.base_sha, BASE)

        # ---- 3. Immutable authorized Work Item -----------------------------
        authorized = loop.authorize_work_item(
            work_item_id="wi-e2e", actor="shaper-oracle")
        self.assertEqual(authorized.status, "AUTHORIZED")
        self.assertEqual(loop.projection.execution_queue(), ["wi-e2e"])

        # ---- 4. Isolated Attempt on exact base SHA -------------------------
        attempt = loop.start_attempt(
            work_item_id="wi-e2e", actor="writer-agent",
            worktree_id="wt-e2e-7f3a", base_sha=BASE,
            authority_envelope_id="wi-e2e-auth", attempt_id="att-e2e")
        self.assertEqual(attempt.actor, "writer-agent")
        self.assertEqual(attempt.base_sha, BASE)
        self.assertEqual(attempt.worktree_id, "wt-e2e-7f3a")

        # ---- 5. Writer candidate (no self-attestation) ---------------------
        loop.submit_candidate(attempt_id="att-e2e", actor="writer-agent",
                              candidate_sha=CANDIDATE)
        self.assertEqual(
            loop.projection.attempts["att-e2e"]["candidate_sha"], CANDIDATE)
        with self.assertRaises(Exception):
            loop.record_tester_evidence(
                attempt_id="att-e2e", actor="writer-agent",
                candidate_sha=CANDIDATE, command="cmd",
                working_directory="/wt", exit_code=0,
                started_at="2026-08-08T09:00:00+00:00",
                ended_at="2026-08-08T09:00:05+00:00")

        # ---- 6. Deterministic Tester evidence bound to candidate SHA -------
        evidence = loop.record_tester_evidence(
            attempt_id="att-e2e", actor="tester-agent",
            candidate_sha=CANDIDATE,
            command="python3 -m unittest discover -s tests",
            working_directory="/tmp/valo-runs/wt-e2e-7f3a", exit_code=0,
            started_at="2026-08-08T09:00:00+00:00",
            ended_at="2026-08-08T09:00:05+00:00",
            env_profile_digest="d" * 64, stdout_digest="e" * 64,
            stderr_digest="f" * 64, test_counts=91, test_failures=0,
            evidence_id="te-e2e")
        self.assertEqual(evidence.candidate_sha, CANDIDATE)
        self.assertEqual(evidence.actor, "tester-agent")

        # ---- 7. Independent parallel Reviewers (after evidence only) ------
        reports = []
        for review_type in REQUIRED_REVIEW_TYPES:
            reports.append(loop.review(
                attempt_id="att-e2e", actor=f"reviewer-{review_type}",
                review_type=review_type, result=PASS,
                report_id=f"rr-e2e-{review_type}"))
        self.assertEqual(len(reports), len(REQUIRED_REVIEW_TYPES))
        self.assertEqual({r.actor for r in reports},
                         {f"reviewer-{t}" for t in REQUIRED_REVIEW_TYPES})
        for report in reports:
            self.assertEqual(report.candidate_sha, CANDIDATE)
            self.assertEqual(report.result, PASS)

        resolution = loop.resolve_review(attempt_id="att-e2e",
                                         actor="orchestrator")
        self.assertEqual(resolution.result, PASS)

        # ---- 8. Learner handoff (proposals only) ---------------------------
        handoff = loop.run_learner(
            attempt_id="att-e2e", actor="learner-agent",
            proposals=[{"kind": "expertise",
                        "summary": "evidence loops bind exact SHAs"}],
            handoff_id="lh-e2e")
        self.assertEqual(handoff.candidate_sha, CANDIDATE)
        self.assertEqual(handoff.proposals[0]["kind"], "expertise")

        # ---- 9. Immutable Merge Candidate binds every evidence digest ------
        candidate = loop.create_merge_candidate(attempt_id="att-e2e",
                                                actor="orchestrator",
                                                candidate_id="mc-e2e")
        self.assertEqual(candidate.status, "PENDING")
        self.assertEqual(candidate.candidate_sha, CANDIDATE)
        self.assertEqual(candidate.base_sha, BASE)
        self.assertEqual(candidate.evidence_digests,
                         (evidence.content_digest,))
        self.assertEqual(candidate.learner_digest, handoff.content_digest)
        # Immutable: the contract object cannot be mutated in place.
        from dataclasses import FrozenInstanceError
        with self.assertRaises(FrozenInstanceError):
            candidate.status = "LANDED"

        # ---- 10. Governed landing rechecks every gate ----------------------
        self.assertFalse(loop.land(
            candidate_id="mc-e2e", actor="orchestrator",
            current_head_sha=BASE, mode=NORMAL, ci_evidence="",
            reht_clearance="reht-current", racs_decision="racs-approve"
        ).landed, "landing without CI evidence must fail")
        self.assertFalse(loop.land(
            candidate_id="mc-e2e", actor="orchestrator",
            current_head_sha=BASE, mode=NORMAL, ci_evidence="ci ok",
            reht_clearance="", racs_decision="racs-approve"
        ).landed, "landing without REHT clearance must fail")
        self.assertFalse(loop.land(
            candidate_id="mc-e2e", actor="orchestrator",
            current_head_sha=BASE, mode="MAINTENANCE", ci_evidence="ci ok",
            reht_clearance="reht-current", racs_decision="racs-approve"
        ).landed, "landing outside NORMAL mode must fail")
        landing = loop.land(
            candidate_id="mc-e2e", actor="orchestrator",
            current_head_sha=HEAD, mode=NORMAL, claim_active=True,
            ci_evidence="ci ok", reht_clearance="reht-current",
            racs_decision="racs-approve")
        self.assertTrue(landing.landed)
        self.assertTrue(landing.checks["mode_normal"])
        self.assertTrue(landing.checks["ci_evidence"])
        self.assertTrue(landing.checks["reht_clearance"])
        self.assertTrue(landing.checks["racs_decision"])
        self.assertTrue(landing.checks["no_target_drift"])

        # ---- 11. Post-merge Observation (never silently triggers work) -----
        post = loop.post_merge_observe(
            repository=REPO, run_id=RUN, base_sha=BASE,
            candidate_sha=CANDIDATE, actor="observer-oracle",
            summary="production feed shows stable behavior",
            observation_id="pmo-e2e")
        self.assertEqual(post.candidate_sha, CANDIDATE)
        # Only an observation was added; no new work was started.
        self.assertEqual(len(loop.projection.work_items), 1)
        self.assertEqual(len(loop.projection.attempts), 1)
        self.assertEqual(len(loop.projection.merge_candidates), 1)
        self.assertEqual(len(loop.projection.landings), 4)

        # ---- 12. Exact SHA lineage -----------------------------------------
        self.assertEqual(BASE, shaped.work_item.base_sha)
        self.assertEqual(BASE, attempt.base_sha)
        self.assertEqual(CANDIDATE, evidence.candidate_sha)
        self.assertEqual(CANDIDATE, handoff.candidate_sha)
        self.assertEqual(CANDIDATE, candidate.candidate_sha)

        # ---- 13. Separate identities, no self-attestation ------------------
        identities = {
            attempt.actor,
            evidence.actor,
            *{r.actor for r in reports},
            handoff.actor,
        }
        self.assertEqual(len(identities), 8)
        self.assertNotEqual(attempt.actor, evidence.actor)

        # ---- 14. Receipt chain for every transition ------------------------
        chain = loop.receipt_chain()
        self.assertEqual(len(chain), len(loop.events()))
        previous = None
        for receipt in chain:
            if previous is not None:
                self.assertEqual(receipt["previous_hash"], previous)
            previous = receipt["event_hash"]
        # First event has no predecessor; every later event links back.
        self.assertIsNone(chain[0]["previous_hash"])
        for receipt in chain[1:]:
            self.assertIsNotNone(receipt["previous_hash"])

        # ---- 15. No human-queue drift --------------------------------------
        self.assertEqual(loop.projection.work_items["wi-e2e"]["status"],
                         "LANDED")
        self.assertEqual(loop.projection.human_queue(), [])
        self.assertEqual(loop.projection.attempts["att-e2e"]["status"],
                         "LANDED")


if __name__ == "__main__":
    unittest.main()
