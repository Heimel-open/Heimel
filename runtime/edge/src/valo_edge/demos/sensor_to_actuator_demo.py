"""End-to-end sensor-to-safe-actuator demonstration for Tiny Edge profile."""

from datetime import datetime, timezone
import json
from valo_edge.adapters import SensorAdapter
from valo_edge.contracts import OfflineAuthorityEnvelope, EdgeDecision
from valo_edge.runtime import MicroRehtEngine
from valo_edge.gateway import HardwareNeutralGateway


def run_demo() -> bool:
    device_id = "device-industrial-pump-01"
    now_iso = "2026-08-04T12:00:00Z"
    future_expiry_iso = "2026-08-05T12:00:00Z"

    # 1. Initialize micro-REHT engine and hardware gateway
    engine = MicroRehtEngine()
    gateway = HardwareNeutralGateway()

    # 2. Issue valid offline authority envelope
    envelope = OfflineAuthorityEnvelope(
        envelope_id="env-pump-safe-01",
        device_id=device_id,
        allowed_action_types=["ADJUST_FLOW_RATE", "EMERGENCY_SHUTDOWN"],
        max_rate_per_sec=5.0,
        valid_until_iso=future_expiry_iso,
    )

    # 3. Create sensor proposal via adapter
    sensor = SensorAdapter(device_id=device_id)
    proposal = sensor.create_proposal(
        action_type="ADJUST_FLOW_RATE",
        parameters={"flow_rate_lpm": 150},
        timestamp_iso=now_iso,
    )

    # 4. Evaluate proposal via micro-REHT
    clearance = engine.evaluate_proposal(proposal, envelope, current_time_iso=now_iso)
    print(f"[DEMO] Clearance Decision: {clearance.decision.value} - Reason: {clearance.reason}")

    # 5. Enforce action via hardware-neutral gateway
    receipt = gateway.execute_action(proposal, clearance, timestamp_iso=now_iso)
    print(f"[DEMO] Receipt Executed: {receipt.executed} - Digest: {receipt.receipt_digest}")

    return receipt.executed and receipt.decision == EdgeDecision.ALLOW


if __name__ == "__main__":
    success = run_demo()
    print(f"[DEMO] Demo completion status: {'SUCCESS' if success else 'FAILED'}")
