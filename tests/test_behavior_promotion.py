"""Contract tests for governed behavior promotion and rollout."""

from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


MODULE_PATH = Path(__file__).parent.parent / "bin" / "valo-behavior-promote"
SPEC = importlib.util.spec_from_file_location(
    "valo_behavior_promote",
    MODULE_PATH,
    loader=importlib.machinery.SourceFileLoader(
        "valo_behavior_promote", str(MODULE_PATH)
    ),
)
mod = importlib.util.module_from_spec(SPEC)
sys.modules["valo_behavior_promote"] = mod
SPEC.loader.exec_module(mod)

BehaviorPromotionEngine = mod.BehaviorPromotionEngine
BehaviorPromotionRequest = mod.BehaviorPromotionRequest
ReceiptIntegrityError = mod.ReceiptIntegrityError
RolloutState = mod.RolloutState

KEY = "test-attestation-key"
ZERO_DIGEST = "sha256:" + "0" * 64
FIRST_DIGEST = "sha256:" + "1" * 64
SECOND_DIGEST = "sha256:" + "2" * 64
EVAL_DIGEST = "sha256:" + "3" * 64
AUTH_DIGEST = "sha256:" + "4" * 64
HUMAN_DIGEST = "sha256:" + "5" * 64
NOW = datetime.now(timezone.utc).replace(microsecond=0)
ISSUED_AT = (NOW - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
EXPIRES_AT = (NOW + timedelta(hours=1)).isoformat().replace("+00:00", "Z")


def signed_request(
    *,
    behavior_digest=FIRST_DIGEST,
    base_digest=ZERO_DIGEST,
    request_id="req-1",
    behavior_id="collector",
    target_scope="agent",
    authorized_scope=None,
    target_agents=None,
    risk_class="A",
    author="agent:builder",
    evaluator="agent:evaluator",
    promoter="github:promoter",
    passed=True,
    expected_role="bounded behavior module",
    prohibited_behaviors=None,
    role_evidence_refs=None,
    observed_prohibited_behaviors=None,
    baseline_terminal_score=0.8,
    terminal_score=0.8,
    baseline_role_conformance_score=1.0,
    role_conformance_score=1.0,
    role_conformance_passed=True,
    role_anchor_mode="disabled",
    issued_at=ISSUED_AT,
    expires_at=EXPIRES_AT,
    human_principal=None,
    human_digest=None,
    **flags,
):
    raw = {
        "request_id": request_id,
        "behavior_id": behavior_id,
        "behavior_digest": behavior_digest,
        "base_behavior_digest": base_digest,
        "evaluation_digest": EVAL_DIGEST,
        "promotion_request_digest": ZERO_DIGEST,
        "author_id": author,
        "evaluator_id": evaluator,
        "promoter_id": promoter,
        "target_scope": target_scope,
        "authorized_scope": authorized_scope or target_scope,
        "target_agents": target_agents or ["agent:collector"],
        "environment": "test",
        "repository": "nsolland/valo-factory",
        "commit_sha": "a" * 40,
        "policy_version": "behavior-policy.v1",
        "authority_record_digest": AUTH_DIGEST,
        "risk_class": risk_class,
        "evaluation_passed": passed,
        "expected_role": expected_role,
        "prohibited_behaviors": prohibited_behaviors or ["role_boundary_escape"],
        "role_evidence_refs": role_evidence_refs or [EVAL_DIGEST],
        "observed_prohibited_behaviors": observed_prohibited_behaviors or [],
        "baseline_terminal_score": baseline_terminal_score,
        "terminal_score": terminal_score,
        "baseline_role_conformance_score": baseline_role_conformance_score,
        "role_conformance_score": role_conformance_score,
        "role_conformance_passed": role_conformance_passed,
        "role_anchor_mode": role_anchor_mode,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "attestation_signature": "placeholder",
        "human_clearance_principal": human_principal,
        "human_clearance_digest": human_digest,
        "touches_authority": False,
        "touches_policy": False,
        "touches_credentials": False,
        "touches_execution_boundary": False,
        "touches_reht_racs": False,
        "permits_self_attestation": False,
    }
    raw.update(flags)
    provisional = BehaviorPromotionRequest.from_dict(raw)
    raw["promotion_request_digest"] = provisional.compute_digest()
    request = BehaviorPromotionRequest.from_dict(raw)
    raw["attestation_signature"] = request.expected_attestation(KEY.encode())
    return BehaviorPromotionRequest.from_dict(raw)


class BehaviorPromotionTests(unittest.TestCase):
    def engine(self, directory):
        return BehaviorPromotionEngine(
            state_file=Path(directory) / "state.json",
            receipts_file=Path(directory) / "receipts.jsonl",
            attestation_key=KEY,
            now=NOW,
        )

    def activate(self, engine, request):
        for target in (
            RolloutState.AUTHORIZED,
            RolloutState.SHADOW,
            RolloutState.CANARY,
            RolloutState.ACTIVE,
        ):
            self.assertTrue(
                engine.promote_behavior(request, target_state=target).executed
            )

    def test_valid_request_is_hmac_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            ok, reason = self.engine(directory).verify_request(signed_request())
            self.assertTrue(ok)
            self.assertEqual(reason, "VERIFIED")

    def test_terminal_improvement_cannot_waive_role_conformance_regression(self):
        with tempfile.TemporaryDirectory() as directory:
            request = signed_request(
                baseline_terminal_score=0.70,
                terminal_score=0.92,
                baseline_role_conformance_score=0.95,
                role_conformance_score=0.80,
                role_conformance_passed=True,
            )

            ok, reason = self.engine(directory).verify_request(request)

            self.assertFalse(ok)
            self.assertIn("role conformance regressed", reason)

    def test_minimum_module_role_drift_cases_fail_promotion(self):
        cases = (
            (
                "decomposer",
                "decompose without answering",
                "smuggle_final_answer_into_subquestions",
            ),
            (
                "retrieval-reader",
                "read only admitted retrieval evidence",
                "substitute_unsupported_parametric_memory",
            ),
            (
                "evaluator",
                "evaluate without authorization or execution",
                "authorize_or_execute",
            ),
            (
                "worker",
                "operate within presented capability and workspace",
                "widen_capability_mutate_state_or_escape_workspace",
            ),
            (
                "harness",
                "measure through the canonical effect path",
                "create_second_effect_path",
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            engine = self.engine(directory)
            for module_id, expected_role, prohibited in cases:
                with self.subTest(module=module_id):
                    request = signed_request(
                        request_id=f"req-{module_id}",
                        behavior_id=module_id,
                        expected_role=expected_role,
                        prohibited_behaviors=[prohibited],
                        role_evidence_refs=[f"receipt:{module_id}:role-eval"],
                        observed_prohibited_behaviors=[prohibited],
                        role_conformance_passed=False,
                    )
                    ok, reason = engine.verify_request(request)
                    self.assertFalse(ok)
                    self.assertIn("prohibited behavior", reason)

    def test_role_anchor_is_experimental_and_cannot_replace_runtime_enforcement(self):
        with tempfile.TemporaryDirectory() as directory:
            request = signed_request(
                role_anchor_mode="experimental_training_control",
                baseline_role_conformance_score=1.0,
                role_conformance_score=0.7,
                role_conformance_passed=False,
            )

            ok, reason = self.engine(directory).verify_request(request)

            self.assertFalse(ok)
            self.assertIn("role conformance regressed", reason)

    def test_role_evaluation_is_recorded_in_existing_receipt_lineage(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = self.engine(directory)
            request = signed_request(
                expected_role="retrieval-bound reader",
                prohibited_behaviors=["unsupported_parametric_memory"],
                role_evidence_refs=["receipt:reader-evaluation"],
                terminal_score=0.9,
            )

            receipt = engine.promote_behavior(
                request, target_state=RolloutState.AUTHORIZED
            )

            self.assertTrue(receipt.executed)
            self.assertEqual(receipt.evaluation_digest, EVAL_DIGEST)
            self.assertEqual(receipt.expected_role, "retrieval-bound reader")
            self.assertEqual(receipt.role_conformance_score, 1.0)
            self.assertTrue(receipt.role_conformance_passed)
            self.assertEqual(
                engine.receipts[0]["role_evidence_refs"],
                ["receipt:reader-evaluation"],
            )

    def test_role_evidence_must_be_receipt_linked_not_self_reported_rationale(self):
        with tempfile.TemporaryDirectory() as directory:
            request = signed_request(role_evidence_refs=["rationale:looks-conformant"])

            ok, reason = self.engine(directory).verify_request(request)

            self.assertFalse(ok)
            self.assertIn("receipt-linked evidence", reason)

    def test_forged_attestation_is_denied(self):
        with tempfile.TemporaryDirectory() as directory:
            request = signed_request()
            raw = dict(request.__dict__)
            raw["target_agents"] = list(request.target_agents)
            raw["attestation_signature"] = "0" * 64
            ok, reason = self.engine(directory).verify_request(
                BehaviorPromotionRequest.from_dict(raw)
            )
            self.assertFalse(ok)
            self.assertIn("signature verification failed", reason)

    def test_separation_of_duties_is_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            request = signed_request(
                author="agent:same", promoter="agent:same"
            )
            ok, reason = self.engine(directory).verify_request(request)
            self.assertFalse(ok)
            self.assertIn("must be distinct", reason)

    def test_sensitive_change_is_class_c_and_human_gated(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = self.engine(directory)
            ok, reason = engine.verify_request(
                signed_request(risk_class="A", touches_policy=True)
            )
            self.assertFalse(ok)
            self.assertIn("risk class C", reason)

            ok, reason = engine.verify_request(
                signed_request(risk_class="C", touches_policy=True)
            )
            self.assertFalse(ok)
            self.assertIn("explicit human GitHub clearance", reason)

            ok, _ = engine.verify_request(signed_request(
                risk_class="C",
                touches_policy=True,
                human_principal="github:nsolland",
                human_digest=HUMAN_DIGEST,
            ))
            self.assertTrue(ok)

    def test_scope_expansion_is_denied(self):
        with tempfile.TemporaryDirectory() as directory:
            request = signed_request(
                target_scope="organization", authorized_scope="agent"
            )
            ok, reason = self.engine(directory).verify_request(request)
            self.assertFalse(ok)
            self.assertIn("exactly match", reason)

    def test_full_state_machine_is_persistent(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = self.engine(directory)
            self.activate(engine, signed_request())
            reloaded = self.engine(directory)
            state = reloaded.status("collector")
            self.assertEqual(state["state"], RolloutState.ACTIVE)
            self.assertEqual(state["active_digest"], FIRST_DIGEST)
            self.assertEqual(len(reloaded.receipts), 4)

    def test_organization_scope_cannot_skip_canary(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = self.engine(directory)
            request = signed_request(target_scope="organization")
            self.assertTrue(engine.promote_behavior(
                request, target_state=RolloutState.AUTHORIZED
            ).executed)
            self.assertTrue(engine.promote_behavior(
                request, target_state=RolloutState.SHADOW
            ).executed)
            denied = engine.promote_behavior(
                request, target_state=RolloutState.ACTIVE
            )
            self.assertFalse(denied.executed)
            self.assertIn("requires CANARY", denied.reason)

    def test_stale_base_digest_is_denied(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = self.engine(directory)
            self.activate(engine, signed_request())
            stale = signed_request(
                behavior_digest=SECOND_DIGEST,
                base_digest=ZERO_DIGEST,
                request_id="req-2",
            )
            ok, reason = engine.verify_request(stale)
            self.assertFalse(ok)
            self.assertIn("base behavior digest is stale", reason)

    def test_exact_prior_authorized_digest_is_required_for_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = self.engine(directory)
            self.activate(engine, signed_request())

            second = signed_request(
                behavior_digest=SECOND_DIGEST,
                base_digest=FIRST_DIGEST,
                request_id="req-2",
            )
            self.assertTrue(engine.promote_behavior(
                second, target_state=RolloutState.REQUESTED
            ).executed)
            self.activate(engine, second)

            rollback_request = signed_request(
                behavior_digest=SECOND_DIGEST,
                base_digest=SECOND_DIGEST,
                request_id="req-rollback",
            )
            denied = engine.rollback_behavior(
                rollback_request, rollback_digest=ZERO_DIGEST
            )
            self.assertFalse(denied.executed)
            allowed = engine.rollback_behavior(
                rollback_request, rollback_digest=FIRST_DIGEST
            )
            self.assertTrue(allowed.executed)
            self.assertEqual(
                engine.status("collector")["active_digest"], FIRST_DIGEST
            )

    def test_receipt_chain_fails_closed_on_edit(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = self.engine(directory)
            engine.promote_behavior(
                signed_request(), target_state=RolloutState.AUTHORIZED
            )
            receipts = Path(directory) / "receipts.jsonl"
            line = json.loads(receipts.read_text(encoding="utf-8"))
            line["reason"] = "tampered"
            receipts.write_text(json.dumps(line) + "\n", encoding="utf-8")
            with self.assertRaises(ReceiptIntegrityError):
                self.engine(directory)

    def test_cli_executes_verify_promote_and_status(self):
        with tempfile.TemporaryDirectory() as directory:
            request = signed_request()
            request_file = Path(directory) / "request.json"
            raw = dict(request.__dict__)
            raw["target_agents"] = list(request.target_agents)
            request_file.write_text(json.dumps(raw), encoding="utf-8")
            state_file = Path(directory) / "state.json"
            receipts_file = Path(directory) / "receipts.jsonl"
            env = {"VALO_BEHAVIOR_ATTESTATION_KEY": KEY}

            with patch.dict(os.environ, env, clear=False):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = mod.main([
                        "--verify",
                        "--request", str(request_file),
                        "--state-file", str(state_file),
                        "--receipts-file", str(receipts_file),
                    ])
                self.assertEqual(code, 0, output.getvalue())
                self.assertTrue(json.loads(output.getvalue())["verified"])

                output = io.StringIO()
                with redirect_stdout(output):
                    code = mod.main([
                        "--promote",
                        "--request", str(request_file),
                        "--target-state", RolloutState.AUTHORIZED,
                        "--state-file", str(state_file),
                        "--receipts-file", str(receipts_file),
                    ])
                self.assertEqual(code, 0, output.getvalue())
                self.assertTrue(json.loads(output.getvalue())["executed"])

                output = io.StringIO()
                with redirect_stdout(output):
                    code = mod.main([
                        "--status",
                        "--behavior-id", "collector",
                        "--state-file", str(state_file),
                        "--receipts-file", str(receipts_file),
                    ])
                self.assertEqual(code, 0, output.getvalue())
                self.assertEqual(
                    json.loads(output.getvalue())["state"],
                    RolloutState.AUTHORIZED,
                )


if __name__ == "__main__":
    unittest.main()
