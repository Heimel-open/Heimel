"""Integration test: WORM log + RRP receipt in the same flow (VAIG #73)."""
from vaig.worm import WORMLog
from vaig.rrp.receipt import ReceiptFactory


def _make_receipt(outcome="EXECUTED", refusal_id=None, uncertainty_inventory_id=None):
    return ReceiptFactory.create(
        receipt_id="rcpt-001",
        evidence_condition_id="ec-001",
        evidence_condition_snapshot={"state": "VALIDATED"},
        intent_id="intent-001",
        intent_snapshot={"action": "query_database", "scope": "read_only"},
        vaig_outcome=outcome,
        vaig_rule_triggered=None if outcome == "EXECUTED" else "DENY_HIGH_RISK",
        vaig_rationale=None if outcome == "EXECUTED" else "Risk exceeds policy threshold",
        accountability_thread_id="thread-001",
        thread_snapshot={"agent": "test-agent"},
        refusal_id=refusal_id,
        uncertainty_inventory_id=uncertainty_inventory_id,
        final_status=outcome,
    )


class TestWormRrpIntegration:
    def test_execute_receipt_appended_and_chain_valid(self, tmp_path):
        worm = WORMLog(str(tmp_path / "audit.jsonl"))
        receipt = _make_receipt(outcome="EXECUTED")
        worm.append("rcpt-001", receipt.to_dict())
        assert worm.verify()

    def test_refusal_receipt_fields_in_worm(self, tmp_path):
        worm = WORMLog(str(tmp_path / "audit.jsonl"))
        receipt = _make_receipt(
            outcome="REFUSED",
            refusal_id="ref-001",
            uncertainty_inventory_id="unc-001",
        )
        worm.append("rcpt-001", receipt.to_dict())
        assert worm.verify()
        entries = worm.read_all()
        assert len(entries) == 1
        assert entries[0]["refusal_id"] == "ref-001"
        assert entries[0]["uncertainty_inventory_id"] == "unc-001"

    def test_multi_receipt_chain_valid(self, tmp_path):
        worm = WORMLog(str(tmp_path / "audit.jsonl"))
        worm.append("rcpt-001", _make_receipt(outcome="EXECUTED").to_dict())
        worm.append("rcpt-002", _make_receipt(outcome="REFUSED", refusal_id="ref-002").to_dict())
        assert worm.verify()
        assert len(worm.read_all()) == 2

    def test_tamper_detection_on_receipt_entry(self, tmp_path):
        log_path = tmp_path / "audit.jsonl"
        worm = WORMLog(str(log_path))
        worm.append("rcpt-001", _make_receipt().to_dict())
        assert worm.verify()

        tampered = log_path.read_text().replace('"EXECUTED"', '"ALLOW"', 1)
        log_path.write_text(tampered)

        assert not WORMLog(str(log_path)).verify()

    def test_receipt_fields_preserved_end_to_end(self, tmp_path):
        worm = WORMLog(str(tmp_path / "audit.jsonl"))
        worm.append(
            "rcpt-e2e",
            _make_receipt(
                outcome="REFUSED",
                refusal_id="ref-xyz",
                uncertainty_inventory_id="unc-xyz",
            ).to_dict(),
        )
        entry = worm.read_all()[0]
        assert entry["vaig_outcome"] == "REFUSED"
        assert entry["refusal_id"] == "ref-xyz"
        assert entry["uncertainty_inventory_id"] == "unc-xyz"
        assert entry["evidence_condition_id"] == "ec-001"
