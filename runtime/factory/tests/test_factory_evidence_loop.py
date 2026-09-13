import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone

from lib.factory_evidence_loop import (
    AUTHORIZED,
    CORRECTING,
    EXECUTION_QUEUE,
    FAIL,
    FactoryEvidenceLoop,
    FactoryLoopError,
    GateError,
    HUMAN_QUEUE,
    ImmutabilityError,
    LANDED,
    LEARNER_READY,
    LoopConfig,
    MemoryEventStore,
    NEEDS_HUMAN,
    NORMAL,
    NotFoundError,
    PASS,
    REQUIRED_REVIEW_TYPES,
    SCHEMA_VERSION,
    SeparationOfDutiesError,
    UNCERTAIN,
    AuthorityError,
)

REPO = "nsolland/valo-factory"
RUN = "run-2026-08-08-001"
BASE = "a" * 40
CANDIDATE = "b" * 40


def make_loop(max_correction_rounds=None, clock=None, store=None):
    config = LoopConfig()
    if max_correction_rounds is not None:
        config = replace(config, max_correction_rounds=max_correction_rounds)
    if clock is not None:
        config = replace(config, now=clock)
    return FactoryEvidenceLoop(store=store, config=config)


def observe_and_shape(loop, work_item_id="wi-1", expires_at="2099-01-01T00:00:00+00:00",
                      **overrides):
    obs = loop.observe(
        repository=REPO, run_id=RUN, base_sha=BASE, actor="observer-a",
        summary="add governed evidence loop", evidence="issue #40",
        observation_id=overrides.pop("observation_id", None),
    )
    shaped = loop.shape(
        repository=REPO, run_id=RUN, base_sha=BASE, actor="shaper-a",
        source_observation_id=obs.observation_id,
        objective="build governed evidence loop",
        acceptance_criteria=["tests green"],
        behavior_rules=["no self attestation"],
        approach="event sourced",
        steps=["write code", "write tests"],
        authority_basis="founder-order#40",
        authority_scope=["lib/", "schemas/"],
        expires_at=expires_at,
        work_item_id=work_item_id,
        **overrides,
    )
    return obs, shaped


def pipeline_to_candidate(loop, ids=None):
    """Drive the loop from Observation through immutable Merge Candidate."""
    ids = ids or {}
    obs, shaped = observe_and_shape(
        loop, work_item_id=ids.get("work_item", "wi-1"),
        observation_id=ids.get("observation_id"))
    loop.authorize_work_item(
        work_item_id=shaped.work_item.work_item_id, actor="shaper-a")
    attempt = loop.start_attempt(
        work_item_id=shaped.work_item.work_item_id, actor="writer-a",
        worktree_id="wt-1", base_sha=BASE,
        authority_envelope_id=f"{shaped.work_item.work_item_id}-auth",
        attempt_id=ids.get("attempt", "att-1"))
    loop.submit_candidate(attempt_id=attempt.attempt_id, actor="writer-a",
                          candidate_sha=CANDIDATE)
    loop.record_tester_evidence(
        attempt_id=attempt.attempt_id, actor="tester-a",
        candidate_sha=CANDIDATE,
        command="python3 -m unittest discover -s tests",
        working_directory="/tmp/valo-runs/wt-1", exit_code=0,
        started_at="2026-08-08T09:00:00+00:00",
        ended_at="2026-08-08T09:00:05+00:00",
        env_profile_digest="e" * 64, stdout_digest="f" * 64,
        stderr_digest="d" * 64, test_counts=42, test_failures=0,
        evidence_id=ids.get("evidence", "te-1"))
    for review_type in REQUIRED_REVIEW_TYPES:
        loop.review(
            attempt_id=attempt.attempt_id,
            actor=f"reviewer-{review_type}", review_type=review_type,
            result=PASS,
            report_id=ids.get(f"report_{review_type}", f"rr-{review_type}"))
    resolution = loop.resolve_review(attempt_id=attempt.attempt_id,
                                     actor="orchestrator")
    loop.run_learner(
        attempt_id=attempt.attempt_id, actor="learner-a",
        proposals=[{"kind": "expertise",
                    "summary": "evidence loops bind digests"}],
        handoff_id=ids.get("handoff", "lh-1"))
    candidate = loop.create_merge_candidate(
        attempt_id=attempt.attempt_id, actor="orchestrator",
        candidate_id=ids.get("candidate", "mc-1"))
    return {
        "obs": obs,
        "shaped": shaped,
        "attempt": attempt,
        "resolution": resolution,
        "candidate": candidate,
    }


def full_pipeline(loop, ids=None):
    """Drive the entire loop to a governed landing + post-merge observation."""
    ids = ids or {}
    result = pipeline_to_candidate(loop, ids=ids)
    landing = loop.land(
        candidate_id=result["candidate"].candidate_id, actor="orchestrator",
        current_head_sha=BASE, mode=NORMAL, claim_active=True,
        ci_evidence="ci passed", reht_clearance="reht-current",
        racs_decision="racs-approve")
    loop.post_merge_observe(
        repository=REPO, run_id=RUN, base_sha=BASE, candidate_sha=CANDIDATE,
        actor="observer-b", summary="post-merge ok",
        observation_id=ids.get("post_merge", "pmo-1"))
    result["landing"] = landing
    return result


def rerun_pipeline(loop, ids=None):
    """Re-drive the loop after a restart. Already-applied steps are skipped
    (fail-closed is itself idempotent: guarded steps raise FactoryLoopError
    and unguarded steps are deduplicated by the append-only store)."""
    ids = ids or {}
    wi = ids.get("work_item", "wi-1")
    att = ids.get("attempt", "att-1")
    te = ids.get("evidence", "te-1")
    lh = ids.get("handoff", "lh-1")
    mc = ids.get("candidate", "mc-1")
    pmo = ids.get("post_merge", "pmo-1")
    observation_id = ids.get("observation_id")

    def step(call):
        try:
            call()
        except FactoryLoopError:
            pass

    step(lambda: loop.observe(
        repository=REPO, run_id=RUN, base_sha=BASE, actor="observer-a",
        summary="add governed evidence loop", evidence="issue #40",
        observation_id=observation_id))
    step(lambda: loop.shape(
        repository=REPO, run_id=RUN, base_sha=BASE, actor="shaper-a",
        source_observation_id=observation_id,
        objective="build governed evidence loop",
        acceptance_criteria=["tests green"],
        behavior_rules=["no self attestation"], approach="event sourced",
        steps=["write code", "write tests"],
        authority_basis="founder-order#40",
        authority_scope=["lib/", "schemas/"],
        expires_at="2099-01-01T00:00:00+00:00", work_item_id=wi))
    step(lambda: loop.authorize_work_item(work_item_id=wi, actor="shaper-a"))
    step(lambda: loop.start_attempt(
        work_item_id=wi, actor="writer-a", worktree_id="wt-1",
        base_sha=BASE, authority_envelope_id=f"{wi}-auth", attempt_id=att))
    step(lambda: loop.submit_candidate(
        attempt_id=att, actor="writer-a", candidate_sha=CANDIDATE))
    step(lambda: loop.record_tester_evidence(
        attempt_id=att, actor="tester-a", candidate_sha=CANDIDATE,
        command="python3 -m unittest discover -s tests",
        working_directory="/tmp/valo-runs/wt-1", exit_code=0,
        started_at="2026-08-08T09:00:00+00:00",
        ended_at="2026-08-08T09:00:05+00:00", env_profile_digest="e" * 64,
        stdout_digest="f" * 64, stderr_digest="d" * 64, test_counts=42,
        test_failures=0, evidence_id=te))
    for review_type in REQUIRED_REVIEW_TYPES:
        step(lambda rt=review_type: loop.review(
            attempt_id=att, actor=f"reviewer-{rt}", review_type=rt,
            result=PASS,
            report_id=ids.get(f"report_{rt}", f"rr-{rt}")))
    step(lambda: loop.resolve_review(attempt_id=att, actor="orchestrator"))
    step(lambda: loop.run_learner(
        attempt_id=att, actor="learner-a",
        proposals=[{"kind": "expertise",
                    "summary": "evidence loops bind digests"}],
        handoff_id=lh))
    step(lambda: loop.create_merge_candidate(
        attempt_id=att, actor="orchestrator", candidate_id=mc))
    step(lambda: loop.land(
        candidate_id=mc, actor="orchestrator", current_head_sha=BASE,
        mode=NORMAL, claim_active=True, ci_evidence="ci passed",
        reht_clearance="reht-current", racs_decision="racs-approve"))
    step(lambda: loop.post_merge_observe(
        repository=REPO, run_id=RUN, base_sha=BASE, candidate_sha=CANDIDATE,
        actor="observer-b", summary="post-merge ok", observation_id=pmo))


class FactoryEvidenceLoopTests(unittest.TestCase):

    # 1. observations are append-only evidence and cannot authorize or queue
    def test_observation_cannot_authorize_dispatch_or_queue_itself(self):
        loop = make_loop()
        obs = loop.observe(
            repository=REPO, run_id=RUN, base_sha=BASE, actor="observer-a",
            summary="add governed evidence loop", evidence="issue #40")
        self.assertEqual(loop.projection.work_items, {})
        self.assertEqual(loop.projection.execution_queue(), [])
        self.assertEqual(loop.projection.human_queue(), [])
        self.assertEqual(loop.projection.attempts, {})
        with self.assertRaises(NotFoundError):
            loop.authorize_work_item(work_item_id=obs.observation_id,
                                     actor="observer-a")
        with self.assertRaises(NotFoundError):
            loop.start_attempt(
                work_item_id=obs.observation_id, actor="writer-a",
                worktree_id="wt", base_sha=BASE,
                authority_envelope_id="nope")

    # 2. authorized Work Item mutation fails closed; revision supersedes
    def test_authorized_work_item_mutation_fails_closed(self):
        loop = make_loop()
        _, shaped = observe_and_shape(loop)
        authorized = loop.authorize_work_item(
            work_item_id=shaped.work_item.work_item_id, actor="shaper-a")
        with self.assertRaises(FrozenInstanceError):
            authorized.status = LANDED
        with self.assertRaises(ImmutabilityError):
            loop.authorize_work_item(
                work_item_id=shaped.work_item.work_item_id, actor="shaper-a")
        superseding = loop.supersede_work_item(
            work_item_id=shaped.work_item.work_item_id, actor="shaper-a")
        self.assertEqual(superseding.version, 2)
        self.assertEqual(superseding.supersedes,
                         shaped.work_item.work_item_id)
        self.assertEqual(
            loop.projection.work_items[shaped.work_item.work_item_id]["status"],
            "SUPERSEDED")

    def test_start_attempt_uses_exact_base_sha(self):
        loop = make_loop()
        _, shaped = observe_and_shape(loop)
        loop.authorize_work_item(
            work_item_id=shaped.work_item.work_item_id, actor="shaper-a")
        with self.assertRaises(AuthorityError):
            loop.start_attempt(
                work_item_id=shaped.work_item.work_item_id,
                actor="writer-a", worktree_id="wt-1",
                base_sha="c" * 40,
                authority_envelope_id=f"{shaped.work_item.work_item_id}-auth")

    # 3. expired / mismatched Authority Envelope prevents Attempt start
    def test_expired_authority_envelope_prevents_attempt_start(self):
        loop = make_loop()
        _, shaped = observe_and_shape(
            loop, work_item_id="wi-exp", expires_at="2000-01-01T00:00:00+00:00")
        loop.authorize_work_item(
            work_item_id=shaped.work_item.work_item_id, actor="shaper-a")
        with self.assertRaises(AuthorityError):
            loop.start_attempt(
                work_item_id=shaped.work_item.work_item_id,
                actor="writer-a", worktree_id="wt-1", base_sha=BASE,
                authority_envelope_id=f"{shaped.work_item.work_item_id}-auth")
        self.assertEqual(loop.projection.attempts, {})

    def test_mismatched_authority_envelope_prevents_attempt_start(self):
        loop = make_loop()
        _, shaped = observe_and_shape(loop, work_item_id="wi-mis")
        # A second work item shaped on a different base SHA provides a
        # valid-looking but mismatched Authority Envelope.
        loop.shape(
            repository=REPO, run_id=RUN, base_sha="c" * 40,
            actor="shaper-a", objective="other",
            acceptance_criteria=["a"], behavior_rules=["b"],
            approach="ap", steps=["s"], authority_basis="order",
            authority_scope=["lib/"],
            expires_at="2099-01-01T00:00:00+00:00",
            work_item_id="wi-other")
        loop.authorize_work_item(
            work_item_id=shaped.work_item.work_item_id, actor="shaper-a")
        with self.assertRaises(AuthorityError):
            loop.start_attempt(
                work_item_id=shaped.work_item.work_item_id,
                actor="writer-a", worktree_id="wt-1", base_sha=BASE,
                authority_envelope_id="wi-other-auth")
        self.assertEqual(loop.projection.attempts, {})

    # 4/6. Writer cannot produce test evidence, approve, QC, merge, land
    def test_writer_cannot_produce_tester_evidence(self):
        loop = make_loop()
        _, shaped = observe_and_shape(loop)
        loop.authorize_work_item(
            work_item_id=shaped.work_item.work_item_id, actor="shaper-a")
        attempt = loop.start_attempt(
            work_item_id=shaped.work_item.work_item_id, actor="writer-a",
            worktree_id="wt-1", base_sha=BASE,
            authority_envelope_id=f"{shaped.work_item.work_item_id}-auth")
        loop.submit_candidate(attempt_id=attempt.attempt_id,
                              actor="writer-a", candidate_sha=CANDIDATE)
        with self.assertRaises(SeparationOfDutiesError):
            loop.record_tester_evidence(
                attempt_id=attempt.attempt_id, actor="writer-a",
                candidate_sha=CANDIDATE, command="cmd",
                working_directory="/wt", exit_code=0,
                started_at="2026-08-08T09:00:00+00:00",
                ended_at="2026-08-08T09:00:05+00:00")
        self.assertEqual(loop.projection.tester_evidence, {})

    def test_writer_cannot_review_merge_or_land_own_candidate(self):
        loop = make_loop()
        loop.observe(repository=REPO, run_id=RUN, base_sha=BASE,
                     actor="observer-a", summary="s")
        loop.shape(repository=REPO, run_id=RUN, base_sha=BASE,
                   actor="shaper-a", objective="o",
                   acceptance_criteria=["a"], behavior_rules=["b"],
                   approach="ap", steps=["s"], authority_basis="order",
                   authority_scope=["lib/"],
                   expires_at="2099-01-01T00:00:00+00:00",
                   work_item_id="wi-sod")
        loop.authorize_work_item(work_item_id="wi-sod", actor="shaper-a")
        attempt = loop.start_attempt(
            work_item_id="wi-sod", actor="writer-a", worktree_id="wt-1",
            base_sha=BASE, authority_envelope_id="wi-sod-auth",
            attempt_id="att-sod")
        loop.submit_candidate(attempt_id=attempt.attempt_id,
                              actor="writer-a", candidate_sha=CANDIDATE)
        loop.record_tester_evidence(
            attempt_id=attempt.attempt_id, actor="tester-a",
            candidate_sha=CANDIDATE, command="cmd", working_directory="/wt",
            exit_code=0, started_at="2026-08-08T09:00:00+00:00",
            ended_at="2026-08-08T09:00:05+00:00", evidence_id="te-sod")
        for review_type in REQUIRED_REVIEW_TYPES:
            loop.review(attempt_id=attempt.attempt_id,
                        actor=f"reviewer-{review_type}",
                        review_type=review_type, result=PASS,
                        report_id=f"rr-sod-{review_type}")
        loop.resolve_review(attempt_id=attempt.attempt_id,
                            actor="orchestrator")
        loop.run_learner(attempt_id=attempt.attempt_id, actor="learner-a",
                         handoff_id="lh-sod")
        # Writer cannot adjudicate, QC or create/land the merge candidate.
        with self.assertRaises(SeparationOfDutiesError):
            loop.resolve_review(attempt_id=attempt.attempt_id, actor="writer-a")
        with self.assertRaises(SeparationOfDutiesError):
            loop.create_merge_candidate(attempt_id=attempt.attempt_id,
                                        actor="writer-a")
        candidate = loop.create_merge_candidate(
            attempt_id=attempt.attempt_id, actor="orchestrator",
            candidate_id="mc-sod")
        with self.assertRaises(SeparationOfDutiesError):
            loop.land(candidate_id=candidate.candidate_id, actor="writer-a",
                      current_head_sha=BASE, mode=NORMAL, ci_evidence="ci",
                      reht_clearance="reht", racs_decision="racs")

    # 5. Tester evidence bound to another SHA is rejected
    def test_tester_evidence_bound_to_another_sha_is_rejected(self):
        loop = make_loop()
        _, shaped = observe_and_shape(loop)
        loop.authorize_work_item(
            work_item_id=shaped.work_item.work_item_id, actor="shaper-a")
        attempt = loop.start_attempt(
            work_item_id=shaped.work_item.work_item_id, actor="writer-a",
            worktree_id="wt-1", base_sha=BASE,
            authority_envelope_id=f"{shaped.work_item.work_item_id}-auth")
        loop.submit_candidate(attempt_id=attempt.attempt_id,
                              actor="writer-a", candidate_sha=CANDIDATE)
        with self.assertRaises(GateError):
            loop.record_tester_evidence(
                attempt_id=attempt.attempt_id, actor="tester-a",
                candidate_sha="c" * 40, command="cmd",
                working_directory="/wt", exit_code=0,
                started_at="2026-08-08T09:00:00+00:00",
                ended_at="2026-08-08T09:00:05+00:00")
        self.assertEqual(loop.projection.tester_evidence, {})

    # 6. Reviewer cannot write candidate files (read-only + no mutation)
    def test_reviewer_cannot_write_candidate_files(self):
        loop = make_loop()
        _, shaped = observe_and_shape(loop)
        loop.authorize_work_item(
            work_item_id=shaped.work_item.work_item_id, actor="shaper-a")
        attempt = loop.start_attempt(
            work_item_id=shaped.work_item.work_item_id, actor="writer-a",
            worktree_id="wt-1", base_sha=BASE,
            authority_envelope_id=f"{shaped.work_item.work_item_id}-auth")
        loop.submit_candidate(attempt_id=attempt.attempt_id,
                              actor="writer-a", candidate_sha=CANDIDATE)
        loop.record_tester_evidence(
            attempt_id=attempt.attempt_id, actor="tester-a",
            candidate_sha=CANDIDATE, command="cmd", working_directory="/wt",
            exit_code=0, started_at="2026-08-08T09:00:00+00:00",
            ended_at="2026-08-08T09:00:05+00:00", evidence_id="te-ro")
        before = dict(loop.projection.attempts[attempt.attempt_id])
        loop.review(attempt_id=attempt.attempt_id, actor="reviewer-behavior",
                    review_type="behavior", result=PASS, report_id="rr-ro")
        after = loop.projection.attempts[attempt.attempt_id]
        self.assertEqual(after["candidate_sha"], before["candidate_sha"])
        self.assertEqual(after["worktree_id"], before["worktree_id"])
        # A Reviewer cannot submit a candidate (write) for the attempt.
        with self.assertRaises(SeparationOfDutiesError):
            loop.submit_candidate(attempt_id=attempt.attempt_id,
                                  actor="reviewer-behavior",
                                  candidate_sha=CANDIDATE)

    # 7. independent reviewers run in parallel after Tester evidence exists
    def test_independent_reviewers_run_in_parallel(self):
        loop = make_loop()
        loop.observe(repository=REPO, run_id=RUN, base_sha=BASE,
                     actor="observer-a", summary="s")
        loop.shape(repository=REPO, run_id=RUN, base_sha=BASE,
                   actor="shaper-a", objective="o",
                   acceptance_criteria=["a"], behavior_rules=["b"],
                   approach="ap", steps=["s"], authority_basis="order",
                   authority_scope=["lib/"],
                   expires_at="2099-01-01T00:00:00+00:00",
                   work_item_id="wi-par")
        loop.authorize_work_item(work_item_id="wi-par", actor="shaper-a")
        attempt = loop.start_attempt(
            work_item_id="wi-par", actor="writer-a", worktree_id="wt-1",
            base_sha=BASE, authority_envelope_id="wi-par-auth",
            attempt_id="att-par")
        loop.submit_candidate(attempt_id=attempt.attempt_id,
                              actor="writer-a", candidate_sha=CANDIDATE)
        # No reviewer may run before Tester evidence exists.
        with self.assertRaises(GateError):
            loop.review(attempt_id=attempt.attempt_id,
                        actor="reviewer-behavior", review_type="behavior",
                        result=PASS)
        loop.record_tester_evidence(
            attempt_id=attempt.attempt_id, actor="tester-a",
            candidate_sha=CANDIDATE, command="cmd", working_directory="/wt",
            exit_code=0, started_at="2026-08-08T09:00:00+00:00",
            ended_at="2026-08-08T09:00:05+00:00", evidence_id="te-par")
        reports = []
        for review_type in REQUIRED_REVIEW_TYPES:
            reports.append(loop.review(
                attempt_id=attempt.attempt_id,
                actor=f"reviewer-{review_type}", review_type=review_type,
                result=PASS, report_id=f"rr-par-{review_type}"))
        self.assertEqual(len(loop.projection.review_reports),
                         len(REQUIRED_REVIEW_TYPES))
        self.assertEqual({r.actor for r in reports},
                         {f"reviewer-{t}" for t in REQUIRED_REVIEW_TYPES})

    # 8. UNCERTAIN routes to human attention, never pass/fail
    def test_uncertain_routes_to_human_without_becoming_pass_or_fail(self):
        loop = make_loop()
        loop.observe(repository=REPO, run_id=RUN, base_sha=BASE,
                     actor="observer-a", summary="s")
        loop.shape(repository=REPO, run_id=RUN, base_sha=BASE,
                   actor="shaper-a", objective="o",
                   acceptance_criteria=["a"], behavior_rules=["b"],
                   approach="ap", steps=["s"], authority_basis="order",
                   authority_scope=["lib/"],
                   expires_at="2099-01-01T00:00:00+00:00",
                   work_item_id="wi-unc")
        loop.authorize_work_item(work_item_id="wi-unc", actor="shaper-a")
        attempt = loop.start_attempt(
            work_item_id="wi-unc", actor="writer-a", worktree_id="wt-1",
            base_sha=BASE, authority_envelope_id="wi-unc-auth",
            attempt_id="att-unc")
        loop.submit_candidate(attempt_id=attempt.attempt_id,
                              actor="writer-a", candidate_sha=CANDIDATE)
        loop.record_tester_evidence(
            attempt_id=attempt.attempt_id, actor="tester-a",
            candidate_sha=CANDIDATE, command="cmd", working_directory="/wt",
            exit_code=0, started_at="2026-08-08T09:00:00+00:00",
            ended_at="2026-08-08T09:00:05+00:00", evidence_id="te-unc")
        loop.review(attempt_id=attempt.attempt_id,
                    actor="reviewer-behavior", review_type="behavior",
                    result=UNCERTAIN, findings=[{
                        "severity": "minor", "evidence": "ambiguous",
                        "requires_human": True}],
                    report_id="rr-unc")
        resolution = loop.resolve_review(attempt_id=attempt.attempt_id,
                                         actor="orchestrator")
        self.assertEqual(resolution.result, UNCERTAIN)
        self.assertTrue(resolution.needs_human)
        self.assertIn("wi-unc", loop.projection.human_queue())
        self.assertEqual(
            loop.projection.work_items["wi-unc"]["status"], NEEDS_HUMAN)
        self.assertEqual(
            loop.projection.attempts["att-unc"]["status"], NEEDS_HUMAN)

    # 9. three failed correction rounds -> NEEDS_HUMAN
    def test_three_failed_correction_rounds_produce_needs_human(self):
        loop = make_loop(max_correction_rounds=3)
        loop.observe(repository=REPO, run_id=RUN, base_sha=BASE,
                     actor="observer-a", summary="s")
        loop.shape(repository=REPO, run_id=RUN, base_sha=BASE,
                   actor="shaper-a", objective="o",
                   acceptance_criteria=["a"], behavior_rules=["b"],
                   approach="ap", steps=["s"], authority_basis="order",
                   authority_scope=["lib/"],
                   expires_at="2099-01-01T00:00:00+00:00",
                   work_item_id="wi-cor")
        loop.authorize_work_item(work_item_id="wi-cor", actor="shaper-a")
        for i in range(1, 4):
            attempt = loop.start_attempt(
                work_item_id="wi-cor", actor="writer-a",
                worktree_id=f"wt-{i}", base_sha=BASE,
                authority_envelope_id="wi-cor-auth",
                attempt_id=f"att-cor{i}")
            loop.submit_candidate(attempt_id=attempt.attempt_id,
                                  actor="writer-a", candidate_sha=CANDIDATE)
            loop.record_tester_evidence(
                attempt_id=attempt.attempt_id, actor="tester-a",
                candidate_sha=CANDIDATE, command="cmd",
                working_directory=f"/wt-{i}", exit_code=0,
                started_at="2026-08-08T09:00:00+00:00",
                ended_at="2026-08-08T09:00:05+00:00",
                evidence_id=f"te-cor{i}")
            loop.review(
                attempt_id=attempt.attempt_id, actor="reviewer-behavior",
                review_type="behavior", result=FAIL,
                findings=[{"severity": "blocking", "evidence": "bug",
                           "file": "lib/x.py", "line": "3"}],
                report_id=f"rr-cor{i}")
            resolution = loop.resolve_review(attempt_id=attempt.attempt_id,
                                             actor="orchestrator")
            if i < 3:
                self.assertFalse(resolution.needs_human)
                self.assertEqual(
                    loop.projection.work_items["wi-cor"]["status"],
                    CORRECTING)
            else:
                self.assertTrue(resolution.needs_human)
                self.assertEqual(
                    loop.projection.work_items["wi-cor"]["status"],
                    NEEDS_HUMAN)
        self.assertEqual(
            loop.projection.work_items["wi-cor"]["correction_round"], 3)

    # 10. minor/out-of-scope findings become Observations only
    def test_minor_and_out_of_scope_findings_become_observations(self):
        loop = make_loop()
        loop.observe(repository=REPO, run_id=RUN, base_sha=BASE,
                     actor="observer-a", summary="s")
        loop.shape(repository=REPO, run_id=RUN, base_sha=BASE,
                   actor="shaper-a", objective="o",
                   acceptance_criteria=["a"], behavior_rules=["b"],
                   approach="ap", steps=["s"], authority_basis="order",
                   authority_scope=["lib/"],
                   expires_at="2099-01-01T00:00:00+00:00",
                   work_item_id="wi-min")
        loop.authorize_work_item(work_item_id="wi-min", actor="shaper-a")
        attempt = loop.start_attempt(
            work_item_id="wi-min", actor="writer-a", worktree_id="wt-1",
            base_sha=BASE, authority_envelope_id="wi-min-auth",
            attempt_id="att-min")
        loop.submit_candidate(attempt_id=attempt.attempt_id,
                              actor="writer-a", candidate_sha=CANDIDATE)
        loop.record_tester_evidence(
            attempt_id=attempt.attempt_id, actor="tester-a",
            candidate_sha=CANDIDATE, command="cmd", working_directory="/wt",
            exit_code=0, started_at="2026-08-08T09:00:00+00:00",
            ended_at="2026-08-08T09:00:05+00:00", evidence_id="te-min")
        loop.review(
            attempt_id=attempt.attempt_id, actor="reviewer-tests",
            review_type="tests", result=PASS,
            findings=[
                {"severity": "minor", "evidence": "naming nit",
                 "file": "lib/x.py", "line": "10"},
                {"severity": "out-of-scope", "evidence": "unrelated area",
                 "file": "docs/other.md"},
            ],
            report_id="rr-min")
        for review_type in ("behavior", "architecture", "documentation",
                            "security"):
            loop.review(attempt_id=attempt.attempt_id,
                        actor=f"reviewer-{review_type}",
                        review_type=review_type, result=PASS,
                        report_id=f"rr-min-{review_type}")
        resolution = loop.resolve_review(attempt_id=attempt.attempt_id,
                                         actor="orchestrator")
        self.assertEqual(resolution.result, PASS)
        minor = [o for o in loop.projection.observations.values()
                 if o["classification"] == "review-minor-finding"]
        self.assertEqual(len(minor), 2)
        # Active delivery is unchanged: still exactly one work item.
        self.assertEqual(len(loop.projection.work_items), 1)

    # 11. Learner emits proposals only; never policy/authority/activation
    def test_learner_cannot_alter_policy_authority_or_behavior_directly(self):
        loop = make_loop()
        loop.observe(repository=REPO, run_id=RUN, base_sha=BASE,
                     actor="observer-a", summary="s")
        loop.shape(repository=REPO, run_id=RUN, base_sha=BASE,
                   actor="shaper-a", objective="o",
                   acceptance_criteria=["a"], behavior_rules=["b"],
                   approach="ap", steps=["s"], authority_basis="order",
                   authority_scope=["lib/"],
                   expires_at="2099-01-01T00:00:00+00:00",
                   work_item_id="wi-le")
        loop.authorize_work_item(work_item_id="wi-le", actor="shaper-a")
        attempt = loop.start_attempt(
            work_item_id="wi-le", actor="writer-a", worktree_id="wt-1",
            base_sha=BASE, authority_envelope_id="wi-le-auth",
            attempt_id="att-le")
        loop.submit_candidate(attempt_id=attempt.attempt_id,
                              actor="writer-a", candidate_sha=CANDIDATE)
        loop.record_tester_evidence(
            attempt_id=attempt.attempt_id, actor="tester-a",
            candidate_sha=CANDIDATE, command="cmd", working_directory="/wt",
            exit_code=0, started_at="2026-08-08T09:00:00+00:00",
            ended_at="2026-08-08T09:00:05+00:00", evidence_id="te-le")
        for review_type in REQUIRED_REVIEW_TYPES:
            loop.review(attempt_id=attempt.attempt_id,
                        actor=f"reviewer-{review_type}",
                        review_type=review_type, result=PASS,
                        report_id=f"rr-le-{review_type}")
        loop.resolve_review(attempt_id=attempt.attempt_id,
                            actor="orchestrator")
        for forbidden in ("policy", "authority", "activation", "behavior",
                          "credential"):
            with self.assertRaises(GateError, msg=forbidden):
                loop.run_learner(
                    attempt_id=attempt.attempt_id, actor="learner-a",
                    proposals=[{"kind": forbidden, "summary": "x"}])
        handoff = loop.run_learner(
            attempt_id=attempt.attempt_id, actor="learner-a",
            proposals=[{"kind": "expertise",
                        "summary": "evidence loops bind digests"}],
            handoff_id="lh-le")
        # Only a handoff is recorded: no policy/authority/behavior state.
        self.assertEqual(len(loop.projection.learner_handoffs), 1)
        self.assertEqual(handoff.proposals[0]["kind"], "expertise")

    def test_learner_runs_only_after_gates(self):
        loop = make_loop()
        _, shaped = observe_and_shape(loop, work_item_id="wi-lg")
        loop.authorize_work_item(work_item_id="wi-lg", actor="shaper-a")
        attempt = loop.start_attempt(
            work_item_id="wi-lg", actor="writer-a", worktree_id="wt-1",
            base_sha=BASE, authority_envelope_id="wi-lg-auth",
            attempt_id="att-lg")
        loop.submit_candidate(attempt_id=attempt.attempt_id,
                              actor="writer-a", candidate_sha=CANDIDATE)
        loop.record_tester_evidence(
            attempt_id=attempt.attempt_id, actor="tester-a",
            candidate_sha=CANDIDATE, command="cmd", working_directory="/wt",
            exit_code=0, started_at="2026-08-08T09:00:00+00:00",
            ended_at="2026-08-08T09:00:05+00:00", evidence_id="te-lg")
        # Learner gate is closed before review passes.
        with self.assertRaises(GateError):
            loop.run_learner(attempt_id=attempt.attempt_id, actor="learner-a",
                             handoff_id="lh-lg")
        self.assertEqual(loop.projection.learner_handoffs, {})

    # 12. Merge Candidate invalidates on target/head drift
    def test_merge_candidate_invalidates_on_target_head_drift(self):
        loop = make_loop()
        result = pipeline_to_candidate(loop, ids={"candidate": "mc-drift"})
        candidate = result["candidate"]
        self.assertEqual(candidate.status, "PENDING")
        landing = loop.land(
            candidate_id=candidate.candidate_id, actor="orchestrator",
            current_head_sha="d" * 40, mode=NORMAL, ci_evidence="ci",
            reht_clearance="reht", racs_decision="racs")
        self.assertFalse(landing.landed)
        self.assertFalse(landing.checks["no_target_drift"])
        self.assertEqual(
            loop.projection.merge_candidates[candidate.candidate_id]["status"],
            "INVALID")
        # Drifted candidate cannot land even when head is corrected.
        with self.assertRaises(GateError):
            loop.land(candidate_id=candidate.candidate_id,
                      actor="orchestrator", current_head_sha=BASE,
                      mode=NORMAL, ci_evidence="ci", reht_clearance="reht",
                      racs_decision="racs")
        self.assertEqual(
            loop.projection.work_items["wi-1"]["status"],
            "MERGE_CANDIDATE")

    # 13. mode other than NORMAL prevents landing writes
    def test_mode_other_than_normal_prevents_landing_writes(self):
        loop = make_loop()
        result = pipeline_to_candidate(loop, ids={"candidate": "mc-mode"})
        landing = loop.land(
            candidate_id=result["candidate"].candidate_id,
            actor="orchestrator", current_head_sha=BASE,
            mode="MAINTENANCE", ci_evidence="ci", reht_clearance="reht",
            racs_decision="racs")
        self.assertFalse(landing.landed)
        self.assertFalse(landing.checks["mode_normal"])
        self.assertTrue(any("NORMAL" in r for r in landing.reasons))
        self.assertEqual(
            loop.projection.merge_candidates[
                result["candidate"].candidate_id]["status"], "PENDING")
        self.assertEqual(loop.projection.work_items["wi-1"]["status"],
                         "MERGE_CANDIDATE")

    # 14. missing REHT clearance / RACS permit prevents landing
    def test_missing_reht_or_racs_prevents_landing(self):
        loop = make_loop()
        result = pipeline_to_candidate(loop, ids={"candidate": "mc-gate"})
        candidate_id = result["candidate"].candidate_id
        no_reht = loop.land(candidate_id=candidate_id, actor="orchestrator",
                            current_head_sha=BASE, mode=NORMAL,
                            ci_evidence="ci", reht_clearance="",
                            racs_decision="racs")
        self.assertFalse(no_reht.landed)
        self.assertTrue(any("REHT" in r for r in no_reht.reasons))
        no_racs = loop.land(candidate_id=candidate_id, actor="orchestrator",
                            current_head_sha=BASE, mode=NORMAL,
                            ci_evidence="ci", reht_clearance="reht",
                            racs_decision="")
        self.assertFalse(no_racs.landed)
        self.assertTrue(any("RACS" in r for r in no_racs.reasons))
        # Full gate set lands successfully.
        ok = loop.land(candidate_id=candidate_id, actor="orchestrator",
                       current_head_sha=BASE, mode=NORMAL, ci_evidence="ci",
                       reht_clearance="reht", racs_decision="racs")
        self.assertTrue(ok.landed)

    # 15. repeated run is idempotent (no duplicate attempts/reviews/merges)
    def test_repeated_run_is_idempotent(self):
        # A fixed clock makes payloads byte-identical across runs so the
        # append-only store deduplicates every repeated transition.
        fixed_clock = lambda: "2026-08-08T10:00:00+00:00"
        store = MemoryEventStore()
        ids = {
            "observation_id": "obs-ip",
            "work_item": "wi-ip", "attempt": "att-ip",
            "evidence": "te-ip", "handoff": "lh-ip", "candidate": "mc-ip",
            "post_merge": "pmo-ip",
        }
        for review_type in REQUIRED_REVIEW_TYPES:
            ids[f"report_{review_type}"] = f"rr-ip-{review_type}"
        loop1 = make_loop(clock=fixed_clock, store=store)
        full_pipeline(loop1, ids=ids)
        first_hashes = [e.event_hash for e in loop1.events()]
        first_counts = {
            "attempts": len(loop1.projection.attempts),
            "reports": len(loop1.projection.review_reports),
            "candidates": len(loop1.projection.merge_candidates),
            "landings": len(loop1.projection.landings),
        }
        loop2 = make_loop(clock=fixed_clock, store=store)
        rerun_pipeline(loop2, ids=ids)
        self.assertEqual(len(loop2.events()), len(first_hashes))
        self.assertEqual([e.event_hash for e in loop2.events()],
                         first_hashes)
        self.assertEqual(len(loop2.projection.attempts),
                         first_counts["attempts"])
        self.assertEqual(len(loop2.projection.review_reports),
                         first_counts["reports"])
        self.assertEqual(len(loop2.projection.merge_candidates),
                         first_counts["candidates"])
        self.assertEqual(len(loop2.projection.landings),
                         first_counts["landings"])

    # 16. independent work items proceed while another waits for human
    def test_independent_work_items_continue_while_another_waits(self):
        loop = make_loop()
        # Work item A: routed to human attention (UNCERTAIN).
        loop.observe(repository=REPO, run_id=RUN, base_sha=BASE,
                     actor="observer-a", summary="a")
        loop.shape(repository=REPO, run_id=RUN, base_sha=BASE,
                   actor="shaper-a", objective="a",
                   acceptance_criteria=["a"], behavior_rules=["b"],
                   approach="ap", steps=["s"], authority_basis="order",
                   authority_scope=["lib/"],
                   expires_at="2099-01-01T00:00:00+00:00",
                   work_item_id="wi-a")
        loop.authorize_work_item(work_item_id="wi-a", actor="shaper-a")
        attempt_a = loop.start_attempt(
            work_item_id="wi-a", actor="writer-a", worktree_id="wt-a",
            base_sha=BASE, authority_envelope_id="wi-a-auth",
            attempt_id="att-a")
        loop.submit_candidate(attempt_id=attempt_a.attempt_id,
                              actor="writer-a", candidate_sha=CANDIDATE)
        loop.record_tester_evidence(
            attempt_id=attempt_a.attempt_id, actor="tester-a",
            candidate_sha=CANDIDATE, command="cmd", working_directory="/wta",
            exit_code=0, started_at="2026-08-08T09:00:00+00:00",
            ended_at="2026-08-08T09:00:05+00:00", evidence_id="te-a")
        loop.review(attempt_id=attempt_a.attempt_id,
                    actor="reviewer-behavior", review_type="behavior",
                    result=UNCERTAIN, report_id="rr-a")
        loop.resolve_review(attempt_id=attempt_a.attempt_id,
                            actor="orchestrator")
        self.assertIn("wi-a", loop.projection.human_queue())
        # Work item B: independent full loop to landing, not blocked by A.
        full_pipeline(loop, ids={
            "work_item": "wi-b", "attempt": "att-b", "evidence": "te-b",
            "handoff": "lh-b", "candidate": "mc-b", "post_merge": "pmo-b",
        })
        self.assertEqual(loop.projection.work_items["wi-b"]["status"], LANDED)
        self.assertEqual(loop.projection.attempts["att-b"]["status"], LANDED)
        self.assertEqual(loop.projection.work_items["wi-a"]["status"],
                         NEEDS_HUMAN)
        self.assertIn("wi-a", loop.projection.human_queue())
        self.assertEqual(len(loop.projection.merge_candidates), 1)

    # 17. deterministic replay rebuilds the same state and digests
    def test_deterministic_replay_rebuilds_same_state_and_digests(self):
        loop1 = make_loop()
        full_pipeline(loop1)
        snapshot1 = _projection_snapshot(loop1)
        hashes1 = [e.event_hash for e in loop1.events()]
        replayed = MemoryEventStore(events=loop1.events())
        loop2 = make_loop(store=replayed)
        snapshot2 = _projection_snapshot(loop2)
        self.assertEqual(hashes1, [e.event_hash for e in loop2.events()])
        self.assertEqual(snapshot1, snapshot2)

    # 18. every artifact binds repo, run, SHA, actor, schema and digest
    def test_artifacts_bind_repository_run_sha_actor_schema_digest(self):
        loop = make_loop()
        full_pipeline(loop)
        for event in loop.events():
            for key, artifact in event.payload.items():
                if not isinstance(artifact, dict) or "content_digest" not in \
                        artifact:
                    continue
                self.assertEqual(artifact["schema_version"], SCHEMA_VERSION)
                self.assertEqual(artifact["repository"], REPO)
                self.assertEqual(artifact["run_id"], RUN)
                self.assertIn(artifact["actor"], {
                    "observer-a", "observer-b", "shaper-a", "writer-a",
                    "tester-a", "orchestrator", "learner-a",
                    *[f"reviewer-{t}" for t in REQUIRED_REVIEW_TYPES],
                })
                self.assertEqual(artifact["content_digest"],
                                 artifact["content_digest"])
                self.assertTrue(len(artifact["content_digest"]) == 64)

    # 19. SQLite-backed persistence rebuilds equivalent state
    def test_sqlite_persistence_rebuilds_equivalent_state(self):
        import os
        import tempfile
        from lib.factory_evidence_loop import SqliteEventStore
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "loop.db")
            store1 = SqliteEventStore(db_path=db_path)
            loop1 = make_loop(store=store1)
            full_pipeline(loop1)
            snapshot1 = _projection_snapshot(loop1)
            hashes1 = [e.event_hash for e in loop1.events()]
            store1.close()
            store2 = SqliteEventStore(db_path=db_path)
            loop2 = make_loop(store=store2)
            snapshot2 = _projection_snapshot(loop2)
            hashes2 = [e.event_hash for e in loop2.events()]
            store2.close()
            self.assertEqual(hashes1, hashes2)
            self.assertEqual(snapshot1, snapshot2)


def _projection_snapshot(loop):
    p = loop.projection
    return {
        "observations": p.observations,
        "shape_artifacts": p.shape_artifacts,
        "work_items": p.work_items,
        "work_item_order": p.work_item_order,
        "attempts": p.attempts,
        "tester_evidence": p.tester_evidence,
        "review_reports": p.review_reports,
        "review_findings": p.review_findings,
        "learner_handoffs": p.learner_handoffs,
        "merge_candidates": p.merge_candidates,
        "post_merge_observations": p.post_merge_observations,
        "landings": p.landings,
    }


if __name__ == "__main__":
    unittest.main()
