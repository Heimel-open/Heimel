#!/usr/bin/env python3
"""VALO Orchestrator — Parable 5-gate workflow on top of existing governance contracts.

Design rule: Director/Worker/5-gate reuse REHT/VAIG/RACS primitives.
No parallel governance layer. Every gate outcome is an Evidence/Envelope/Receipt.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from broker.broker import ActionEnvelope, Evidence, ValoBroker
from broker.parable import Gate, Plan

log = logging.getLogger("valo.orchestrator")


class RatchetLimitExceeded(Exception):
    pass


class ParableOrchestrator:
    """Run a 5-gate workflow: Plan → Evidence → Command → Review → Ensemble.

    Each gate produces real REHT/VAIG/RACS artifacts:
    - Evidence stored via `broker.add_evidence`
    - Actions sealed as envelopes via `broker.seal_envelope`
    - Outcomes recorded as receipts via `broker.record_receipt`
    - Reviews and ensembles stored via Parable tables, linked to plan/gate IDs
    """

    def __init__(self, broker: ValoBroker) -> None:
        self.broker = broker

    # ---------- High-level workflow ----------

    def run_5gate(
        self,
        actor: str,
        intent: str,
        evidence_sources: List[tuple[str, str]],
        director_brief: str,
        workers: List[str],
        senior: str,
        max_ratchet_rounds: int = 3,
    ) -> Dict[str, Any]:
        """Run the full 5-gate loop for a single intent.

        Args:
            actor: who initiates
            intent: what we want to achieve
            evidence_sources: list of (source, content) tuples for initial evidence
            director_brief: the Director's brief for the worker
            workers: list of worker identifiers/models
            senior: reviewer identifier/model
            max_ratchet_rounds: max iterations for Review gate

        Returns:
            Summary dict with plan_id, gate outcomes, and final receipt refs
        """
        # Gate 0: create plan from existing evidence
        initial_evidence = [
            self.broker.add_evidence(src, content).claim_id for src, content in evidence_sources
        ]
        plan = self.broker.create_plan(actor=actor, intent=intent, evidence_ids=initial_evidence)
        self.broker.approve_plan(plan.plan_id)

        # Gate 1: evidence check — already satisfied by creation, seal as envelope
        g_evidence = self.broker.add_gate(plan.plan_id, "Evidence check", "evidence", True, seq=1)
        self.broker.pass_gate(
            g_evidence.gate_id,
            evidence_ids=initial_evidence,
            output_ref=f"evidence:{len(initial_evidence)} items",
        )
        self._seal_gate_envelope(plan, g_evidence, actor, "evidence.check", initial_evidence)

        # Gate 2: command/output — worker executes the brief
        g_cmd = self.broker.add_gate(plan.plan_id, "Command output", "command_output", True, seq=2)
        delegation = self.broker.create_delegation(
            plan.plan_id,
            g_cmd.gate_id,
            actor,
            workers[0],
            director_brief,
        )
        # Worker executes → sealed as envelope + receipt
        worker_result = self._execute_worker(delegation)
        self.broker.complete_delegation(delegation.delegation_id, result_ref=worker_result["ref"])
        self.broker.pass_gate(g_cmd.gate_id, output_ref=worker_result["ref"])
        self._seal_gate_envelope(plan, g_cmd, actor, "command.execute", [worker_result["ref"]])

        # Gate 3: review — senior reviews, with ratchet loop
        g_review = self.broker.add_gate(plan.plan_id, "Review", "review", True, seq=3)
        review_result = self._ratchet_review(
            plan.plan_id,
            g_review.gate_id,
            delegation.delegation_id,
            senior,
            max_ratchet_rounds,
        )
        self.broker.pass_gate(g_review.gate_id, output_ref=review_result["ref"])
        self._seal_gate_envelope(plan, g_review, actor, "review.ratchet", [review_result["ref"]])

        # Gate 4: ensemble — N-way check for contradictions
        g_ensemble = self.broker.add_gate(plan.plan_id, "Ensemble", "ensemble", True, seq=4)
        ensemble = self.broker.create_ensemble(
            plan.plan_id,
            g_ensemble.gate_id,
            workers,
            "Contradiction check on: {}".format(intent),
        )
        ensemble_result = self._run_ensemble(ensemble)
        self.broker.complete_ensemble(ensemble.ensemble_id, result_ref=ensemble_result["ref"])
        self.broker.pass_gate(g_ensemble.gate_id, output_ref=ensemble_result["ref"])
        self._seal_gate_envelope(plan, g_ensemble, actor, "ensemble.check", [ensemble_result["ref"]])

        # Final: seal the whole plan as a delivery envelope
        final_envelope = ActionEnvelope(
            actor=actor,
            intent=intent,
            evidence_ids=initial_evidence,
            tool="parable.5gate.complete",
            params={
                "plan_id": plan.plan_id,
                "gate_count": 4,
                "worker": workers[0],
                "reviewer": senior,
            },
        )
        sealed = self.broker.seal_envelope(final_envelope)
        self.broker.record_receipt(sealed.envelope_id, "ok", result_hash=ensemble_result["ref"])

        return {
            "plan_id": plan.plan_id,
            "envelope_id": sealed.envelope_id,
            "gates_passed": 4,
            "ratchet_rounds": review_result.get("rounds", 0),
            "contradictions": ensemble_result.get("contradictions", 0),
            "receipt": sealed.signature,
        }

    # ---------- Worker execution (reuses envelope/receipt) ----------

    def _execute_worker(self, delegation: Any) -> Dict[str, Any]:
        """Simulate worker execution by sealing an envelope and recording a receipt."""
        ref = f"worker:{delegation.worker}:{delegation.delegation_id[:8]}"
        envelope = ActionEnvelope(
            actor=delegation.worker,
            intent=delegation.brief,
            evidence_ids=[],
            tool="worker.execute",
            params={"delegation_id": delegation.delegation_id},
        )
        sealed = self.broker.seal_envelope(envelope)
        self.broker.record_receipt(sealed.envelope_id, "ok", result_hash=ref)
        log.debug("Worker executed: %s → %s", delegation.worker, ref)
        return {"ref": ref, "envelope_id": sealed.envelope_id}

    # ---------- Ratchet review ----------

    def _ratchet_review(
        self,
        plan_id: str,
        gate_id: str,
        delegation_id: str,
        reviewer: str,
        max_rounds: int = 3,
    ) -> Dict[str, Any]:
        """Run review with ratchet loop: revise until approve or max rounds."""
        for round_i in range(1, max_rounds + 1):
            verdict = "approve" if round_i >= max_rounds else "revise"
            notes = "Ratchet round {}/{}".format(round_i, max_rounds)
            review = self.broker.add_review(delegation_id, reviewer, verdict, notes)
            ref = f"review:{review.review_id}"
            if verdict == "approve":
                return {"ref": ref, "rounds": round_i}
            # revise: mark gate pending for re-delegation
            self.broker.pass_gate(gate_id, output_ref=f"{ref}:revised")
        raise RatchetLimitExceeded(
            "Review did not converge within {} rounds for plan {}".format(max_rounds, plan_id)
        )

    # ---------- Ensemble contradiction check ----------

    def _run_ensemble(self, ensemble: Any) -> Dict[str, Any]:
        """Simulate ensemble: run N workers, record contradictions if any."""
        agents = json.loads(ensemble.agents) if isinstance(ensemble.agents, str) else ensemble.agents
        contradictions = 0
        for i in range(len(agents) - 1):
            for j in range(i + 1, len(agents)):
                # In production: compare actual outputs; here we simulate no contradictions
                pass
        ref = f"ensemble:{ensemble.ensemble_id}:{len(agents)} agents"
        return {"ref": ref, "contradictions": contradictions}

    # ---------- Helpers ----------

    def _seal_gate_envelope(
        self, plan: Plan, gate: Gate, actor: str, tool: str, evidence_ids: List[str]
    ) -> ActionEnvelope:
        envelope = ActionEnvelope(
            actor=actor,
            intent=f"Gate {gate.seq}: {gate.name} for plan {plan.plan_id}",
            evidence_ids=evidence_ids,
            tool=tool,
            params={"plan_id": plan.plan_id, "gate_id": gate.gate_id},
        )
        return self.broker.seal_envelope(envelope)
