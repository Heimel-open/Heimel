"""Reference product demo: ONE Operator API drives BOTH domain flows end-to-end.

- Public flow: application -> register -> review -> decision -> notify ->
  appeal deadline -> finalize -> close
- Trades flow: workorder -> register -> schedule -> reserve -> dispatch ->
  execute -> invoice -> payment -> reconcile -> close

Both flows run through the SAME Operator API (submit + evidence) over the
frozen core + real REHT.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from valo_operator import OperatorRequest, build_public_runtime, build_trades_runtime

PUBLIC_FLOW = [
    ("valo.public.register_case", {"application": {"id": "app-1", "service_type": "PUBLIC_SERVICE_A"}}),
    ("valo.public.mark_ready_for_review", {"case": {"id": "case-1"}}),
    ("valo.public.mark_under_review", {"case": {"id": "case-1"}}),
    ("valo.public.mark_ready_for_decision", {"case": {"id": "case-1"}}),
    ("valo.public.issue_public_decision", {"context": {"case": "case-1"}}),
    ("valo.public.notify", {"notification": {"recipient": "applicant-1", "message": "decision"}}),
    ("valo.public.create_appeal_right", {"decision": {"decision_id": "d-1"}}),
    ("valo.public.finalize_case", {"case": {"id": "case-1"}}),
    ("valo.public.close_case", {"case": {"id": "case-1"}}),
]

TRADES_FLOW = [
    ("valo.trades.register_workorder", {"registration": {"id": "wo-reg-1"}}),
    ("valo.trades.schedule", {"requirement": {"service": "EV_CHARGER_INSTALLATION", "duration_minutes": 240}}),
    ("valo.trades.reserve", {"resource": {"resource_id": "worker-a", "status": "AVAILABLE"}}),
    ("valo.trades.dispatch", {"reservation": {"reservation_id": "res-wf-1", "resource_id": "worker-a"}}),
    ("valo.trades.execute_work", {"decision": {"dispatch_id": "d-1"}}),
    ("valo.trades.issue_invoice", {"completion": {"type": "installation_completed", "status": "VERIFIED"}}),
    ("valo.trades.receive_payment", {"obligation": {"invoice_id": "inv-1", "amount": "16500.00"}}),
    ("valo.trades.reconcile_payment", {"payment": {"payment_id": "pay-1", "amount": "16500.00"}}),
    ("valo.trades.close_work_order", {"verified": {"work_order_id": "workorder-1", "verified": True}}),
]


@dataclass
class FlowRun:
    pack: str
    final_state: str
    steps: list[tuple[str, str, str]] = field(default_factory=list)  # (function_id, status, decision)


def run_flow(pack: str) -> FlowRun:
    runtime = build_public_runtime() if pack == "public" else build_trades_runtime()
    flow = PUBLIC_FLOW if pack == "public" else TRADES_FLOW
    steps = []
    for index, (function_id, inputs) in enumerate(flow):
        result = runtime.submit(OperatorRequest(
            correlation_id=f"{pack}-{index}", function_id=function_id, inputs=inputs,
        ))
        steps.append((function_id, result.status, result.decision or ""))
        if result.status != "COMPLETED":
            break
    entity = "case-1" if pack == "public" else "workorder-1"
    final_state = runtime.kernel.state().entities[entity].state
    return FlowRun(pack=pack, final_state=final_state, steps=steps)
