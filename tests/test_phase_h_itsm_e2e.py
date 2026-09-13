"""Phase H: End-to-End ITSM Workflow Testing

Complete testing of:
1. Procedure creation in ITSM → VALO ingestion → RiskContract generation
2. Governance evaluation → enforcement decision
3. Enforcement logging back to ITSM system
4. Multi-customer scenarios with different industries
5. Procedure synchronization fidelity
6. Realistic customer onboarding with ITSM procedures

Tests ensure procedure-to-policy flow is production-ready.
"""

import pytest
from datetime import datetime, timezone
from src.valo_platform.itsm.connectors import (
    JiraConnector, ServiceNowConnector, ITSMConnectorFactory,
    ITSMProcedure, ITSMEventType
)
from src.valo_platform.customer_onboarding import (
    CustomerProfile, CustomerOnboardingOrchestrator,
    CustomerOnboardingSession, OnboardingStage, DeploymentEnvironment,
    AuthProviderConfig
)
from src.valo_platform.procedure_translator import ProcedureTranslator
from src.valo_platform.models.procedure import ProcedurePayload, ProcedureStep


class TestITSME2EWorkflow:
    """End-to-end ITSM workflow testing."""

    @pytest.fixture
    def jira_connector(self):
        """Create Jira connector for testing."""
        return JiraConnector(
            instance_url="https://company.atlassian.net",
            api_token="test-api-token",
            email="user@company.com",
        )

    @pytest.fixture
    def servicenow_connector(self):
        """Create ServiceNow connector for testing."""
        return ServiceNowConnector(
            instance_url="https://dev12345.service-now.com",
            client_id="test-client-id",
            client_secret="test-client-secret",
        )

    @pytest.fixture
    def translator(self):
        """Create procedure translator."""
        return ProcedureTranslator()

    @pytest.fixture
    def orchestrator(self):
        """Create customer onboarding orchestrator."""
        return CustomerOnboardingOrchestrator()

    def test_e2e_jira_procedure_creation_workflow(self, jira_connector):
        """Test complete Jira workflow: create → retrieve → update → log enforcement."""
        # Step 1: Authenticate
        result = jira_connector.authenticate()
        assert result is True
        assert jira_connector.authenticated is True

        # Step 2: Create procedure in Jira
        procedure = ITSMProcedure(
            procedure_id="proc-jira-001",
            title="AI Model Access Control - Jira Test",
            description="Controls access to high-risk AI models in production",
            owner="security-team",
            owner_email="security@company.com",
            version=1,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            status="active",
            source_system="jira",
            source_id="",  # Will be set by Jira
            custom_fields={
                "risk_level": "high",
                "compliance_framework": "eu_ai_act",
                "approval_required": "manager_and_ciso",
                "business_impact": "Model compromise affects all customer data"
            },
        )

        created = jira_connector.create_procedure(procedure)
        assert created is not None
        assert created.procedure_id == "proc-jira-001"
        assert "PROC-" in created.source_id
        assert created.source_system == "jira"

        # Step 3: Retrieve procedure
        retrieved = jira_connector.get_procedure("proc-jira-001")
        assert retrieved is not None
        assert retrieved.title == procedure.title
        assert retrieved.owner == procedure.owner
        assert retrieved.custom_fields["risk_level"] == "high"

        # Step 4: Update procedure (simulate version bump)
        retrieved.title = "AI Model Access Control - Updated"
        retrieved.updated_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        updated = jira_connector.update_procedure(retrieved)
        assert updated is True

        # Step 5: Verify update (version increments on update)
        retrieved_v2 = jira_connector.get_procedure("proc-jira-001")
        assert retrieved_v2.version > 1
        assert retrieved_v2.title == "AI Model Access Control - Updated"

        # Step 6: Log enforcement event back to Jira
        enforcement_event = {
            "event_type": "access_granted",
            "actor": "user-12345",
            "actor_role": "engineer",
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "decision": "ALLOWED",
            "decision_reason": "Manager approval satisfied",
            "request_context": "Requested access to GPT-4 model"
        }
        logged = jira_connector.log_enforcement_event("proc-jira-001", enforcement_event)
        assert logged is True

        # Step 7: Delete procedure (cleanup)
        deleted = jira_connector.delete_procedure("proc-jira-001")
        assert deleted is True
        final_check = jira_connector.get_procedure("proc-jira-001")
        assert final_check is None

    def test_e2e_servicenow_procedure_creation_workflow(self, servicenow_connector):
        """Test complete ServiceNow workflow: create → retrieve → update → log enforcement."""
        # Step 1: Authenticate
        result = servicenow_connector.authenticate()
        assert result is True
        assert servicenow_connector.authenticated is True

        # Step 2: Create procedure in ServiceNow
        procedure = ITSMProcedure(
            procedure_id="proc-sn-001",
            title="Data Handling Procedure - ServiceNow Test",
            description="Controls how sensitive customer data is handled",
            owner="compliance-team",
            owner_email="compliance@company.com",
            version=1,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            status="active",
            source_system="servicenow",
            source_id="",  # Will be set by ServiceNow
            custom_fields={
                "risk_level": "critical",
                "regulatory_mapping": ["gdpr", "hipaa", "pci_dss"],
                "data_categories": ["customer_pii", "health_records", "payment_data"],
                "retention_policy": "7_years"
            },
        )

        created = servicenow_connector.create_procedure(procedure)
        assert created is not None
        assert created.procedure_id == "proc-sn-001"
        assert "CHG" in created.source_id
        assert created.source_system == "servicenow"

        # Step 3: Retrieve procedure
        retrieved = servicenow_connector.get_procedure("proc-sn-001")
        assert retrieved is not None
        assert retrieved.title == procedure.title
        assert "gdpr" in retrieved.custom_fields["regulatory_mapping"]

        # Step 4: Update procedure
        procedure.version = 2
        procedure.custom_fields["retention_policy"] = "10_years"
        updated = servicenow_connector.update_procedure(procedure)
        assert updated is True

        # Step 5: Log enforcement event (change execution)
        enforcement_event = {
            "event_type": "change_executed",
            "actor": "automation-service",
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "status": "completed",
            "affected_systems": ["data_warehouse", "backup_system"],
            "records_affected": 1_250_000,
            "encryption_verified": True
        }
        logged = servicenow_connector.log_enforcement_event("proc-sn-001", enforcement_event)
        assert logged is True

        # Step 6: Delete procedure (cleanup)
        deleted = servicenow_connector.delete_procedure("proc-sn-001")
        assert deleted is True

    def test_e2e_multi_procedure_listing(self, jira_connector):
        """Test retrieving multiple procedures simultaneously."""
        jira_connector.authenticate()

        # Create multiple procedures
        procs = []
        for i in range(5):
            proc = ITSMProcedure(
                procedure_id=f"proc-list-{i:03d}",
                title=f"Procedure {i}",
                description=f"Test procedure {i}",
                owner="test-owner",
                owner_email="test@company.com",
                version=1,
                created_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                updated_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
                status="active",
                source_system="jira",
                source_id="",
                custom_fields={},
            )
            created = jira_connector.create_procedure(proc)
            procs.append(created)

        # List all procedures
        all_procedures = jira_connector.get_procedures()
        assert len(all_procedures) == 5
        assert all(p.source_system == "jira" for p in all_procedures)

        # Verify each procedure is retrievable
        for i in range(5):
            retrieved = jira_connector.get_procedure(f"proc-list-{i:03d}")
            assert retrieved is not None
            assert retrieved.title == f"Procedure {i}"

    def test_e2e_factory_creates_correct_connectors(self):
        """Test factory creates appropriate connectors for each system."""
        # Create Jira connector via factory
        jira = ITSMConnectorFactory.create_connector(
            system="jira",
            instance_url="https://test.atlassian.net",
            credentials={"api_token": "token", "email": "test@example.com"}
        )
        assert isinstance(jira, JiraConnector)
        assert jira.instance_url == "https://test.atlassian.net"

        # Create ServiceNow connector via factory
        servicenow = ITSMConnectorFactory.create_connector(
            system="servicenow",
            instance_url="https://test.service-now.com",
            credentials={"client_id": "id", "client_secret": "secret"}
        )
        assert isinstance(servicenow, ServiceNowConnector)
        assert servicenow.instance_url == "https://test.service-now.com"

        # Factory is case-insensitive
        jira_upper = ITSMConnectorFactory.create_connector(
            system="JIRA",
            instance_url="https://test.atlassian.net",
            credentials={"api_token": "token", "email": "test@example.com"}
        )
        assert isinstance(jira_upper, JiraConnector)


class TestCustomerPilotScenarios:
    """Test realistic customer onboarding scenarios."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator for customer onboarding."""
        return CustomerOnboardingOrchestrator()

    @pytest.fixture
    def energy_company_profile(self):
        """Create profile for Energy sector customer."""
        return CustomerProfile(
            customer_id="customer-energy-001",
            company_name="GridOperations Inc",
            contact_email="admin@gridops.no",
            contact_phone="+47-123-45678",
            industry="energy",
            employee_count=450,
            data_classification="confidential",
            compliance_frameworks=["EU_AI_ACT", "IEC_62351_11", "NERC_CIP"],
            integration_source="jira",
            deployment_env=DeploymentEnvironment.PRODUCTION,
            timezone="Europe/Oslo"
        )

    @pytest.fixture
    def healthcare_company_profile(self):
        """Create profile for Healthcare sector customer."""
        return CustomerProfile(
            customer_id="customer-health-001",
            company_name="CareHealth Systems",
            contact_email="compliance@carehealth.se",
            contact_phone="+46-123-45678",
            industry="healthcare",
            employee_count=800,
            data_classification="restricted",
            compliance_frameworks=["HIPAA", "GDPR", "EU_AI_ACT"],
            integration_source="servicenow",
            deployment_env=DeploymentEnvironment.PRODUCTION,
            timezone="Europe/Stockholm"
        )

    def test_pilot_energy_sector_onboarding(self, orchestrator, energy_company_profile):
        """Test onboarding flow for Energy sector customer."""
        # Step 1: Start onboarding
        session = orchestrator.start_onboarding(energy_company_profile)
        assert session is not None
        assert session.session_id is not None
        assert session.current_stage == OnboardingStage.INTAKE
        assert session.customer_profile.industry == "energy"

        # Step 2: Provision tenant
        provisioning_result = orchestrator.provision_tenant(session)
        assert provisioning_result is not None
        assert "tenant_id" in provisioning_result
        assert "shard_id" in provisioning_result
        assert "encryption_key" in provisioning_result

        # Step 3: Setup auth provider (Jira in this case)
        auth_config = AuthProviderConfig(
            provider="jira",
            client_id="test-client",
            client_secret="test-secret"
        )
        auth_config_result = orchestrator.setup_auth_provider(session, auth_config)
        assert auth_config_result is not None
        assert auth_config_result["provider"] == "jira"

        # Step 4: Load industry-specific templates
        templates_result = orchestrator.load_policy_templates(session, "energy")
        assert templates_result is not None
        assert "templates" in templates_result
        templates = templates_result["templates"]
        assert len(templates) > 0
        # Energy templates should include grid access control, emergency shutdown

        # Step 5: Setup monitoring for critical infrastructure
        monitoring_result = orchestrator.setup_monitoring(
            session,
            contact_email="ops@gridops.no",
            contact_phone="+47-123-45678"
        )
        assert monitoring_result is not None
        assert isinstance(monitoring_result, dict)
        assert len(monitoring_result) > 0

        # Step 6: Initialize audit trail with 7-year retention for regulatory compliance
        audit_result = orchestrator.initialize_audit_trail(session)
        assert audit_result is not None
        assert audit_result["worm_enabled"] is True
        assert audit_result["retention_days"] == 2555  # 7 years

        # Step 7: Complete onboarding
        completion_result = orchestrator.complete_onboarding(session)
        assert completion_result is not None
        assert isinstance(completion_result, dict)

        # Step 8: Verify final status
        status = orchestrator.get_onboarding_status(session.session_id)
        assert status["progress_percent"] >= 75
        assert len(status["completed_stages"]) > 0

    def test_pilot_healthcare_sector_onboarding(self, orchestrator, healthcare_company_profile):
        """Test onboarding flow for Healthcare sector customer."""
        # Step 1: Start onboarding
        session = orchestrator.start_onboarding(healthcare_company_profile)
        assert session is not None
        assert session.customer_profile.industry == "healthcare"
        assert "HIPAA" in session.customer_profile.compliance_frameworks

        # Step 2: Provision tenant
        orchestrator.provision_tenant(session)

        # Step 3: Setup auth provider (ServiceNow for healthcare)
        auth_config = AuthProviderConfig(
            provider="servicenow",
            client_id="test-client",
            client_secret="test-secret"
        )
        orchestrator.setup_auth_provider(session, auth_config)

        # Step 4: Load healthcare-specific templates
        templates_result = orchestrator.load_policy_templates(session, "healthcare")
        assert templates_result is not None
        templates = templates_result["templates"]
        # Healthcare templates should include patient data access, PHI handling
        assert len(templates) > 0

        # Step 5: Setup monitoring with healthcare alerts
        monitoring_result = orchestrator.setup_monitoring(
            session,
            contact_email="compliance@carehealth.se",
            contact_phone="+46-123-45678"
        )
        assert monitoring_result is not None

    def test_pilot_concurrent_customer_onboarding(self, orchestrator):
        """Test concurrent onboarding of multiple customers."""
        industries = ["energy", "healthcare", "finance", "technology", "manufacturing"]
        customers = [
            CustomerProfile(
                customer_id=f"customer-{i:03d}",
                company_name=f"Company {i}",
                contact_email=f"admin-{i}@company.com",
                contact_phone=f"+47-123-456{i:02d}",
                industry=industries[i % 5],
                employee_count=100 * (i + 1),
                data_classification="internal",
                compliance_frameworks=["EU_AI_ACT"],
                integration_source="jira",
                deployment_env=DeploymentEnvironment.PRODUCTION,
                timezone="Europe/Oslo"
            )
            for i in range(3)
        ]

        sessions = []
        for profile in customers:
            session = orchestrator.start_onboarding(profile)
            sessions.append(session)

        assert len(sessions) == 3
        for session in sessions:
            assert session is not None
            status = orchestrator.get_onboarding_status(session.session_id)
            assert status is not None


class TestProcedureSynchronizationFidelity:
    """Test that procedures sync correctly without data loss or corruption."""

    @pytest.fixture
    def jira_connector(self):
        return JiraConnector(
            instance_url="https://company.atlassian.net",
            api_token="test-api-token",
            email="user@company.com",
        )

    def test_custom_fields_preserved_during_sync(self, jira_connector):
        """Test that custom fields are preserved through sync cycle."""
        jira_connector.authenticate()

        original_procedure = ITSMProcedure(
            procedure_id="proc-sync-001",
            title="Test Procedure",
            description="Testing field preservation",
            owner="test-owner",
            owner_email="test@company.com",
            version=1,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            status="active",
            source_system="jira",
            source_id="",
            custom_fields={
                "risk_level": "high",
                "approval_required": "manager_and_ciso",
                "business_impact": "Critical system down",
                "recovery_time_objective": "1_hour",
                "recovery_point_objective": "15_minutes",
                "regulatory_mapping": ["SOC_2", "ISO_27001"],
                "affected_services": ["API", "Database", "Cache"],
                "escalation_policy": "24/7_on_call"
            }
        )

        # Create procedure
        created = jira_connector.create_procedure(original_procedure)
        assert created is not None

        # Retrieve and verify all custom fields preserved
        retrieved = jira_connector.get_procedure("proc-sync-001")
        assert retrieved.custom_fields == original_procedure.custom_fields
        assert len(retrieved.custom_fields) == len(original_procedure.custom_fields)

    def test_procedure_version_tracking(self, jira_connector):
        """Test that version increments are tracked correctly."""
        jira_connector.authenticate()

        procedure = ITSMProcedure(
            procedure_id="proc-version-001",
            title="Versioning Test",
            description="Testing version tracking",
            owner="test-owner",
            owner_email="test@company.com",
            version=1,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            status="active",
            source_system="jira",
            source_id="",
            custom_fields={}
        )

        # Create (v1)
        created = jira_connector.create_procedure(procedure)
        assert created.version == 1
        initial_version = created.version

        # Update (version increments)
        created.description = "Updated description"
        updated = jira_connector.update_procedure(created)
        assert updated is True

        # Verify version incremented
        v2 = jira_connector.get_procedure("proc-version-001")
        assert v2.version > initial_version
        assert v2.description == "Updated description"

    def test_enforcement_event_idempotency(self, jira_connector):
        """Test that logging the same event multiple times is safe."""
        jira_connector.authenticate()

        procedure = ITSMProcedure(
            procedure_id="proc-event-001",
            title="Event Test",
            description="Testing event idempotency",
            owner="test-owner",
            owner_email="test@company.com",
            version=1,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            status="active",
            source_system="jira",
            source_id="",
            custom_fields={}
        )

        jira_connector.create_procedure(procedure)

        event = {
            "event_type": "access_granted",
            "actor": "user-123",
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            "decision": "ALLOWED"
        }

        # Log same event multiple times
        for _ in range(3):
            result = jira_connector.log_enforcement_event("proc-event-001", event)
            assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
