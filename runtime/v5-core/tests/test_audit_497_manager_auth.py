"""Manager-auth enforcement tests for the L2 orchestrator."""

import sys
import tempfile
import time
from pathlib import Path

import pytest

_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(_ROOT / "l2-orchestrator"))

from src.auth import AuthSession, Role, YubiKeyOrchestrator  # noqa: E402
from src.propagator import ContextPropagator  # noqa: E402
from src.worm_log import WORMAuditLog  # noqa: E402


class FakeDecision:
    name = "ALLOW"


class FakeBridge:
    """Minimal ValoBridge stand-in."""

    def __init__(self):
        self.frames = []

    def pack_valo_frame(
        self,
        val_primary=0.0,
        val_secondary=0.0,
        max_spread=0.0,
        identifier=0,
        domain=0,
        fail_mode=0,
        timestamp_ns=0,
        **kwargs,
    ):
        self.frames.append((val_primary, val_secondary, max_spread, fail_mode))
        return b"\x00" * 64

    def send_frame(self, frame):
        return FakeDecision(), 1000


@pytest.fixture
def logger():
    return WORMAuditLog(log_dir=tempfile.mkdtemp(prefix="valo_audit_"))


@pytest.fixture
def orchestrator():
    return YubiKeyOrchestrator()


@pytest.fixture
def propagator(orchestrator, logger):
    return ContextPropagator(auth_system=orchestrator, logger=logger, bridge=FakeBridge())


def _valid_manager_session(orchestrator):
    orchestrator.initiate_handshake(Role.MANAGER, ["SER-VALO-001", "SER-VALO-002"])
    return orchestrator.session


def test_manager_handshake_requires_two_distinct_authorized_keys(orchestrator):
    orchestrator.initiate_handshake(Role.MANAGER)
    assert orchestrator.session is not None
    assert orchestrator.session.is_active is False
    assert orchestrator.check_integrity() is False

    orchestrator.initiate_handshake(Role.MANAGER, ["SER-VALO-001", "SER-VALO-001"])
    assert orchestrator.session is not None
    assert orchestrator.session.tokens_validated == 1
    assert orchestrator.session.is_active is False
    assert orchestrator.check_integrity() is False

    _valid_manager_session(orchestrator)
    assert orchestrator.session is not None
    assert orchestrator.session.tokens_validated == 2
    assert orchestrator.session.is_active is True
    assert len(orchestrator.session.token_ids) == 2
    assert orchestrator.check_integrity() is True
    assert orchestrator.check_integrity() is False


def test_manager_handshake_rejects_revoked_or_expired_sessions(orchestrator):
    orchestrator.revoked_keys.add("SER-VALO-002")
    orchestrator.initiate_handshake(Role.MANAGER, ["SER-VALO-001", "SER-VALO-002"])
    assert orchestrator.session is not None
    assert orchestrator.session.is_active is False
    assert orchestrator.session.tokens_validated == 1
    assert orchestrator.check_integrity() is False

    _valid_manager_session(orchestrator)
    assert orchestrator.session is not None
    orchestrator.session.expires_at = time.time() - 1
    assert orchestrator.check_integrity() is False


def test_manager_session_rejects_manual_construction(orchestrator):
    orchestrator.session = AuthSession(
        role=Role.MANAGER,
        tokens_validated=2,
        start_time=time.time(),
        is_active=True,
        token_ids=("SER-VALO-001", "SER-VALO-002"),
        expires_at=time.time() + 300,
        nonce="forged-nonce",
        session_proof="forged-proof",
    )
    assert orchestrator.check_integrity() is False


def test_manual_override_requires_valid_manager_session(orchestrator, propagator):
    orchestrator.initiate_handshake(Role.MANAGER)
    assert propagator.propagate_manual_override(new_spread_limit=2.0, reason="audit") is False

    _valid_manager_session(orchestrator)
    assert propagator.propagate_manual_override(new_spread_limit=2.0, reason="audit") is True
    assert propagator.propagate_manual_override(new_spread_limit=3.0, reason="replay") is False


def test_operator_handshake_remains_active_but_sealed(orchestrator):
    orchestrator.initiate_handshake(Role.OPERATOR)
    assert orchestrator.session is not None
    assert orchestrator.session.is_active is True
    assert orchestrator.session.token_ids == ("OPERATOR_PIN",)
    assert orchestrator.check_integrity() is True
    assert orchestrator.check_integrity() is False


def test_step7_runtime_entrypoints():
    import subprocess

    root = _ROOT
    out = subprocess.run(
        [
            "grep",
            "-rln",
            "-E",
            r"from \.?auth import|import auth|from \.?propagator import|import propagator",
            str(root / "l2-orchestrator"),
            str(root / "sidecar"),
            str(root / "demo-server"),
            str(root / "mcp_server.py"),
            str(root / "janus_integration.py"),
        ],
        capture_output=True,
        text=True,
    ).stdout.strip().splitlines()
    print(f"[OBSERVED] entrypoints importing auth/propagator: {out}")
    assert out, "expected at least one runtime entrypoint"
