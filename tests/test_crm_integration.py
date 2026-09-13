"""Tests for CRM integration (Salesforce + HubSpot).

NOTE: the consequence-bearing capture routes (POST /api/v1/crm/capture/*)
are fail-closed by the AFG execution gate (src/valo_platform/gate_integration.py
-> LEGACY_MUTATION_ROUTES). They return 409 LEGACY_MUTATION_PATH_DISABLED until
migrated to a bounded GovernanceClearance + AFGMutationGuard adapter. These tests
assert that fail-closed contract rather than the pre-gate 200 behaviour.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from fastapi.testclient import TestClient

from src.valo_platform.app import app
from src.valo_platform.api.crm_routes import (
    SalesforceOpportunityCapture,
    SalesforceAccountCapture,
    SalesforceContactCapture,
    HubSpotDealCapture,
    HubSpotContactCapture,
    _evaluate_crm_governance,
)


client = TestClient(app)


def _assert_fail_closed(response):
    """Assert the AFG gate's fail-closed 409 contract for legacy mutation routes."""
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "LEGACY_MUTATION_PATH_DISABLED"
    assert body["execution_authorized"] is False
    assert body["commit_preclusive"] is True
    assert body["required_path"]


class TestSalesforceIntegration:
    """Tests for Salesforce CRM integration."""

    @patch("src.valo_platform.api.crm_routes.salesforce_connector")
    def test_capture_opportunity_success(self, mock_sf):
        """Legacy capture route is fail-closed by the AFG gate (409)."""
        mock_sf.get_opportunity.return_value = {
            "Id": "opp-123",
            "Name": "Test Opportunity",
            "StageName": "Negotiation/Review",
            "Amount": 50000.0,
        }
        mock_sf.create_intelligence_record.return_value = "intelligence-id-1"

        response = client.post(
            "/api/v1/crm/capture/salesforce/opportunity",
            json={
                "opportunity_id": "opp-123",
                "title": "Risk Assessment",
                "intelligence_content": "Opportunity carries moderate risk",
            },
        )

        _assert_fail_closed(response)

    @patch("src.valo_platform.api.crm_routes.salesforce_connector")
    def test_capture_opportunity_not_found(self, mock_sf):
        """Legacy capture route is blocked before the handler runs (409)."""
        mock_sf.get_opportunity.return_value = None

        response = client.post(
            "/api/v1/crm/capture/salesforce/opportunity",
            json={
                "opportunity_id": "nonexistent",
                "title": "Risk Assessment",
                "intelligence_content": "Content",
            },
        )

        _assert_fail_closed(response)

    @patch("src.valo_platform.api.crm_routes.salesforce_connector")
    def test_capture_account_success(self, mock_sf):
        """Legacy capture route is fail-closed by the AFG gate (409)."""
        mock_sf.get_account.return_value = {
            "Id": "acc-123",
            "Name": "Test Account",
            "Industry": "Technology",
        }
        mock_sf.create_intelligence_record.return_value = "intelligence-id-2"

        response = client.post(
            "/api/v1/crm/capture/salesforce/account",
            json={
                "account_id": "acc-123",
                "title": "Compliance Review",
                "intelligence_content": "Account meets compliance requirements",
            },
        )

        _assert_fail_closed(response)

    @patch("src.valo_platform.api.crm_routes.salesforce_connector")
    def test_capture_contact_success(self, mock_sf):
        """Legacy capture route is fail-closed by the AFG gate (409)."""
        mock_sf.get_contact.return_value = {
            "Id": "con-123",
            "FirstName": "John",
            "LastName": "Doe",
            "Email": "john@example.com",
        }
        mock_sf.create_intelligence_record.return_value = "intelligence-id-3"

        response = client.post(
            "/api/v1/crm/capture/salesforce/contact",
            json={
                "contact_id": "con-123",
                "title": "Verification",
                "intelligence_content": "Contact identity verified",
            },
        )

        _assert_fail_closed(response)

    def test_capture_salesforce_not_initialized(self):
        """Legacy capture route is blocked by the gate before connector init (409)."""
        response = client.post(
            "/api/v1/crm/capture/salesforce/opportunity",
            json={
                "opportunity_id": "opp-123",
                "title": "Test",
                "intelligence_content": "Test content",
            },
        )

        _assert_fail_closed(response)

    @patch("src.valo_platform.api.crm_routes.salesforce_connector")
    def test_get_opportunity_intelligence(self, mock_sf):
        """Test retrieving intelligence for a Salesforce opportunity."""
        mock_sf.get_intelligence_for_record.return_value = [
            {
                "Id": "intel-1",
                "Title__c": "Initial Assessment",
                "Content__c": "Risk assessment content",
                "Captured_At__c": "2024-01-15T10:30:00Z",
            },
            {
                "Id": "intel-2",
                "Title__c": "Follow-up Review",
                "Content__c": "Updated assessment",
                "Captured_At__c": "2024-01-20T14:15:00Z",
            },
        ]

        response = client.get(
            "/api/v1/crm/intelligence/salesforce/opp-123",
            params={"object_type": "Opportunity"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["record_id"] == "opp-123"
        assert data["crm_type"] == "salesforce"
        assert len(data["intelligence_records"]) == 2

    @patch("src.valo_platform.api.crm_routes.salesforce_connector")
    def test_get_account_intelligence(self, mock_sf):
        """Test retrieving intelligence for a Salesforce account."""
        mock_sf.get_intelligence_for_record.return_value = [
            {
                "Id": "intel-1",
                "Title__c": "Compliance Check",
                "Content__c": "Account compliant",
                "Captured_At__c": "2024-01-15T10:30:00Z",
            },
        ]

        response = client.get(
            "/api/v1/crm/intelligence/salesforce/acc-456",
            params={"object_type": "Account"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["object_type"] == "Account"
        assert len(data["intelligence_records"]) == 1


class TestHubSpotIntegration:
    """Tests for HubSpot CRM integration."""

    @patch("src.valo_platform.api.crm_routes.hubspot_connector")
    def test_capture_deal_success(self, mock_hs):
        """Legacy capture route is fail-closed by the AFG gate (409)."""
        mock_hs.get_deal.return_value = {
            "id": "deal-123",
            "properties": {
                "dealname": {"value": "Test Deal"},
                "dealstage": {"value": "closedwon"},
                "amount": {"value": "75000"},
            },
        }
        mock_hs.create_intelligence_note.return_value = "deals/123/notes"

        response = client.post(
            "/api/v1/crm/capture/hubspot/deal",
            json={
                "deal_id": "deal-123",
                "title": "Deal Intelligence",
                "intelligence_content": "Deal assessment and risk analysis",
            },
        )

        _assert_fail_closed(response)

    @patch("src.valo_platform.api.crm_routes.hubspot_connector")
    def test_capture_deal_not_found(self, mock_hs):
        """Legacy capture route is blocked before the handler runs (409)."""
        mock_hs.get_deal.return_value = None

        response = client.post(
            "/api/v1/crm/capture/hubspot/deal",
            json={
                "deal_id": "nonexistent",
                "title": "Test",
                "intelligence_content": "Content",
            },
        )

        _assert_fail_closed(response)

    @patch("src.valo_platform.api.crm_routes.hubspot_connector")
    def test_capture_contact_success(self, mock_hs):
        """Legacy capture route is fail-closed by the AFG gate (409)."""
        mock_hs.get_contact.return_value = {
            "id": "con-456",
            "properties": {
                "firstname": {"value": "Jane"},
                "lastname": {"value": "Smith"},
                "email": {"value": "jane@example.com"},
            },
        }
        mock_hs.create_intelligence_note.return_value = "contacts/456/notes"

        response = client.post(
            "/api/v1/crm/capture/hubspot/contact",
            json={
                "contact_id": "con-456",
                "title": "Contact Verification",
                "intelligence_content": "Contact information verified and updated",
            },
        )

        _assert_fail_closed(response)

    def test_capture_hubspot_not_initialized(self):
        """Legacy capture route is blocked by the gate before connector init (409)."""
        response = client.post(
            "/api/v1/crm/capture/hubspot/deal",
            json={
                "deal_id": "deal-123",
                "title": "Test",
                "intelligence_content": "Test content",
            },
        )

        _assert_fail_closed(response)

    @patch("src.valo_platform.api.crm_routes.hubspot_connector")
    def test_get_deal_intelligence(self, mock_hs):
        """Test retrieving intelligence for a HubSpot deal."""
        mock_hs.get_intelligence_history.return_value = {
            "object_id": "deal-123",
            "object_type": "deals",
            "intelligence": "Previous intelligence notes and assessment",
            "captured_at": "2024-01-15T10:30:00Z",
        }

        response = client.get(
            "/api/v1/crm/intelligence/hubspot/deal-123",
            params={"object_type": "deals"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["record_id"] == "deal-123"
        assert data["crm_type"] == "hubspot"

    @patch("src.valo_platform.api.crm_routes.hubspot_connector")
    def test_get_contact_intelligence(self, mock_hs):
        """Test retrieving intelligence for a HubSpot contact."""
        mock_hs.get_intelligence_history.return_value = {
            "object_id": "con-456",
            "object_type": "contacts",
            "intelligence": "Contact intelligence data",
            "captured_at": "2024-01-15T10:30:00Z",
        }

        response = client.get(
            "/api/v1/crm/intelligence/hubspot/con-456",
            params={"object_type": "contacts"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["object_type"] == "contacts"


class TestCRMGovernanceEvaluation:
    """Tests for CRM governance evaluation."""

    def test_evaluate_high_risk_content(self):
        """Test governance evaluation for high-risk content."""
        content = "This is a sensitive security breach incident"
        status, actions = _evaluate_crm_governance(content, "salesforce", "Opportunity")

        assert status == "high"
        assert any(a["action"] == "escalate_to_compliance" for a in actions)

    def test_evaluate_medium_risk_content(self):
        """Test governance evaluation for extended content."""
        content = "x" * 600
        status, actions = _evaluate_crm_governance(content, "salesforce", "Opportunity")

        assert status == "medium"
        assert any(a["action"] == "flag_for_review" for a in actions)

    def test_evaluate_low_risk_content(self):
        """Test governance evaluation for low-risk content."""
        content = "Regular opportunity update"
        status, actions = _evaluate_crm_governance(content, "salesforce", "Opportunity")

        assert status == "low"

    def test_evaluate_confidential_content(self):
        """Test governance evaluation for confidential content."""
        content = "This is a confidential business matter"
        status, actions = _evaluate_crm_governance(content, "hubspot", "deal")

        assert status == "high"

    def test_salesforce_opportunity_suggests_account_link(self):
        """Test that Salesforce opportunity capture suggests account linking."""
        content = "New opportunity"
        status, actions = _evaluate_crm_governance(content, "salesforce", "Opportunity")

        assert any(a["action"] == "link_to_account" for a in actions)

    def test_salesforce_contact_suggests_relationship_check(self):
        """Test that Salesforce contact capture suggests relationship check."""
        content = "New contact"
        status, actions = _evaluate_crm_governance(content, "salesforce", "Contact")

        assert any(a["action"] == "check_relationships" for a in actions)

    def test_hubspot_deal_suggests_stage_check(self):
        """Test that HubSpot deal capture suggests stage checking."""
        content = "Deal update"
        status, actions = _evaluate_crm_governance(content, "hubspot", "deal")

        assert any(a["action"] == "check_deal_stage" for a in actions)

    def test_actions_limited_to_three(self):
        """Test that suggested actions are limited to 3."""
        content = "x" * 600 + " sensitive confidential"
        status, actions = _evaluate_crm_governance(content, "salesforce", "Contact")

        assert len(actions) <= 3


class TestCRMIntegrationModels:
    """Tests for CRM integration data models."""

    def test_salesforce_opportunity_capture_creation(self):
        """Test SalesforceOpportunityCapture model creation."""
        capture = SalesforceOpportunityCapture(
            opportunity_id="opp-123",
            title="Test",
            intelligence_content="Test content",
        )

        assert capture.opportunity_id == "opp-123"
        assert capture.title == "Test"
        assert capture.source == "OLAV"

    def test_salesforce_account_capture_creation(self):
        """Test SalesforceAccountCapture model creation."""
        capture = SalesforceAccountCapture(
            account_id="acc-123",
            title="Test",
            intelligence_content="Test content",
        )

        assert capture.account_id == "acc-123"

    def test_salesforce_contact_capture_creation(self):
        """Test SalesforceContactCapture model creation."""
        capture = SalesforceContactCapture(
            contact_id="con-123",
            title="Test",
            intelligence_content="Test content",
        )

        assert capture.contact_id == "con-123"

    def test_hubspot_deal_capture_creation(self):
        """Test HubSpotDealCapture model creation."""
        capture = HubSpotDealCapture(
            deal_id="deal-123",
            title="Test",
            intelligence_content="Test content",
        )

        assert capture.deal_id == "deal-123"

    def test_hubspot_contact_capture_creation(self):
        """Test HubSpotContactCapture model creation."""
        capture = HubSpotContactCapture(
            contact_id="con-123",
            title="Test",
            intelligence_content="Test content",
        )

        assert capture.contact_id == "con-123"


class TestCRMHealth:
    """Tests for CRM health checks."""

    def test_crm_health_endpoint(self):
        """Test CRM service health check."""
        response = client.get("/api/v1/crm/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "salesforce_connected" in data
        assert "hubspot_connected" in data


class TestCRMErrorHandling:
    """Tests for CRM error handling (read-only / non-legacy routes only)."""

    @patch("src.valo_platform.api.crm_routes.salesforce_connector")
    def test_salesforce_capture_error_handling(self, mock_sf):
        """Legacy capture route is blocked by the gate before the handler (409)."""
        mock_sf.get_opportunity.side_effect = Exception("API Error")

        response = client.post(
            "/api/v1/crm/capture/salesforce/opportunity",
            json={
                "opportunity_id": "opp-123",
                "title": "Test",
                "intelligence_content": "Test",
            },
        )

        _assert_fail_closed(response)

    @patch("src.valo_platform.api.crm_routes.hubspot_connector")
    def test_hubspot_capture_error_handling(self, mock_hs):
        """Legacy capture route is blocked by the gate before the handler (409)."""
        mock_hs.get_deal.side_effect = Exception("API Error")

        response = client.post(
            "/api/v1/crm/capture/hubspot/deal",
            json={
                "deal_id": "deal-123",
                "title": "Test",
                "intelligence_content": "Test",
            },
        )

        _assert_fail_closed(response)

    @patch("src.valo_platform.api.crm_routes.salesforce_connector")
    def test_get_intelligence_error_handling(self, mock_sf):
        """Test error handling for intelligence retrieval failures."""
        mock_sf.get_intelligence_for_record.side_effect = Exception("API Error")

        response = client.get(
            "/api/v1/crm/intelligence/salesforce/opp-123",
            params={"object_type": "Opportunity"},
        )

        assert response.status_code == 500
