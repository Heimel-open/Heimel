"""Tests for ITSM system connectors."""

import pytest
from datetime import datetime, timezone
from src.valo_platform.itsm import (
    ITSMProcedure,
    JiraConnector,
    ServiceNowConnector,
    ITSMConnectorFactory,
    ITSMEventType,
)


@pytest.fixture
def jira_connector():
    """Create a Jira connector for testing."""
    return JiraConnector(
        instance_url="https://company.atlassian.net",
        api_token="test-api-token",
        email="user@company.com",
    )


@pytest.fixture
def servicenow_connector():
    """Create a ServiceNow connector for testing."""
    return ServiceNowConnector(
        instance_url="https://dev12345.service-now.com",
        client_id="test-client-id",
        client_secret="test-client-secret",
    )


@pytest.fixture
def sample_procedure():
    """Create a sample procedure for testing."""
    return ITSMProcedure(
        procedure_id="proc-test-001",
        title="AI Model Access Control",
        description="Procedure for granting access to high-risk AI models",
        owner="security-team",
        owner_email="security@company.com",
        version=1,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        status="active",
        source_system="jira",
        source_id="PROC-1",
        custom_fields={"risk_level": "high", "compliance_framework": "eu_ai_act"},
    )


class TestJiraConnectorAuth:
    """Tests for Jira connector authentication."""

    def test_authenticate_success(self, jira_connector):
        """Test successful Jira authentication."""
        result = jira_connector.authenticate()
        assert result is True
        assert jira_connector.authenticated is True

    def test_authenticate_with_missing_token(self):
        """Test authentication fails with missing API token."""
        connector = JiraConnector(
            instance_url="https://company.atlassian.net",
            api_token="",  # Missing
            email="user@company.com",
        )
        result = connector.authenticate()
        assert result is False

    def test_authenticate_with_missing_email(self):
        """Test authentication fails with missing email."""
        connector = JiraConnector(
            instance_url="https://company.atlassian.net",
            api_token="test-token",
            email="",  # Missing
        )
        result = connector.authenticate()
        assert result is False

    def test_authenticate_with_missing_instance_url(self):
        """Test authentication fails with missing instance URL."""
        connector = JiraConnector(
            instance_url="",  # Missing
            api_token="test-token",
            email="user@company.com",
        )
        result = connector.authenticate()
        assert result is False


class TestJiraProcedureCRUD:
    """Tests for Jira procedure CRUD operations."""

    def test_create_procedure(self, jira_connector, sample_procedure):
        """Test creating a procedure in Jira."""
        jira_connector.authenticate()
        result = jira_connector.create_procedure(sample_procedure)

        assert result is not None
        assert result.procedure_id == sample_procedure.procedure_id
        assert result.source_system == "jira"
        assert "PROC-" in result.source_id  # Jira issue key format

    def test_get_procedure(self, jira_connector, sample_procedure):
        """Test retrieving a procedure from Jira."""
        jira_connector.authenticate()
        jira_connector.create_procedure(sample_procedure)

        retrieved = jira_connector.get_procedure(sample_procedure.procedure_id)
        assert retrieved is not None
        assert retrieved.title == sample_procedure.title
        assert retrieved.owner == sample_procedure.owner

    def test_get_nonexistent_procedure(self, jira_connector):
        """Test retrieving a nonexistent procedure."""
        jira_connector.authenticate()
        result = jira_connector.get_procedure("nonexistent-id")
        assert result is None

    def test_update_procedure(self, jira_connector, sample_procedure):
        """Test updating a procedure in Jira."""
        jira_connector.authenticate()
        jira_connector.create_procedure(sample_procedure)

        sample_procedure.title = "Updated Title"
        result = jira_connector.update_procedure(sample_procedure)

        assert result is True

        retrieved = jira_connector.get_procedure(sample_procedure.procedure_id)
        assert retrieved.title == "Updated Title"
        assert retrieved.version == 2

    def test_update_nonexistent_procedure(self, jira_connector, sample_procedure):
        """Test updating a nonexistent procedure fails."""
        jira_connector.authenticate()
        result = jira_connector.update_procedure(sample_procedure)
        assert result is False

    def test_delete_procedure(self, jira_connector, sample_procedure):
        """Test deleting a procedure from Jira."""
        jira_connector.authenticate()
        jira_connector.create_procedure(sample_procedure)

        result = jira_connector.delete_procedure(sample_procedure.procedure_id)
        assert result is True

        retrieved = jira_connector.get_procedure(sample_procedure.procedure_id)
        assert retrieved is None

    def test_delete_nonexistent_procedure(self, jira_connector):
        """Test deleting a nonexistent procedure fails."""
        jira_connector.authenticate()
        result = jira_connector.delete_procedure("nonexistent-id")
        assert result is False


class TestJiraProcedureList:
    """Tests for listing Jira procedures."""

    def test_get_procedures_empty(self, jira_connector):
        """Test getting procedures when none exist."""
        jira_connector.authenticate()
        procedures = jira_connector.get_procedures()
        assert len(procedures) == 0

    def test_get_procedures_multiple(self, jira_connector):
        """Test getting multiple procedures."""
        jira_connector.authenticate()

        proc1 = ITSMProcedure(
            procedure_id="proc-001",
            title="Procedure 1",
            description="Description 1",
            owner="owner1",
            owner_email="owner1@company.com",
            version=1,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            status="active",
            source_system="jira",
            source_id="PROC-1",
            custom_fields={},
        )

        proc2 = ITSMProcedure(
            procedure_id="proc-002",
            title="Procedure 2",
            description="Description 2",
            owner="owner2",
            owner_email="owner2@company.com",
            version=1,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            status="active",
            source_system="jira",
            source_id="PROC-2",
            custom_fields={},
        )

        jira_connector.create_procedure(proc1)
        jira_connector.create_procedure(proc2)

        procedures = jira_connector.get_procedures()
        assert len(procedures) == 2
        assert any(p.procedure_id == "proc-001" for p in procedures)
        assert any(p.procedure_id == "proc-002" for p in procedures)

    def test_get_procedures_unauthenticated(self, jira_connector, sample_procedure):
        """Test getting procedures without authentication."""
        jira_connector.create_procedure(sample_procedure)
        procedures = jira_connector.get_procedures()
        assert len(procedures) == 0  # Should return empty without auth


class TestServiceNowConnectorAuth:
    """Tests for ServiceNow connector authentication."""

    def test_authenticate_success(self, servicenow_connector):
        """Test successful ServiceNow authentication."""
        result = servicenow_connector.authenticate()
        assert result is True
        assert servicenow_connector.authenticated is True

    def test_authenticate_with_missing_client_id(self):
        """Test authentication fails with missing client ID."""
        connector = ServiceNowConnector(
            instance_url="https://dev12345.service-now.com",
            client_id="",  # Missing
            client_secret="test-secret",
        )
        result = connector.authenticate()
        assert result is False

    def test_authenticate_with_missing_client_secret(self):
        """Test authentication fails with missing client secret."""
        connector = ServiceNowConnector(
            instance_url="https://dev12345.service-now.com",
            client_id="test-id",
            client_secret="",  # Missing
        )
        result = connector.authenticate()
        assert result is False


class TestServiceNowProcedureCRUD:
    """Tests for ServiceNow procedure CRUD operations."""

    def test_create_procedure(self, servicenow_connector, sample_procedure):
        """Test creating a procedure in ServiceNow."""
        servicenow_connector.authenticate()
        sample_procedure.source_system = "servicenow"
        result = servicenow_connector.create_procedure(sample_procedure)

        assert result is not None
        assert result.procedure_id == sample_procedure.procedure_id
        assert result.source_system == "servicenow"
        assert "CHG" in result.source_id  # ServiceNow change request format

    def test_get_procedure(self, servicenow_connector, sample_procedure):
        """Test retrieving a procedure from ServiceNow."""
        servicenow_connector.authenticate()
        sample_procedure.source_system = "servicenow"
        servicenow_connector.create_procedure(sample_procedure)

        retrieved = servicenow_connector.get_procedure(sample_procedure.procedure_id)
        assert retrieved is not None
        assert retrieved.title == sample_procedure.title

    def test_update_procedure(self, servicenow_connector, sample_procedure):
        """Test updating a procedure in ServiceNow."""
        servicenow_connector.authenticate()
        sample_procedure.source_system = "servicenow"
        servicenow_connector.create_procedure(sample_procedure)

        sample_procedure.title = "Updated Title"
        result = servicenow_connector.update_procedure(sample_procedure)

        assert result is True
        assert servicenow_connector.get_procedure(sample_procedure.procedure_id).version == 2

    def test_delete_procedure(self, servicenow_connector, sample_procedure):
        """Test deleting a procedure from ServiceNow."""
        servicenow_connector.authenticate()
        sample_procedure.source_system = "servicenow"
        servicenow_connector.create_procedure(sample_procedure)

        result = servicenow_connector.delete_procedure(sample_procedure.procedure_id)
        assert result is True

        retrieved = servicenow_connector.get_procedure(sample_procedure.procedure_id)
        assert retrieved is None


class TestITSMConnectorFactory:
    """Tests for ITSM connector factory."""

    def test_create_jira_connector(self):
        """Test creating a Jira connector via factory."""
        connector = ITSMConnectorFactory.create_connector(
            system="jira",
            instance_url="https://company.atlassian.net",
            credentials={"api_token": "token", "email": "user@company.com"},
        )

        assert isinstance(connector, JiraConnector)
        assert connector.instance_url == "https://company.atlassian.net"

    def test_create_servicenow_connector(self):
        """Test creating a ServiceNow connector via factory."""
        connector = ITSMConnectorFactory.create_connector(
            system="servicenow",
            instance_url="https://dev12345.service-now.com",
            credentials={"client_id": "id", "client_secret": "secret"},
        )

        assert isinstance(connector, ServiceNowConnector)
        assert connector.instance_url == "https://dev12345.service-now.com"

    def test_create_unsupported_connector(self):
        """Test that creating unsupported connector raises error."""
        with pytest.raises(ValueError):
            ITSMConnectorFactory.create_connector(
                system="unsupported",
                instance_url="https://example.com",
                credentials={},
            )

    def test_factory_case_insensitive(self):
        """Test factory is case-insensitive for system names."""
        connector = ITSMConnectorFactory.create_connector(
            system="JIRA",
            instance_url="https://company.atlassian.net",
            credentials={"api_token": "token", "email": "user@company.com"},
        )

        assert isinstance(connector, JiraConnector)


class TestITSMProcedureModel:
    """Tests for ITSMProcedure data model."""

    def test_procedure_to_dict(self, sample_procedure):
        """Test converting procedure to dictionary."""
        proc_dict = sample_procedure.to_dict()

        assert proc_dict["procedure_id"] == "proc-test-001"
        assert proc_dict["title"] == "AI Model Access Control"
        assert proc_dict["owner"] == "security-team"
        assert proc_dict["version"] == 1
        assert proc_dict["custom_fields"]["risk_level"] == "high"

    def test_procedure_custom_fields(self):
        """Test procedure with custom fields."""
        proc = ITSMProcedure(
            procedure_id="proc-custom",
            title="Custom Procedure",
            description="Test custom fields",
            owner="owner",
            owner_email="owner@company.com",
            version=1,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            status="active",
            source_system="jira",
            source_id="PROC-1",
            custom_fields={
                "approval_level": "executive",
                "business_impact": "critical",
                "regulatory_mapping": ["eu_ai_act", "gdpr"],
            },
        )

        assert proc.custom_fields["approval_level"] == "executive"
        assert "gdpr" in proc.custom_fields["regulatory_mapping"]


class TestEnforcementLogging:
    """Tests for logging enforcement events back to ITSM."""

    def test_jira_log_enforcement_event(self, jira_connector, sample_procedure):
        """Test logging enforcement event to Jira."""
        jira_connector.authenticate()
        jira_connector.create_procedure(sample_procedure)

        event = {
            "event_type": "access_granted",
            "actor": "user-123",
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "decision": "ALLOWED",
        }

        result = jira_connector.log_enforcement_event(sample_procedure.procedure_id, event)
        assert result is True

    def test_servicenow_log_enforcement_event(self, servicenow_connector, sample_procedure):
        """Test logging enforcement event to ServiceNow."""
        servicenow_connector.authenticate()
        sample_procedure.source_system = "servicenow"
        servicenow_connector.create_procedure(sample_procedure)

        event = {
            "event_type": "change_executed",
            "actor": "automation",
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "status": "completed",
        }

        result = servicenow_connector.log_enforcement_event(sample_procedure.procedure_id, event)
        assert result is True

    def test_log_event_to_nonexistent_procedure(self, jira_connector):
        """Test logging event to nonexistent procedure fails."""
        jira_connector.authenticate()

        event = {
            "event_type": "access_granted",
            "actor": "user-123",
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        }

        result = jira_connector.log_enforcement_event("nonexistent-id", event)
        assert result is False

    def test_log_event_without_auth(self, jira_connector, sample_procedure):
        """Test logging event without authentication fails."""
        jira_connector.create_procedure(sample_procedure)

        event = {
            "event_type": "access_granted",
            "actor": "user-123",
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        }

        result = jira_connector.log_enforcement_event(sample_procedure.procedure_id, event)
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
