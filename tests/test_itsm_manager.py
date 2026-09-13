"""Tests for ITSM Manager and Operator."""

import pytest
from datetime import datetime, timezone

from src.valo_platform.itsm_manager import (
    ITSMManager,
    ITSMOperator,
    Procedure,
    ProcedureStatus,
    WebhookEventType,
)


class TestITSMManager:
    """Tests for ITSMManager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ITSMManager()

    def test_import_procedure(self):
        """Test importing a procedure from ITSM."""
        proc_data = {
            "id": "proc-001",
            "title": "Supplier Payment Approval",
            "version": "1.0.0",
            "domain": "PAYMENT",
            "owner_role": "manager",
            "status": "active",
            "created_date": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "last_modified": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "approval_hierarchy": {"manager": 2, "director": 3},
            "regulatory_references": ["EU AI Act Article 14", "GDPR"],
            "steps": [
                {"step": 1, "action": "collect_evidence"},
                {"step": 2, "action": "validate_authority"},
            ],
            "business_impact": "Controls supplier payment fraud risk",
            "itsm_link": "https://itsm.example.com/proc-001",
        }

        procedure = self.manager.import_procedure(proc_data)

        assert procedure.procedure_id == "proc-001"
        assert procedure.title == "Supplier Payment Approval"
        assert procedure.domain == "PAYMENT"
        assert procedure.status == ProcedureStatus.ACTIVE
        assert len(procedure.regulatory_references) == 2

    def test_list_procedures_all(self):
        """Test listing all procedures."""
        self.manager.import_procedure({
            "id": "proc-001",
            "title": "Payment",
            "domain": "PAYMENT",
            "status": "active",
        })
        self.manager.import_procedure({
            "id": "proc-002",
            "title": "Data Access",
            "domain": "DATA",
            "status": "active",
        })

        procedures = self.manager.list_procedures()
        assert len(procedures) == 2

    def test_list_procedures_by_domain(self):
        """Test filtering procedures by domain."""
        self.manager.import_procedure({
            "id": "proc-001",
            "domain": "PAYMENT",
            "status": "active",
        })
        self.manager.import_procedure({
            "id": "proc-002",
            "domain": "DATA",
            "status": "active",
        })

        payment_procs = self.manager.list_procedures(domain="PAYMENT")
        assert len(payment_procs) == 1
        assert payment_procs[0].procedure_id == "proc-001"

    def test_handle_webhook_procedure_created(self):
        """Test handling webhook for procedure creation."""
        webhook_data = {
            "event_type": "procedure.created",
            "source": "jira",
            "source_id": "PROC-123",
            "procedure": {
                "id": "proc-new",
                "title": "New Procedure",
                "domain": "SECURITY",
                "status": "draft",
            },
        }

        webhook_id = self.manager.handle_webhook(webhook_data)

        assert webhook_id is not None
        assert "proc-new" in self.manager.procedures
        assert self.manager.procedures["proc-new"].status == ProcedureStatus.DRAFT

    def test_record_enforcement(self):
        """Test recording enforcement outcome."""
        self.manager.import_procedure({
            "id": "proc-001",
            "title": "Payment",
            "domain": "PAYMENT",
        })

        execution_id = self.manager.record_enforcement(
            procedure_id="proc-001",
            execution_id="exec-123",
            decision="allow",
            authority_level=2,
            confidence=0.95,
            evidence_count=4,
            risk_score=30.0,
        )

        assert execution_id == "exec-123"
        assert len(self.manager.enforcement_logs) == 1

    def test_get_enforcement_history(self):
        """Test retrieving enforcement history for a procedure."""
        self.manager.import_procedure({
            "id": "proc-001",
            "title": "Payment",
        })

        # Record multiple enforcement outcomes
        for i in range(3):
            self.manager.record_enforcement(
                procedure_id="proc-001",
                execution_id=f"exec-{i}",
                decision="allow",
                authority_level=2,
                confidence=0.95,
                evidence_count=4,
                risk_score=30.0,
            )

        history = self.manager.get_enforcement_history("proc-001")
        assert len(history) == 3

    def test_get_compliance_report(self):
        """Test generating compliance report."""
        self.manager.import_procedure({
            "id": "proc-001",
            "title": "Payment",
            "regulatory_references": ["EU AI Act"],
            "status": "active",
        })
        self.manager.import_procedure({
            "id": "proc-002",
            "title": "Data",
            "regulatory_references": ["GDPR"],
            "status": "active",
        })

        # Record some enforcement outcomes
        self.manager.record_enforcement(
            procedure_id="proc-001",
            execution_id="exec-1",
            decision="allow",
            authority_level=2,
            confidence=0.95,
            evidence_count=4,
            risk_score=30.0,
        )

        report = self.manager.get_compliance_report()

        assert report["total_procedures"] == 2
        assert report["active_procedures"] == 2
        assert report["total_enforcements"] == 1
        assert report["decision_breakdown"]["allowed"] == 1
        assert "EU AI Act" in report["regulatory_coverage"]
        assert "GDPR" in report["regulatory_coverage"]


class TestITSMOperator:
    """Tests for ITSMOperator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ITSMManager()
        self.operator = ITSMOperator(self.manager)

    def test_subscribe_to_webhooks(self):
        """Test subscribing to webhook events."""
        sub_id = self.operator.subscribe_to_webhooks(
            "https://valo.example.com/webhooks"
        )

        assert sub_id is not None
        assert len(self.operator.webhook_subscriptions) == 1

    def test_sync_procedures_from_itsm(self):
        """Test bulk importing procedures."""
        procedures = [
            {"id": "proc-001", "title": "Payment", "domain": "PAYMENT", "status": "active"},
            {"id": "proc-002", "title": "Data", "domain": "DATA", "status": "active"},
        ]

        count = self.operator.sync_procedures_from_itsm(procedures)

        assert count == 2
        assert len(self.manager.procedures) == 2

    def test_report_enforcement_to_itsm(self):
        """Test reporting enforcement outcome to ITSM."""
        self.manager.import_procedure({
            "id": "proc-001",
            "title": "Payment",
            "domain": "PAYMENT",
        })

        outcome = {
            "decision": "allow",
            "authority_level": 2,
            "confidence": 0.95,
            "evidence_count": 4,
            "risk_score": 30.0,
        }

        exec_id = self.operator.report_enforcement_to_itsm(
            procedure_id="proc-001",
            execution_id="exec-456",
            outcome=outcome,
        )

        assert exec_id == "exec-456"
        assert len(self.manager.enforcement_logs) == 1

    def test_get_sync_status(self):
        """Test getting synchronization status."""
        self.operator.subscribe_to_webhooks("https://valo.example.com/webhooks")
        procedures = [
            {"id": "proc-001", "title": "Payment", "domain": "PAYMENT", "status": "active"},
        ]
        self.operator.sync_procedures_from_itsm(procedures)

        status = self.operator.get_sync_status()

        assert status["webhook_subscriptions"] == 1
        assert status["procedures_synced"] == 1
        assert status["active_procedures"] == 1

    def test_full_itsm_workflow(self):
        """Test complete ITSM workflow: subscribe → sync → enforce → report."""
        # 1. Subscribe to webhooks
        self.operator.subscribe_to_webhooks("https://valo.example.com/webhooks")

        # 2. Sync procedures from ITSM
        procedures = [
            {
                "id": "proc-supplier-payment",
                "title": "Supplier Payment Approval",
                "domain": "PAYMENT",
                "status": "active",
                "regulatory_references": ["GDPR", "EU AI Act"],
            }
        ]
        count = self.operator.sync_procedures_from_itsm(procedures)
        assert count == 1

        # 3. Record enforcement outcome
        outcome = {
            "decision": "allow",
            "authority_level": 2,
            "confidence": 0.95,
            "evidence_count": 4,
            "risk_score": 30.0,
        }
        exec_id = self.operator.report_enforcement_to_itsm(
            procedure_id="proc-supplier-payment",
            execution_id="exec-001",
            outcome=outcome,
        )
        assert exec_id == "exec-001"

        # 4. Check sync status
        status = self.operator.get_sync_status()
        assert status["procedures_synced"] == 1
        assert status["enforcements_logged"] == 1
        assert "GDPR" in status["regulatory_coverage"]
        assert "EU AI Act" in status["regulatory_coverage"]
