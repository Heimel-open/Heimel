#!/usr/bin/env python3
"""VALO Broker — minimal governance core.

Implements VAIG evidence-gating + RACS action envelope + receipts.
This is intentionally offline-capable and has no external API dependencies.
"""
import hashlib
import json
import logging
import os
import sqlite3
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from broker.parable import ParableBrokerMixin

log = logging.getLogger("valo.broker")


@dataclass
class Evidence:
    claim_id: str
    source: str
    content_hash: str
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ActionEnvelope:
    actor: str
    intent: str
    evidence_ids: List[str]
    tool: str
    params: Dict[str, Any]
    envelope_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    signature: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ValoBroker(ParableBrokerMixin):
    """In-process governance broker."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        base_sql = """
        CREATE TABLE IF NOT EXISTS evidence (
            claim_id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS envelopes (
            envelope_id TEXT PRIMARY KEY,
            actor TEXT NOT NULL,
            intent TEXT NOT NULL,
            evidence_ids TEXT NOT NULL,
            tool TEXT NOT NULL,
            params TEXT NOT NULL,
            created_at REAL NOT NULL,
            signature TEXT
        );
        CREATE TABLE IF NOT EXISTS receipts (
            receipt_id TEXT PRIMARY KEY,
            envelope_id TEXT NOT NULL,
            status TEXT NOT NULL,
            result_hash TEXT,
            created_at REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_envelopes_actor ON envelopes(actor);
        CREATE INDEX IF NOT EXISTS idx_receipts_envelope ON receipts(envelope_id);
        """
        parable_sql = """
        CREATE TABLE IF NOT EXISTS plans (
            plan_id TEXT PRIMARY KEY,
            actor TEXT NOT NULL,
            intent TEXT NOT NULL,
            evidence_ids TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS gates (
            gate_id TEXT PRIMARY KEY,
            plan_id TEXT NOT NULL,
            seq INTEGER NOT NULL,
            name TEXT NOT NULL,
            check_type TEXT NOT NULL,
            required BOOLEAN DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'pending',
            evidence_ids TEXT,
            output_ref TEXT,
            FOREIGN KEY(plan_id) REFERENCES plans(plan_id)
        );
        CREATE TABLE IF NOT EXISTS delegations (
            delegation_id TEXT PRIMARY KEY,
            plan_id TEXT NOT NULL,
            gate_id TEXT NOT NULL,
            actor TEXT NOT NULL,
            worker TEXT NOT NULL,
            brief TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at REAL NOT NULL,
            completed_at REAL,
            result_ref TEXT,
            FOREIGN KEY(plan_id) REFERENCES plans(plan_id),
            FOREIGN KEY(gate_id) REFERENCES gates(gate_id)
        );
        CREATE TABLE IF NOT EXISTS reviews (
            review_id TEXT PRIMARY KEY,
            delegation_id TEXT NOT NULL,
            reviewer TEXT NOT NULL,
            verdict TEXT NOT NULL,
            notes TEXT,
            created_at REAL NOT NULL,
            FOREIGN KEY(delegation_id) REFERENCES delegations(delegation_id)
        );
        CREATE TABLE IF NOT EXISTS ensemble_runs (
            ensemble_id TEXT PRIMARY KEY,
            plan_id TEXT NOT NULL,
            gate_id TEXT NOT NULL,
            agents TEXT NOT NULL,
            brief TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'running',
            created_at REAL NOT NULL,
            completed_at REAL,
            result_ref TEXT,
            FOREIGN KEY(plan_id) REFERENCES plans(plan_id),
            FOREIGN KEY(gate_id) REFERENCES gates(gate_id)
        );
        CREATE TABLE IF NOT EXISTS contradictions (
            contradiction_id TEXT PRIMARY KEY,
            ensemble_id TEXT NOT NULL,
            agent_a TEXT NOT NULL,
            agent_b TEXT NOT NULL,
            topic TEXT NOT NULL,
            resolution TEXT,
            created_at REAL NOT NULL,
            FOREIGN KEY(ensemble_id) REFERENCES ensemble_runs(ensemble_id)
        );
        CREATE INDEX IF NOT EXISTS idx_plans_actor ON plans(actor);
        CREATE INDEX IF NOT EXISTS idx_gates_plan ON gates(plan_id);
        CREATE INDEX IF NOT EXISTS idx_delegations_plan ON delegations(plan_id);
        CREATE INDEX IF NOT EXISTS idx_reviews_delegation ON reviews(delegation_id);
        CREATE INDEX IF NOT EXISTS idx_ensemble_plan ON ensemble_runs(plan_id);
        CREATE INDEX IF NOT EXISTS idx_contradictions_ensemble ON contradictions(ensemble_id);
        """
        self._conn.executescript(base_sql + parable_sql)
        self._conn.commit()

    # ---------- Evidence ----------

    def add_evidence(self, source: str, content: str | bytes) -> Evidence:
        if isinstance(content, bytes):
            content_hash = hashlib.sha256(content).hexdigest()
        else:
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        claim_id = hashlib.sha256(
            f"{source}:{content_hash}:{time.time()}".encode("utf-8")
        ).hexdigest()[:32]

        ev = Evidence(
            claim_id=claim_id, source=source, content_hash=content_hash
        )
        self._conn.execute(
            "INSERT OR REPLACE INTO evidence (claim_id, source, content_hash, created_at) VALUES (?,?,?,?)",
            (ev.claim_id, ev.source, ev.content_hash, ev.created_at),
        )
        self._conn.commit()
        log.debug("Evidence stored: %s", ev.claim_id)
        return ev

    def list_evidence(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT claim_id, source, content_hash, created_at FROM evidence ORDER BY created_at DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
        return [dict(r) for r in rows]

    # ---------- Envelopes ----------

    def seal_envelope(self, envelope: ActionEnvelope) -> ActionEnvelope:
        payload = json.dumps(
            {
                "actor": envelope.actor,
                "intent": envelope.intent,
                "evidence_ids": envelope.evidence_ids,
                "tool": envelope.tool,
                "params": envelope.params,
            },
            sort_keys=True,
        )
        envelope.signature = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        self._conn.execute(
            "INSERT OR REPLACE INTO envelopes (envelope_id, actor, intent, evidence_ids, tool, params, created_at, signature) VALUES (?,?,?,?,?,?,?,?)",
            (
                envelope.envelope_id,
                envelope.actor,
                envelope.intent,
                json.dumps(envelope.evidence_ids),
                envelope.tool,
                json.dumps(envelope.params),
                envelope.created_at,
                envelope.signature,
            ),
        )
        self._conn.commit()
        log.info("Envelope sealed: %s", envelope.envelope_id)
        return envelope

    def record_receipt(
        self, envelope_id: str, status: str, result_hash: str | None = None
    ) -> dict[str, Any]:
        receipt_id = hashlib.sha256(
            f"{envelope_id}:{status}:{time.time()}".encode("utf-8")
        ).hexdigest()[:32]

        self._conn.execute(
            "INSERT OR REPLACE INTO receipts (receipt_id, envelope_id, status, result_hash, created_at) VALUES (?,?,?,?,?)",
            (receipt_id, envelope_id, status, result_hash, time.time()),
        )
        self._conn.commit()
        log.debug("Receipt recorded: %s (%s)", receipt_id, status)
        return {"receipt_id": receipt_id, "envelope_id": envelope_id, "status": status}

    def audit_trail(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT r.receipt_id, r.envelope_id, e.actor, e.tool, r.status, r.result_hash, r.created_at
            FROM receipts r
            JOIN envelopes e ON r.envelope_id = e.envelope_id
            ORDER BY r.created_at DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
        return [dict(r) for r in rows]
