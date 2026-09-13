#!/usr/bin/env python3
"""Minimal MCP server exposing VALO governance as tools.

Protocol: stdio JSON-RPC (MCP 2024-11-05 style).
"""
from __future__ import annotations

import json
import logging
import sys
from typing import Any

from broker.broker import ValoBroker, Evidence, ActionEnvelope
from broker.parable import ParableBrokerMixin

log = logging.getLogger("valo.mcp.server")


def create_mcp_server(broker: ValoBroker):
    """Return an MCP server object with .run() that speaks JSON-RPC over stdio."""
    tools: list[dict[str, Any]] = [
        # ... existing tools ...
    ]

    # --- Parable workflow tools ---
    tools.extend([
        {
            "name": "valo.create_plan",
            "description": "Create a Parable-style plan: intent + evidence ids. Returns plan_id.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "actor": {"type": "string"},
                    "intent": {"type": "string"},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["actor", "intent", "evidence_ids"],
            },
        },
        {
            "name": "valo.approve_plan",
            "description": "Approve a plan so execution can begin.",
            "inputSchema": {
                "type": "object",
                "properties": {"plan_id": {"type": "string"}},
                "required": ["plan_id"],
            },
        },
        {
            "name": "valo.list_plans",
            "description": "List recent plans.",
            "inputSchema": {
                "type": "object",
                "properties": {"limit": {"type": "integer", "default": 20}},
            },
        },
        {
            "name": "valo.add_gate",
            "description": "Add a 5-gate check to a plan: evidence | command_output | review | ensemble.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string"},
                    "name": {"type": "string"},
                    "check_type": {"type": "string", "enum": ["evidence", "command_output", "review", "ensemble"]},
                    "required": {"type": "boolean", "default": True},
                },
                "required": ["plan_id", "name", "check_type"],
            },
        },
        {
            "name": "valo.pass_gate",
            "description": "Mark a gate as passed with optional evidence/output refs.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "gate_id": {"type": "string"},
                    "evidence_ids": {"type": "array", "items": {"type": "string"}},
                    "output_ref": {"type": "string"},
                },
                "required": ["gate_id"],
            },
        },
        {
            "name": "valo.list_gates",
            "description": "List gates for a plan.",
            "inputSchema": {
                "type": "object",
                "properties": {"plan_id": {"type": "string"}},
                "required": ["plan_id"],
            },
        },
        {
            "name": "valo.create_delegation",
            "description": "Delegate work to a worker agent/model for a specific gate.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string"},
                    "gate_id": {"type": "string"},
                    "actor": {"type": "string"},
                    "worker": {"type": "string"},
                    "brief": {"type": "string"},
                },
                "required": ["plan_id", "gate_id", "actor", "worker", "brief"],
            },
        },
        {
            "name": "valo.complete_delegation",
            "description": "Complete a delegation with optional result ref.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "delegation_id": {"type": "string"},
                    "result_ref": {"type": "string"},
                },
                "required": ["delegation_id"],
            },
        },
        {
            "name": "valo.add_review",
            "description": "Add a review verdict to a delegation: approve | revise | reject.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "delegation_id": {"type": "string"},
                    "reviewer": {"type": "string"},
                    "verdict": {"type": "string", "enum": ["approve", "revise", "reject"]},
                    "notes": {"type": "string"},
                },
                "required": ["delegation_id", "reviewer", "verdict"],
            },
        },
        {
            "name": "valo.create_ensemble",
            "description": "Run an N-way ensemble on a gate to surface contradictions.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "plan_id": {"type": "string"},
                    "gate_id": {"type": "string"},
                    "agents": {"type": "array", "items": {"type": "string"}},
                    "brief": {"type": "string"},
                },
                "required": ["plan_id", "gate_id", "agents", "brief"],
            },
        },
        {
            "name": "valo.complete_ensemble",
            "description": "Complete an ensemble run.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "ensemble_id": {"type": "string"},
                    "result_ref": {"type": "string"},
                },
                "required": ["ensemble_id"],
            },
        },
        {
            "name": "valo.add_contradiction",
            "description": "Record a contradiction found between two agents in an ensemble.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "ensemble_id": {"type": "string"},
                    "agent_a": {"type": "string"},
                    "agent_b": {"type": "string"},
                    "topic": {"type": "string"},
                },
                "required": ["ensemble_id", "agent_a", "agent_b", "topic"],
            },
        },
        {
            "name": "valo.resolve_contradiction",
            "description": "Resolve a contradiction: accepted | ignored | pending.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "contradiction_id": {"type": "string"},
                    "resolution": {"type": "string", "enum": ["accepted", "ignored", "pending"]},
                },
                "required": ["contradiction_id", "resolution"],
            },
        },
    ])

    tool_map: dict[str, Any] = {
        "valo.add_evidence": lambda args: broker.add_evidence(args["source"], args["content"]).to_dict(),
        "valo.list_evidence": lambda args: broker.list_evidence(int(args.get("limit", 20))),
        "valo.seal_envelope": lambda args: broker.seal_envelope(
            ActionEnvelope(
                actor=args["actor"],
                intent=args["intent"],
                evidence_ids=[str(x) for x in args["evidence_ids"]],
                tool=args["tool"],
                params=dict(args.get("params") or {}),
            )
        ).to_dict(),
        "valo.record_receipt": lambda args: broker.record_receipt(
            args["envelope_id"], args["status"], args.get("result_hash")
        ),
        "valo.audit_trail": lambda args: broker.audit_trail(int(args.get("limit", 20))),
        # Parable workflow
        "valo.create_plan": lambda args: broker.create_plan(args["actor"], args["intent"], [str(x) for x in args["evidence_ids"]]).to_dict(),
        "valo.approve_plan": lambda args: {"ok": broker.approve_plan is not None and (broker.approve_plan(args["plan_id"]), True)[1]},
        "valo.list_plans": lambda args: broker.list_plans(int(args.get("limit", 20))),
        "valo.add_gate": lambda args: broker.add_gate(
            args["plan_id"], args["name"], args["check_type"], bool(args.get("required", True))
        ).to_dict(),
        "valo.pass_gate": lambda args: (broker.pass_gate(
            args["gate_id"],
            [str(x) for x in (args.get("evidence_ids") or [])],
            args.get("output_ref"),
        ), {"ok": True})[1],
        "valo.list_gates": lambda args: broker.list_gates(args["plan_id"]),
        "valo.create_delegation": lambda args: broker.create_delegation(
            args["plan_id"], args["gate_id"], args["actor"], args["worker"], args["brief"]
        ).to_dict(),
        "valo.complete_delegation": lambda args: (broker.complete_delegation(
            args["delegation_id"], args.get("result_ref")
        ), {"ok": True})[1],
        "valo.add_review": lambda args: broker.add_review(
            args["delegation_id"], args["reviewer"], args["verdict"], args.get("notes")
        ).to_dict(),
        "valo.create_ensemble": lambda args: broker.create_ensemble(
            args["plan_id"], args["gate_id"], [str(x) for x in args["agents"]], args["brief"]
        ).to_dict(),
        "valo.complete_ensemble": lambda args: (broker.complete_ensemble(
            args["ensemble_id"], args.get("result_ref")
        ), {"ok": True})[1],
        "valo.add_contradiction": lambda args: broker.add_contradiction(
            args["ensemble_id"], args["agent_a"], args["agent_b"], args["topic"]
        ).to_dict(),
        "valo.resolve_contradiction": lambda args: (broker.resolve_contradiction(
            args["contradiction_id"], args["resolution"]
        ), {"ok": True})[1],
    }

    class _Server:
        def run(self) -> int:
            log.info("MCP stdio server started")
            init = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "valo-mcp", "version": "0.1.0"},
                },
            }
            sys.stdout.write(json.dumps(init) + "\n")
            sys.stdout.flush()

            while True:
                line = sys.stdin.readline()
                if not line:
                    break
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                response = self._handle(msg)
                if response is not None:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
            return 0

        def _handle(self, msg: dict[str, Any]) -> dict[str, Any] | None:
            req_id = msg.get("id")
            method = msg.get("method")
            params = msg.get("params") or {}

            if method == "initialize":
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {"listChanged": False}},
                        "serverInfo": {"name": "valo-mcp", "version": "0.1.0"},
                    },
                }

            if method == "tools/list":
                return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}}

            if method == "tools/call":
                name = params.get("name")
                arguments = params.get("arguments") or {}
                if name not in tool_map:
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32601, "message": f"Unknown tool: {name}"},
                    }
                try:
                    result = tool_map[name](arguments)
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": json.dumps(result)}],
                            "isError": False,
                        },
                    }
                except Exception as exc:  # pragma: no cover
                    log.exception("tool failed")
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": str(exc)}],
                            "isError": True,
                        },
                    }

            # notifications / unknown
            return None

    return _Server()
