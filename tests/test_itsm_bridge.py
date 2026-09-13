"""Tests for Phase 19: ITSM Integration Bridge."""

import pytest
from datetime import datetime, timezone
from src.valo_platform.itsm_bridge import (
    ITSMBridge,
    ProcedureEvent,
    ITSMSystem,
    ProcedureEventType,
    EnforcementOutcome,
)
from src.valo_platform.procedure_translator import (
    ProcedureDomain,
    RiskTier,
)


class TestITSMBridge:
    """Test ITSM bridge integration."""

    def setup_method(self):
        """Setup for each test."""
        self.bridge = ITSMBridge()

    def _create_procedure_event(
        self,
        procedure_id: str = "proc-ai-001",
        event_type: ProcedureEventType = ProcedureEventType.CREATED,
        source_system: ITSMSystem = ITSMSystem.JIRA,
    ) -> ProcedureEvent:
        """Create sample procedure event."""
        return ProcedureEvent(
            event_id=f"event-{procedure_id}",
            event_type=event_type,
            source_system=source_system,

            procedure_id=procedure_id,
            procedure_version="1.0",
            title="AI Model Access Procedure",

            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
            actor="alice@example.com",
            actor_role="compliance",

            payload={
                "procedure_id": procedure_id,
                "title": "AI Model Access Procedure",
                "version": "1.0",
                "domain": ProcedureDomain.AI_MODEL_ACCESS.value,
                "owner": "alice@example.com",
                "owner_role": "compliance",
                "risk_tier": RiskTier.CRITICAL.value,
                "description": "Procedure for granting access",
                "steps": [
                    {
                        "step_id": "step-1",
                        "order": 1,
                        "description": "Request access",
                        "required_role": "user",
                    },
                    {
                        "step_id": "step-2",
                        "order": 2,
                        "description": "Manager approval",
                        "required_role": "manager",
                        "approval_required": True,
                    },
                ],
                "approval_hierarchy": [
                    {
                        "level": 1,
                        "role": "manager",
                        "authority_scope": ["ai_access_basic"],
                    },
                ],
                "regulatory_references": [
                    {
                        "framework": "EU AI Act",
                        "article_or_section": "Article 14",
                        "requirement": "Human oversight",
                    },
                ],
            }
        )

    def test_bridge_initialization(self):
        """Test bridge initialization."""
        assert self.bridge is not None
        assert self.bridge.contract_registry == {}
        assert self.bridge.enforcement_log == []

    def test_handle_procedure_created_event(self):
        """Test handling procedure created event."""
        event = self._create_procedure_event(event_type=ProcedureEventType.CREATED)
        mapping = self.bridge.handle_procedure_event(event)

        assert mapping is not None
        assert mapping.source_procedure_id == "proc-ai-001"
        assert mapping.risk_class == "CRITICAL"

    def test_handle_procedure_updated_event(self):
        """Test handling procedure updated event."""
        event = self._create_procedure_event(event_type=ProcedureEventType.UPDATED)
        mapping = self.bridge.handle_procedure_event(event)

        assert mapping is not None
        assert event.event_type == ProcedureEventType.UPDATED

    def test_contract_registration(self):
        """Test contract is registered after event."""
        event = self._create_procedure_event()
        mapping = self.bridge.handle_procedure_event(event)

        assert mapping.contract_id in self.bridge.contract_registry
        assert self.bridge.contract_registry[mapping.contract_id] == mapping

    def test_get_contract_by_procedure(self):
        """Test retrieving contract by procedure ID."""
        event = self._create_procedure_event()
        mapping = self.bridge.handle_procedure_event(event)

        retrieved = self.bridge.get_contract_by_procedure("proc-ai-001")
        assert retrieved is not None
        assert retrieved.source_procedure_id == "proc-ai-001"

    def test_log_enforcement(self):
        """Test enforcement logging."""
        event = self._create_procedure_event()
        mapping = self.bridge.handle_procedure_event(event)

        log = self.bridge.log_enforcement(
            contract_id=mapping.contract_id,
            action_id="action-001",
            decision="ALLOWED",
            decision_reason="User has required authority and evidence valid",
            actor="bob@example.com",
            context={"user_role": "researcher", "department": "research"},
        )

        assert log is not None
        assert log.decision == "ALLOWED"
        assert log.action_id == "action-001"

    def test_enforcement_history(self):
        """Test enforcement history retrieval."""
        event = self._create_procedure_event()
        mapping = self.bridge.handle_procedure_event(event)

        # Log multiple enforcements
        for i in range(3):
            self.bridge.log_enforcement(
                contract_id=mapping.contract_id,
                action_id=f"action-{i}",
                decision="ALLOWED",
                decision_reason=f"Decision {i}",
                actor=f"user{i}@example.com",
                context={"index": i},
            )

        history = self.bridge.get_enforcement_history("proc-ai-001")
        assert len(history) == 3

    def test_compliance_status(self):
        """Test compliance status check."""
        event = self._create_procedure_event()
        mapping = self.bridge.handle_procedure_event(event)

        # Log allowed decisions
        for i in range(2):
            self.bridge.log_enforcement(
                contract_id=mapping.contract_id,
                action_id=f"action-allow-{i}",
                decision="ALLOWED",
                decision_reason="Approved",
                actor="user@example.com",
                context={},
            )

        status = self.bridge.check_compliance_status("proc-ai-001")

        assert status["procedure_id"] == "proc-ai-001"
        assert status["total_enforcements"] == 2
        assert status["allowed"] == 2
        assert status["compliance_rate"] == 1.0
        assert status["status"] == "compliant"

    def test_compliance_status_with_denials(self):
        """Test compliance status with some denials."""
        event = self._create_procedure_event()
        mapping = self.bridge.handle_procedure_event(event)

        # Log mixed decisions
        self.bridge.log_enforcement(
            contract_id=mapping.contract_id,
            action_id="action-1",
            decision="ALLOWED",
            decision_reason="Approved",
            actor="user@example.com",
            context={},
        )

        self.bridge.log_enforcement(
            contract_id=mapping.contract_id,
            action_id="action-2",
            decision="DENIED",
            decision_reason="Insufficient authority",
            actor="user@example.com",
            context={},
        )

        status = self.bridge.check_compliance_status("proc-ai-001")

        assert status["total_enforcements"] == 2
        assert status["allowed"] == 1
        assert status["denied"] == 1
        # Denials reduce compliance rate
        assert status["compliance_rate"] < 1.0

    def test_compliance_status_unknown_procedure(self):
        """Test compliance status for unknown procedure."""
        status = self.bridge.check_compliance_status("unknown-proc")

        assert status["status"] == "unknown"
        assert status["reason"] == "procedure_not_found"

    def test_multiple_procedures(self):
        """Test handling multiple procedures."""
        event1 = self._create_procedure_event(procedure_id="proc-1")
        event2 = self._create_procedure_event(procedure_id="proc-2")

        mapping1 = self.bridge.handle_procedure_event(event1)
        mapping2 = self.bridge.handle_procedure_event(event2)

        assert mapping1.source_procedure_id == "proc-1"
        assert mapping2.source_procedure_id == "proc-2"
        assert len(self.bridge.contract_registry) == 2

    def test_different_itsm_systems(self):
        """Test handling procedures from different ITSM systems."""
        jira_event = self._create_procedure_event(source_system=ITSMSystem.JIRA)
        servicenow_event = self._create_procedure_event(
            procedure_id="proc-2",
            source_system=ITSMSystem.SERVICENOW,
        )

        mapping1 = self.bridge.handle_procedure_event(jira_event)
        mapping2 = self.bridge.handle_procedure_event(servicenow_event)

        assert mapping1 is not None
        assert mapping2 is not None

    def test_enforcement_log_evidence_hash(self):
        """Test enforcement log includes evidence hash."""
        event = self._create_procedure_event()
        mapping = self.bridge.handle_procedure_event(event)

        log = self.bridge.log_enforcement(
            contract_id=mapping.contract_id,
            action_id="action-001",
            decision="ALLOWED",
            decision_reason="Approved",
            actor="user@example.com",
            context={},
        )

        assert log.evidence_hash is not None
        assert len(log.evidence_hash) == 64  # SHA-256

    def test_enforcement_log_metadata(self):
        """Test enforcement log includes procedure metadata."""
        event = self._create_procedure_event()
        mapping = self.bridge.handle_procedure_event(event)

        log = self.bridge.log_enforcement(
            contract_id=mapping.contract_id,
            action_id="action-001",
            decision="ALLOWED",
            decision_reason="Approved",
            actor="user@example.com",
            context={},
        )

        assert "procedure_version" in log.metadata
        assert "procedure_snapshot_hash" in log.metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
