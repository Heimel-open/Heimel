from __future__ import annotations

from examples.reference_flows import PUBLIC_FLOW, TRADES_FLOW, run_flow


def _assert_completed(run) -> None:
    assert run.final_state == "CLOSED"
    assert len(run.steps) == len(PUBLIC_FLOW if run.pack == "public" else TRADES_FLOW)
    assert all(status == "COMPLETED" for _, status, _ in run.steps)


def test_reference_demo_public_flow() -> None:
    run = run_flow("public")
    _assert_completed(run)
    assert run.steps[-1][0] == "valo.public.close_case"


def test_reference_demo_trades_flow() -> None:
    run = run_flow("trades")
    _assert_completed(run)
    assert run.steps[-1][0] == "valo.trades.close_work_order"


def test_same_operator_api_drives_both_domains() -> None:
    """The single Operator API drives both domains end-to-end to their terminal
    state."""
    _assert_completed(run_flow("public"))
    _assert_completed(run_flow("trades"))
