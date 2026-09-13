#!/usr/bin/env python3
"""VALO Broker — Parable-inspired extensions.

Adds: Plan, Gate, Delegation, Review, Ensemble, Contradiction.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Plan:
    plan_id: str
    actor: str
    intent: str
    evidence_ids: List[str]
    status: str = "draft"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class Gate:
    gate_id: str
    plan_id: str
    seq: int
    name: str
    check_type: str
    required: bool = True
    status: str = "pending"
    evidence_ids: Optional[str] = None
    output_ref: Optional[str] = None


@dataclass
class Delegation:
    delegation_id: str
    plan_id: str
    gate_id: str
    actor: str
    worker: str
    brief: str
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    result_ref: Optional[str] = None


@dataclass
class Review:
    review_id: str
    delegation_id: str
    reviewer: str
    verdict: str
    notes: Optional[str]
    created_at: float = field(default_factory=time.time)


@dataclass
class EnsembleRun:
    ensemble_id: str
    plan_id: str
    gate_id: str
    agents: List[str]
    brief: str
    status: str = "running"
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    result_ref: Optional[str] = None


@dataclass
class Contradiction:
    contradiction_id: str
    ensemble_id: str
    agent_a: str
    agent_b: str
    topic: str
    resolution: Optional[str]
    created_at: float = field(default_factory=time.time)


class ParableBrokerMixin:
    """Mixin providing Parable workflow methods."""

    # ---------- Plans ----------

    def create_plan(self, actor: str, intent: str, evidence_ids: List[str]) -> Plan:
        plan_id = uuid.uuid4().hex[:24]
        now = time.time()
        self._conn.execute(
            "INSERT INTO plans (plan_id, actor, intent, evidence_ids, status, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
            (plan_id, actor, intent, json.dumps(evidence_ids), "draft", now, now),
        )
        self._conn.commit()
        return Plan(plan_id=plan_id, actor=actor, intent=intent, evidence_ids=evidence_ids, created_at=now, updated_at=now)

    def approve_plan(self, plan_id: str) -> None:
        now = time.time()
        self._conn.execute(
            "UPDATE plans SET status='approved', updated_at=? WHERE plan_id=?",
            (now, plan_id),
        )
        self._conn.commit()

    def get_plan(self, plan_id: str) -> Optional[dict[str, Any]]:
        row = self._conn.execute("SELECT * FROM plans WHERE plan_id=?", (plan_id,)).fetchone()
        return dict(row) if row else None

    def list_plans(self, limit: int = 20) -> List[dict[str, Any]]:
        return [dict(r) for r in self._conn.execute(
            "SELECT * FROM plans ORDER BY created_at DESC LIMIT ?", (int(limit),)
        ).fetchall()]

    # ---------- Gates ----------

    def add_gate(self, plan_id: str, name: str, check_type: str, required: bool = True, seq: Optional[int] = None) -> Gate:
        gate_id = uuid.uuid4().hex[:24]
        if seq is None:
            row = self._conn.execute("SELECT COUNT(*) FROM gates WHERE plan_id=?", (plan_id,)).fetchone()
            seq = (row[0] if row else 0) + 1
        self._conn.execute(
            "INSERT INTO gates (gate_id, plan_id, seq, name, check_type, required, status) VALUES (?,?,?,?,?,?,?)",
            (gate_id, plan_id, seq, name, check_type, 1 if required else 0, "pending"),
        )
        self._conn.commit()
        return Gate(gate_id=gate_id, plan_id=plan_id, seq=seq, name=name, check_type=check_type, required=required)

    def pass_gate(self, gate_id: str, evidence_ids: Optional[List[str]] = None, output_ref: Optional[str] = None) -> None:
        self._conn.execute(
            "UPDATE gates SET status='passed', evidence_ids=?, output_ref=? WHERE gate_id=?",
            (json.dumps(evidence_ids or []), output_ref, gate_id),
        )
        self._conn.commit()

    def list_gates(self, plan_id: str) -> List[dict[str, Any]]:
        return [dict(r) for r in self._conn.execute(
            "SELECT * FROM gates WHERE plan_id=? ORDER BY seq ASC", (plan_id,)
        ).fetchall()]

    # ---------- Delegations ----------

    def create_delegation(self, plan_id: str, gate_id: str, actor: str, worker: str, brief: str) -> Delegation:
        delegation_id = uuid.uuid4().hex[:24]
        now = time.time()
        self._conn.execute(
            "INSERT INTO delegations (delegation_id, plan_id, gate_id, actor, worker, brief, status, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (delegation_id, plan_id, gate_id, actor, worker, brief, "pending", now),
        )
        self._conn.commit()
        return Delegation(delegation_id=delegation_id, plan_id=plan_id, gate_id=gate_id, actor=actor, worker=worker, brief=brief, created_at=now)

    def complete_delegation(self, delegation_id: str, result_ref: Optional[str] = None) -> None:
        now = time.time()
        self._conn.execute(
            "UPDATE delegations SET status='done', completed_at=?, result_ref=? WHERE delegation_id=?",
            (now, result_ref, delegation_id),
        )
        self._conn.commit()

    def list_delegations(self, plan_id: str) -> List[dict[str, Any]]:
        return [dict(r) for r in self._conn.execute(
            "SELECT * FROM delegations WHERE plan_id=? ORDER BY created_at ASC", (plan_id,)
        ).fetchall()]

    # ---------- Reviews ----------

    def add_review(self, delegation_id: str, reviewer: str, verdict: str, notes: Optional[str] = None) -> Review:
        review_id = uuid.uuid4().hex[:24]
        self._conn.execute(
            "INSERT INTO reviews (review_id, delegation_id, reviewer, verdict, notes, created_at) VALUES (?,?,?,?,?,?)",
            (review_id, delegation_id, reviewer, verdict, notes, time.time()),
        )
        self._conn.commit()
        return Review(review_id=review_id, delegation_id=delegation_id, reviewer=reviewer, verdict=verdict, notes=notes)

    def list_reviews(self, delegation_id: str) -> List[dict[str, Any]]:
        return [dict(r) for r in self._conn.execute(
            "SELECT * FROM reviews WHERE delegation_id=? ORDER BY created_at ASC", (delegation_id,)
        ).fetchall()]

    # ---------- Ensembles ----------

    def create_ensemble(self, plan_id: str, gate_id: str, agents: List[str], brief: str) -> EnsembleRun:
        ensemble_id = uuid.uuid4().hex[:24]
        now = time.time()
        self._conn.execute(
            "INSERT INTO ensemble_runs (ensemble_id, plan_id, gate_id, agents, brief, status, created_at) VALUES (?,?,?,?,?,?,?)",
            (ensemble_id, plan_id, gate_id, json.dumps(agents), brief, "running", now),
        )
        self._conn.commit()
        return EnsembleRun(ensemble_id=ensemble_id, plan_id=plan_id, gate_id=gate_id, agents=agents, brief=brief, created_at=now)

    def complete_ensemble(self, ensemble_id: str, result_ref: Optional[str] = None) -> None:
        now = time.time()
        self._conn.execute(
            "UPDATE ensemble_runs SET status='done', completed_at=?, result_ref=? WHERE ensemble_id=?",
            (now, result_ref, ensemble_id),
        )
        self._conn.commit()

    def list_ensembles(self, plan_id: str) -> List[dict[str, Any]]:
        return [dict(r) for r in self._conn.execute(
            "SELECT * FROM ensemble_runs WHERE plan_id=? ORDER BY created_at ASC", (plan_id,)
        ).fetchall()]

    # ---------- Contradictions ----------

    def add_contradiction(self, ensemble_id: str, agent_a: str, agent_b: str, topic: str, resolution: Optional[str] = None) -> Contradiction:
        contradiction_id = uuid.uuid4().hex[:24]
        self._conn.execute(
            "INSERT INTO contradictions (contradiction_id, ensemble_id, agent_a, agent_b, topic, resolution, created_at) VALUES (?,?,?,?,?,?,?)",
            (contradiction_id, ensemble_id, agent_a, agent_b, topic, resolution, time.time()),
        )
        self._conn.commit()
        return Contradiction(contradiction_id=contradiction_id, ensemble_id=ensemble_id, agent_a=agent_a, agent_b=agent_b, topic=topic, resolution=resolution)

    def resolve_contradiction(self, contradiction_id: str, resolution: str) -> None:
        self._conn.execute(
            "UPDATE contradictions SET resolution=? WHERE contradiction_id=?",
            (resolution, contradiction_id),
        )
        self._conn.commit()

    def list_contradictions(self, ensemble_id: str) -> List[dict[str, Any]]:
        return [dict(r) for r in self._conn.execute(
            "SELECT * FROM contradictions WHERE ensemble_id=? ORDER BY created_at ASC", (ensemble_id,)
        ).fetchall()]
