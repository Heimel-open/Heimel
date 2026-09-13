import sys
import time
import pathlib
import importlib.util
from .auth import YubiKeyOrchestrator, Role
from .golden_path import RacsGoldenPathRuntime
from .worm_log import WORMAuditLog

# Bootstrap l2_orchestrator package if not already registered
_ROOT = pathlib.Path(__file__).parents[2]
_l2_dir = _ROOT / "l2-orchestrator"
if "l2_orchestrator" not in sys.modules:
    _pkg_spec = importlib.util.spec_from_file_location(
        "l2_orchestrator", _l2_dir / "__init__.py",
        submodule_search_locations=[str(_l2_dir)],
    )
    _pkg = importlib.util.module_from_spec(_pkg_spec)
    sys.modules["l2_orchestrator"] = _pkg
    _pkg_spec.loader.exec_module(_pkg)

from l2_orchestrator import BridgeFactory
ValoBridge, Decision = BridgeFactory.load()


class ContextPropagator:
    """
    Bridge between L2 Orchestration and L1 execution.
    All state changes are authorized, sent to L1 via TCP, and logged before returning.
    """
    def __init__(
        self,
        auth_system: YubiKeyOrchestrator,
        logger: WORMAuditLog,
        bridge: ValoBridge,
        permit_runtime: RacsGoldenPathRuntime | None = None,
    ):
        self.auth = auth_system
        self.logger = logger
        self.bridge = bridge
        self.permit_runtime = permit_runtime or RacsGoldenPathRuntime()
        self.last_propagation_ts = 0

    def propagate_manual_override(self, new_spread_limit: float, reason: str):
        print(f"[PROPAGATOR] Attempting manual override: {new_spread_limit}")

        if not self.auth.check_integrity() or self.auth.session.role != Role.MANAGER:
            error_msg = "Unauthorized: Manual override requires 2-person MANAGER session."
            self.logger.append_event("SYSTEM", "REJECTED_OVERRIDE", {"reason": error_msg})
            print(f"[ERROR] {error_msg}")
            return False

        metadata = {
            "new_limit": new_spread_limit,
            "reason": reason,
            "authorized_by": self.auth.session.role.name,
        }
        event_hash = self.logger.append_event("MANAGER", "MANUAL_OVERRIDE", metadata)
        self._send_to_l1(new_spread_limit, event_hash)
        self.last_propagation_ts = time.time()
        print(f"[SUCCESS] Context updated and locked with hash {event_hash[:8]}")
        return True

    def validate_and_propagate(
        self,
        val_primary: float,
        val_secondary: float,
        max_spread: float,
        identifier: int = 0,
        domain: int = 0,
    ) -> Decision:
        """Pack a frame, send to L1, log decision + RTT, return Decision."""
        frame = self.bridge.pack_valo_frame(
            val_primary, val_secondary, max_spread, identifier, domain
        )
        decision, rtt_ns = self.bridge.send_frame(frame)
        self.logger.append_event(
            "L2",
            f"DECISION_{decision.name}",
            {
                "val_primary": val_primary,
                "val_secondary": val_secondary,
                "max_spread": max_spread,
                "rtt_ns": rtt_ns,
                "identifier": identifier,
                "domain": domain,
            },
        )
        return decision

    def _send_to_l1(self, limit: float, audit_hash: str):
        frame = self.bridge.pack_valo_frame(
            val_primary=0.0,
            val_secondary=limit,
            max_spread=limit,
            fail_mode=0xDEAD,
        )
        decision, rtt_ns = self.bridge.send_frame(frame)
        self.logger.append_event(
            "L2",
            "OVERRIDE_PROPAGATED",
            {"audit_hash": audit_hash, "decision": decision.name, "rtt_ns": rtt_ns},
        )

    def propagate_execution_permit(
        self,
        permit: dict,
        trusted_issuer: dict,
        now_epoch_ms: int | None = None,
        revocation_registry_path: str | None = None,
    ):
        """
        Execute a RACS-permitted action through the golden path bridge.

        This is the explicit permit-based runtime path. It does not reuse the
        telemetry frame path.
        """
        result = self.permit_runtime.process_permit(
            permit=permit,
            trusted_issuer=trusted_issuer,
            now_epoch_ms=now_epoch_ms,
            revocation_registry_path=revocation_registry_path,
        )
        self.logger.append_event(
            "L2",
            "GOLDEN_PATH_PROCESSED",
            {
                "outcome": result.get("outcome"),
                "execution_allowed": result.get("execution_allowed"),
                "receipt_id": (result.get("receipt") or {}).get("receipt_id"),
                "effector_id": (result.get("receipt") or {}).get("effector_id"),
                "replay_nonce": (result.get("receipt") or {}).get("replay_nonce"),
                "binding_valid": (result.get("receipt") or {}).get("binding_valid"),
                "replay_free": (result.get("receipt") or {}).get("replay_free"),
                "not_expired": (result.get("receipt") or {}).get("not_expired"),
                "binding_digest": (result.get("receipt") or {}).get("binding_digest"),
            },
        )
        return result
