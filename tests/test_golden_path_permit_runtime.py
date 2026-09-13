"""Tests for the explicit RACS -> golden-path permit runtime."""

import sys
from pathlib import Path

_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(_ROOT / "l2-orchestrator"))

from src.auth import YubiKeyOrchestrator  # noqa: E402
from src.propagator import ContextPropagator  # noqa: E402


class FakePermitRuntime:
    def __init__(self):
        self.calls = []

    def process_permit(self, permit, trusted_issuer, now_epoch_ms=None, revocation_registry_path=None):
        call = {
            "permit": permit,
            "trusted_issuer": trusted_issuer,
            "now_epoch_ms": now_epoch_ms,
            "revocation_registry_path": revocation_registry_path,
        }
        self.calls.append(call)
        return {
            "ok": True,
            "outcome": "Executed",
            "execution_allowed": True,
            "receipt": {
                "receipt_id": "rcpt-001",
                "effector_id": "connector.erp",
                "replay_nonce": "nonce-0123456789",
                "binding_valid": True,
                "replay_free": True,
                "not_expired": True,
                "binding_digest": "sha256:binding",
            },
        }


class CapturingLogger:
    def __init__(self):
        self.events = []

    def append_event(self, role, action, metadata):
        self.events.append({
            "role": role,
            "action": action,
            "metadata": metadata,
        })
        return "event-hash"


def test_propagator_uses_permit_runtime():
    auth = YubiKeyOrchestrator()
    runtime = FakePermitRuntime()
    logger = CapturingLogger()
    propagator = ContextPropagator(
        auth_system=auth,
        logger=logger,
        bridge=None,
        permit_runtime=runtime,
    )

    result = propagator.propagate_execution_permit(
        permit={"artifact_id": "permit-1"},
        trusted_issuer={"issuer_id": "platform:test"},
        now_epoch_ms=1234567890,
        revocation_registry_path="/tmp/revocations.jsonl",
    )

    assert result["ok"] is True
    assert runtime.calls == [
        {
            "permit": {"artifact_id": "permit-1"},
            "trusted_issuer": {"issuer_id": "platform:test"},
            "now_epoch_ms": 1234567890,
            "revocation_registry_path": "/tmp/revocations.jsonl",
        }
    ]
    assert result["receipt"]["receipt_id"] == "rcpt-001"
    assert logger.events[-1]["action"] == "GOLDEN_PATH_PROCESSED"
    assert logger.events[-1]["metadata"]["receipt_id"] == "rcpt-001"
    assert logger.events[-1]["metadata"]["binding_valid"] is True
    assert logger.events[-1]["metadata"]["replay_free"] is True
