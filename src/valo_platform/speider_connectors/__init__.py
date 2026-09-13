"""Speider Data Connectors

Abstraction layer for business data sources via MCP.
Allows connector swapping without affecting Speider's composition layer.
"""

from .business_registry import BusinessRegistryConnector
from .allemannsdata_firmafakta import AllemannsdataFirmafaktaConnector
from .allemannsdata_lovdata import AllemannsdataLovdataConnector
from .models import Company, Person, Shareholder, Role, FinancialStatement, Grant, RoleType
from .mcp_connector_base import MCPConnectorBase
from .external_monitor_connectors import WigoloConnector, WorldMonitorConnector
from .entity_resolution import EntityResolutionEngine, EntitySignature, EntityCluster
from .observation_graph import ObservationGraph, Signal, SignalRelation, EntityRelation, SignalRelationType, RelationshipType
from .speider_scanner import SpeiderScanner, ScanResult

__all__ = [
    "BusinessRegistryConnector",
    "AllemannsdataFirmafaktaConnector",
    "AllemannsdataLovdataConnector",
    "Company",
    "Person",
    "Shareholder",
    "Role",
    "FinancialStatement",
    "Grant",
    "RoleType",
    "MCPConnectorBase",
    "WigoloConnector",
    "WorldMonitorConnector",
    "EntityResolutionEngine",
    "EntitySignature",
    "EntityCluster",
    "ObservationGraph",
    "Signal",
    "SignalRelation",
    "EntityRelation",
    "SignalRelationType",
    "RelationshipType",
    "SpeiderScanner",
    "ScanResult",
]
