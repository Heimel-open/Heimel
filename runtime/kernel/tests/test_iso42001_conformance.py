from valo_kernel.iso42001_conformance import (
    ISO42001_CONTROLS,
    Verdict,
    evaluate_iso42001,
    replay,
)


def all_signals() -> set[str]:
    return {signal for spec in ISO42001_CONTROLS for signal in spec.required_signals}


def test_complete_runtime_evidence_passes_all_mapped_controls():
    receipt = evaluate_iso42001(all_signals())

    assert receipt.verdict is Verdict.PASS
    assert all(result.verdict is Verdict.PASS for result in receipt.results)
    assert len(receipt.digest) == 64


def test_missing_signal_is_insufficient_evidence_not_silent_pass():
    signals = all_signals() - {"purpose_bound"}
    receipt = evaluate_iso42001(signals)
    result = next(result for result in receipt.results if result.control == "A.9.4")

    assert result.verdict is Verdict.INSUFFICIENT_EVIDENCE
    assert result.missing == ("purpose_bound",)
    assert receipt.verdict is Verdict.INSUFFICIENT_EVIDENCE


def test_explicit_failed_runtime_signal_fails_control():
    receipt = evaluate_iso42001(all_signals(), failed={"unauthorized_use_denied"})
    result = next(result for result in receipt.results if result.control == "A.9.4")

    assert result.verdict is Verdict.FAIL
    assert receipt.verdict is Verdict.FAIL


def test_residual_evidence_is_preserved_for_partial_controls():
    receipt = evaluate_iso42001(all_signals())
    result = next(result for result in receipt.results if result.control == "A.10.2")

    assert result.verdict is Verdict.PASS
    assert result.residual_evidence
    assert "agreements among all external parties" in result.residual_evidence


def test_receipt_is_deterministic_and_replayable():
    signals = all_signals()
    first = evaluate_iso42001(signals)
    second = evaluate_iso42001(reversed(sorted(signals)))

    assert first.digest == second.digest
    assert replay(first, signals)


def test_replay_detects_changed_evidence():
    signals = all_signals()
    receipt = evaluate_iso42001(signals)

    assert not replay(receipt, signals - {"event_logging_enabled"})
