"""Tests for Phase 32: Enhanced MCP Connector Layer.

Tests MCP connector expansion, entity resolution, observation graph, and Speider scanner.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from src.valo_platform.speider_connectors import (
    MCPConnectorBase,
    AllemannsdataLovdataConnector,
    EntityResolutionEngine,
    EntitySignature,
    EntityCluster,
    ObservationGraph,
    Signal,
    SignalRelation,
    EntityRelation,
    SignalRelationType,
    RelationshipType,
    SpeiderScanner,
    ScanResult,
    BusinessRegistryConnector,
    AllemannsdataFirmafaktaConnector,
    Company,
)


class TestMCPConnectorBase:
    """Test MCP connector base class."""

    def test_mcp_connector_initialization(self):
        """Test MCP connector base initialization."""

        class TestConnector(MCPConnectorBase):
            def register_tools(self):
                self._tool_registry = {
                    "test_tool": {
                        "description": "A test tool",
                        "required_params": ["param1"],
                        "parameters": {"param1": "str"},
                    }
                }

        connector = TestConnector("TestSource")
        assert connector.server_name == "TestSource"
        assert connector.get_connector_name() == "TestSource"
        assert connector.is_healthy()

    def test_tool_registration(self):
        """Test tool registration."""

        class TestConnector(MCPConnectorBase):
            def register_tools(self):
                self._tool_registry = {
                    "tool1": {
                        "description": "Tool 1",
                        "required_params": ["x"],
                        "parameters": {"x": "str"},
                    },
                    "tool2": {
                        "description": "Tool 2",
                        "required_params": ["y"],
                        "parameters": {"y": "int"},
                    },
                }

        connector = TestConnector("TestSource")
        tools = connector.list_tools()
        assert len(tools) == 2
        assert tools[0]["name"] == "tool1"

    def test_tool_invocation(self):
        """Test tool invocation with mocked HTTP client."""

        class TestConnector(MCPConnectorBase):
            def register_tools(self):
                self._tool_registry = {
                    "echo": {
                        "description": "Echo tool",
                        "required_params": ["message"],
                        "parameters": {"message": "str"},
                    }
                }

        connector = TestConnector("TestSource")
        # Mock the HTTP client to avoid real HTTP calls
        connector._http_client.call_tool = MagicMock(return_value={"echoed": "hello"})
        result = connector.call_tool("echo", {"message": "hello"})
        assert result["echoed"] == "hello"


class TestAllemannsdataLovdataConnector:
    """Test Lovdata connector."""

    @pytest.fixture
    def mock_http_client(self):
        """Mock the HTTP client to avoid real API calls."""

        def _call_tool(server, tool_name, params):
            if tool_name == "search_legislation":
                return {
                    "status": "success",
                    "data": [
                        {
                            "statute_id": "LOV-001",
                            "statute_type": "law",
                            "title": "Arbeidsmiljøloven",
                        }
                    ],
                }
            if tool_name == "get_statute":
                return {
                    "status": "success",
                    "data": {
                        "statute_id": "LOV-001",
                        "full_text": "§ 1. Formål …",
                    },
                }
            if tool_name == "search_court_decisions":
                return {
                    "status": "success",
                    "data": [
                        {
                            "decision_id": "HR-2026-1",
                            "court": "District Court",
                        }
                    ],
                }
            if tool_name == "search_regulatory_decisions":
                return {
                    "status": "success",
                    "data": [
                        {
                            "decision_id": "REG-1",
                            "agency": "Datatilsynet",
                        }
                    ],
                }
            return {"status": "success", "data": []}

        with patch(
            "src.valo_platform.speider_connectors.mcp_connector_base.AllemannsdataHTTPClient"
        ) as mock:
            client = mock.return_value
            client.call_tool.side_effect = _call_tool
            yield client

    def test_lovdata_initialization(self, mock_http_client):
        """Test Lovdata connector initialization."""
        connector = AllemannsdataLovdataConnector()
        assert connector.get_connector_name() == "Lovdata"
        assert connector.is_healthy()

    def test_search_legislation(self, mock_http_client):
        """Test legislation search."""
        connector = AllemannsdataLovdataConnector()
        results = connector.search_legislation("arbeidsrettslig")
        assert len(results) > 0
        assert results[0]["statute_type"] == "law"

    def test_get_statute(self, mock_http_client):
        """Test statute retrieval."""
        connector = AllemannsdataLovdataConnector()
        statute = connector.get_statute("LOV-001")
        assert statute["statute_id"] == "LOV-001"
        assert "full_text" in statute

    def test_search_court_decisions(self, mock_http_client):
        """Test court decision search."""
        connector = AllemannsdataLovdataConnector()
        decisions = connector.search_court_decisions("kontakt")
        assert len(decisions) > 0
        assert decisions[0]["court"] == "District Court"

    def test_search_regulatory_decisions(self, mock_http_client):
        """Test regulatory decision search."""
        connector = AllemannsdataLovdataConnector()
        decisions = connector.search_regulatory_decisions("datasikkerhet")
        assert len(decisions) > 0
        assert "decision_id" in decisions[0]


class TestEntityResolutionEngine:
    """Test entity resolution engine."""

    def test_entity_resolution_initialization(self):
        """Test entity resolution engine initialization."""
        engine = EntityResolutionEngine()
        assert len(engine.clusters) == 0

    def test_add_single_entity(self):
        """Test adding single entity."""
        engine = EntityResolutionEngine()
        sig = EntitySignature(
            entity_type="company",
            primary_id="999000001",
            source="Firmafakta",
            name="Test Company",
        )
        cluster_id = engine.add_entity(sig)
        assert cluster_id in engine.clusters
        assert engine.clusters[cluster_id].primary_entity.name == "Test Company"

    def test_entity_clustering(self):
        """Test entity clustering."""
        engine = EntityResolutionEngine()

        # Add same entity from two sources
        sig1 = EntitySignature(
            entity_type="company",
            primary_id="999000001",
            source="Firmafakta",
            name="Acme Corp",
        )
        sig2 = EntitySignature(
            entity_type="company",
            primary_id="999000002",
            source="Lovdata",
            name="Acme Corp",
        )

        cluster_id_1 = engine.add_entity(sig1)
        cluster_id_2 = engine.add_entity(sig2)

        # Should be clustered together due to name matching
        assert cluster_id_1 == cluster_id_2

    def test_fuzzy_matching(self):
        """Test fuzzy string matching."""
        engine = EntityResolutionEngine()

        score = engine._fuzzy_match("Test Company", "Test Company")
        assert score == 1.0

        score = engine._fuzzy_match("Test Company", "Test Corp")
        assert score > 0.5

    def test_entity_cluster_merging(self):
        """Test manual cluster merging."""
        engine = EntityResolutionEngine()

        sig1 = EntitySignature(
            entity_type="company",
            primary_id="999000001",
            source="Firmafakta",
            name="Company A",
        )
        sig2 = EntitySignature(
            entity_type="company",
            primary_id="999000002",
            source="Firmafakta",  # Different ID, same source
            name="Company B",
        )

        cluster_id_1 = engine.add_entity(sig1)
        cluster_id_2 = engine.add_entity(sig2)

        # With stricter matching, these should be different clusters
        assert cluster_id_1 != cluster_id_2

        # Merge clusters
        merged_id = engine.merge_clusters(cluster_id_1, cluster_id_2)
        assert merged_id == cluster_id_1
        assert len(engine.clusters) == 1

    def test_resolution_statistics(self):
        """Test resolution statistics."""
        engine = EntityResolutionEngine()

        # Create companies with unique names to avoid fuzzy matching
        companies = ["Acme Corporation", "XYZ Industries", "Beta Enterprises"]
        for i, name in enumerate(companies):
            sig = EntitySignature(
                entity_type="company",
                primary_id=f"999{i:06d}",
                source="Firmafakta",
                name=name,
            )
            engine.add_entity(sig)

        stats = engine.get_resolution_stats()
        assert stats["total_clusters"] == 3
        assert stats["by_type"]["company"]["clusters"] == 3


class TestObservationGraph:
    """Test observation graph."""

    def test_observation_graph_initialization(self):
        """Test observation graph initialization."""
        graph = ObservationGraph()
        assert len(graph.signals) == 0
        assert len(graph.signal_relations) == 0

    def test_add_signal(self):
        """Test adding signals."""
        graph = ObservationGraph()

        signal = Signal(
            signal_id="SIG-001",
            signal_type="transaction",
            entity_id="ENT-001",
            source="Firmafakta",
            value={"amount": 10000},
            confidence=0.95,
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
        )

        graph.add_signal(signal)
        assert "SIG-001" in graph.signals
        assert signal in graph.get_entity_signals("ENT-001")

    def test_get_signals_by_type(self):
        """Test retrieving signals by type."""
        graph = ObservationGraph()

        for i in range(3):
            signal = Signal(
                signal_id=f"SIG-{i}",
                signal_type="transaction" if i < 2 else "grant",
                entity_id="ENT-001",
                source="Firmafakta",
                value={},
                confidence=0.9,
                timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            graph.add_signal(signal)

        transactions = graph.get_signals_by_type("transaction")
        assert len(transactions) == 2

    def test_get_signals_by_source(self):
        """Test retrieving signals by source."""
        graph = ObservationGraph()

        for source in ["Firmafakta", "Lovdata", "Firmafakta"]:
            signal = Signal(
                signal_id=f"SIG-{source}-{len(graph.signals)}",
                signal_type="data",
                entity_id="ENT-001",
                source=source,
                value={},
                confidence=0.9,
                timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            graph.add_signal(signal)

        firmafakta_signals = graph.get_signals_by_source("Firmafakta")
        assert len(firmafakta_signals) == 2

    def test_entity_relations(self):
        """Test entity relations."""
        graph = ObservationGraph()

        relation = EntityRelation(
            relation_id="REL-001",
            entity_id_1="ENT-001",
            entity_id_2="ENT-002",
            relation_type=RelationshipType.SHAREHOLDER,
        )

        graph.add_entity_relation(relation)
        related = graph.get_related_entities("ENT-001")
        assert len(related) > 0
        assert related[0][0] == "ENT-002"

    def test_anomaly_detection(self):
        """Test anomaly detection."""
        graph = ObservationGraph()

        # Add signals from multiple sources
        for source in ["Firmafakta", "Lovdata"]:
            signal = Signal(
                signal_id=f"SIG-{source}",
                signal_type="grant_award",
                entity_id="ENT-001",
                source=source,
                value={"amount": 100000},
                confidence=0.95,
                timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            graph.add_signal(signal)

        patterns = graph.detect_anomalous_patterns("ENT-001")
        # Should detect multi-source agreement pattern
        assert any(p["pattern_type"] == "multi_source_agreement" for p in patterns)

    def test_entity_subgraph(self):
        """Test entity subgraph extraction."""
        graph = ObservationGraph()

        # Add signals and relations
        signal = Signal(
            signal_id="SIG-001",
            signal_type="transaction",
            entity_id="ENT-001",
            source="Firmafakta",
            value={},
            confidence=0.9,
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        graph.add_signal(signal)

        relation = EntityRelation(
            relation_id="REL-001",
            entity_id_1="ENT-001",
            entity_id_2="ENT-002",
            relation_type=RelationshipType.SHAREHOLDER,
        )
        graph.add_entity_relation(relation)

        subgraph = graph.get_entity_graph("ENT-001", depth=2)
        assert subgraph["root_entity"] == "ENT-001"
        assert subgraph["entity_count"] >= 1


class TestSpeiderScanner:
    """Test Speider scanner."""

    @pytest.fixture
    def mock_firmafakta_connector(self):
        """Create a mock Firmafakta connector that doesn't make real HTTP calls."""
        connector = MagicMock(spec=AllemannsdataFirmafaktaConnector)
        connector.get_connector_name.return_value = "Firmafakta"
        connector.is_healthy.return_value = True

        # Mock company data
        mock_company = Company(
            org_number="999000001",
            name="Test Company AS",
            business_code="62.010",
            municipality="Oslo",
            status="Active",
            employee_count=10,
            source="Firmafakta",
        )
        connector.get_company.return_value = mock_company
        connector.get_company_shareholders.return_value = []
        connector.get_company_roles.return_value = []
        connector.get_company_financials.return_value = {}
        connector.get_company_grants.return_value = []
        connector.get_person_holdings.return_value = []
        return connector

    @pytest.fixture
    def mock_lovdata_connector(self):
        """Create a mock Lovdata connector."""
        connector = MagicMock(spec=BusinessRegistryConnector)
        connector.get_connector_name.return_value = "Lovdata"
        connector.is_healthy.return_value = True
        connector.get_company.return_value = None  # Lovdata doesn't have company data
        connector.get_company_shareholders.return_value = []
        connector.get_company_roles.return_value = []
        connector.get_company_financials.return_value = {}
        connector.get_company_grants.return_value = []
        connector.get_person_holdings.return_value = []
        return connector

    def test_scanner_initialization(self):
        """Test Speider scanner initialization."""
        scanner = SpeiderScanner("tenant-1")
        assert scanner.tenant_id == "tenant-1"
        assert len(scanner.connectors) == 0

    def test_register_connector(self, mock_firmafakta_connector):
        """Test connector registration."""
        scanner = SpeiderScanner("tenant-1")
        scanner.register_connector(mock_firmafakta_connector)

        assert "Firmafakta" in scanner.connectors
        assert len(scanner.connectors) == 1

    def test_scan_company(self, mock_firmafakta_connector):
        """Test company scanning."""
        scanner = SpeiderScanner("tenant-1")
        scanner.register_connector(mock_firmafakta_connector)

        result = scanner.scan_company("999000001")

        assert result.entity_id == "999000001"
        assert result.entity_type == "company"
        assert result.total_signals > 0
        assert "Firmafakta" in result.sources_consulted

    def test_scan_result_structure(self, mock_firmafakta_connector):
        """Test scan result structure."""
        scanner = SpeiderScanner("tenant-1")
        scanner.register_connector(mock_firmafakta_connector)

        result = scanner.scan_company("999000001")

        assert isinstance(result, ScanResult)
        assert result.scan_id
        assert result.timestamp
        assert result.status in ["success", "partial", "failed"]

    def test_multiple_connectors(self, mock_firmafakta_connector, mock_lovdata_connector):
        """Test scanning with multiple connectors."""
        scanner = SpeiderScanner("tenant-1")
        scanner.register_connector(mock_firmafakta_connector)
        scanner.register_connector(mock_lovdata_connector)

        result = scanner.scan_company("999000001")

        assert len(result.sources_consulted) >= 1

    def test_entity_intelligence(self, mock_firmafakta_connector):
        """Test entity intelligence retrieval."""
        scanner = SpeiderScanner("tenant-1")
        scanner.register_connector(mock_firmafakta_connector)

        # Scan first
        scanner.scan_company("999000001")

        # Get intelligence
        intelligence = scanner.get_entity_intelligence("999000001")

        assert intelligence["entity_id"] == "999000001"
        assert "signal_count" in intelligence
        assert "anomalies" in intelligence

    def test_scanner_statistics(self, mock_firmafakta_connector, mock_lovdata_connector):
        """Test scanner statistics."""
        scanner = SpeiderScanner("tenant-1")
        scanner.register_connector(mock_firmafakta_connector)
        scanner.register_connector(mock_lovdata_connector)

        scanner.scan_company("999000001")

        stats = scanner.get_scanner_statistics()
        assert stats["tenant_id"] == "tenant-1"
        assert stats["connectors_registered"] == 2
        assert "observation_graph" in stats

    def test_scan_person(self, mock_firmafakta_connector):
        """Test person scanning."""
        scanner = SpeiderScanner("tenant-1")
        scanner.register_connector(mock_firmafakta_connector)

        result = scanner.scan_person("person-123")

        assert result.entity_id == "person-123"
        assert result.entity_type == "person"
        assert result.status in ["success", "partial"]


class TestPhase32Integration:
    """Integration tests for Phase 32."""

    @pytest.fixture
    def mock_firmafakta_connector(self):
        """Create a mock Firmafakta connector."""
        connector = MagicMock(spec=AllemannsdataFirmafaktaConnector)
        connector.get_connector_name.return_value = "Firmafakta"
        connector.is_healthy.return_value = True

        mock_company = Company(
            org_number="999000001",
            name="Test Company AS",
            business_code="62.010",
            municipality="Oslo",
            status="Active",
            employee_count=10,
            source="Firmafakta",
        )
        connector.get_company.return_value = mock_company
        connector.get_company_shareholders.return_value = []
        connector.get_company_roles.return_value = []
        connector.get_company_financials.return_value = {}
        connector.get_company_grants.return_value = []
        connector.get_person_holdings.return_value = []
        return connector

    @pytest.fixture
    def mock_lovdata_connector(self):
        """Create a mock Lovdata connector."""
        connector = MagicMock(spec=BusinessRegistryConnector)
        connector.get_connector_name.return_value = "Lovdata"
        connector.is_healthy.return_value = True
        connector.get_company.return_value = None
        connector.get_company_shareholders.return_value = []
        connector.get_company_roles.return_value = []
        connector.get_company_financials.return_value = {}
        connector.get_company_grants.return_value = []
        connector.get_person_holdings.return_value = []
        return connector

    def test_end_to_end_scanning(self, mock_firmafakta_connector, mock_lovdata_connector):
        """Test end-to-end scanning workflow."""
        scanner = SpeiderScanner("tenant-1")

        # Register multiple sources
        scanner.register_connector(mock_firmafakta_connector)
        scanner.register_connector(mock_lovdata_connector)

        # Scan company
        result = scanner.scan_company("999000001")

        # Verify result
        assert result.status == "success"
        assert result.total_signals > 0

        # Check entity resolution
        resolution = scanner.entity_resolution.get_resolution_stats()
        assert resolution["total_entities"] > 0

        # Check observation graph
        graph_stats = scanner.observation_graph.get_graph_statistics()
        assert graph_stats["total_signals"] > 0

    def test_multi_source_entity_resolution(self):
        """Test entity resolution across multiple sources."""
        engine = EntityResolutionEngine()

        # Add same company from different sources with slightly different names
        sources = [
            ("Firmafakta", "Acme Corp"),
            ("Lovdata", "Acme Corporation"),
            ("SSB", "ACME CORP"),
        ]

        cluster_ids = set()
        for source, name in sources:
            sig = EntitySignature(
                entity_type="company",
                primary_id=f"ORG-{source}",
                source=source,
                name=name,
            )
            cluster_id = engine.add_entity(sig)
            cluster_ids.add(cluster_id)

        # All should resolve to same cluster (or at least very few clusters)
        assert len(cluster_ids) <= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
