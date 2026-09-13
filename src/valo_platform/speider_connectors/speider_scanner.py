"""Speider Scanner

Orchestrates automated observation fetching from MCP connectors.
Coordinates entity resolution and observation graph construction.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass

logger = logging.getLogger(__name__)

from .business_registry import BusinessRegistryConnector
from .entity_resolution import EntityResolutionEngine, EntitySignature
from .observation_graph import ObservationGraph, Signal, SignalRelationType, SignalRelation
from .models import Company, Person, Shareholder, Role


@dataclass
class ScanResult:
    """Result of a Speider scan."""
    scan_id: str
    entity_id: str
    entity_type: str
    timestamp: datetime
    total_signals: int
    resolved_entities: int
    anomalies_detected: int
    sources_consulted: List[str]
    status: str  # "success", "partial", "failed"


class SpeiderScanner:
    """Orchestrates Speider observation scanning."""

    def __init__(self, tenant_id: str):
        """Initialize Speider scanner.

        Args:
            tenant_id: Tenant context for multi-tenancy
        """
        self.tenant_id = tenant_id
        self.connectors: Dict[str, BusinessRegistryConnector] = {}
        self.entity_resolution = EntityResolutionEngine()
        self.observation_graph = ObservationGraph()
        self._scan_history: Dict[str, ScanResult] = {}

    def register_connector(self, connector: BusinessRegistryConnector) -> None:
        """Register a data connector."""
        name = connector.get_connector_name()
        self.connectors[name] = connector

    def scan_company(self, org_number: str) -> ScanResult:
        """Scan a company across all registered connectors.

        Args:
            org_number: Organization number

        Returns:
            ScanResult with aggregated findings
        """
        scan_id = f"SCAN-{org_number}-{datetime.now(timezone.utc).replace(tzinfo=None).timestamp()}"
        signals = []
        resolved_count = 0

        # Consult each connector
        sources_consulted = []

        for connector_name, connector in self.connectors.items():
            try:
                if not connector.is_healthy():
                    continue

                sources_consulted.append(connector_name)

                # Get company details
                company = connector.get_company(org_number)
                if company:
                    # Create entity signature and resolve
                    sig = EntitySignature(
                        entity_type="company",
                        primary_id=company.org_number,
                        source=connector_name,
                        name=company.name,
                        additional_attrs={
                            "business_code": company.business_code,
                            "municipality": company.municipality,
                        },
                    )
                    cluster_id = self.entity_resolution.add_entity(sig)
                    resolved_count += 1

                    # Add signal for company data
                    signal = Signal(
                        signal_id=f"SIG-COMPANY-{scan_id}-{connector_name}",
                        signal_type="company_data",
                        entity_id=org_number,
                        source=connector_name,
                        value={
                            "name": company.name,
                            "status": company.status,
                            "employees": company.employee_count,
                        },
                        confidence=0.95,
                        timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
                        metadata={"cluster_id": cluster_id},
                    )
                    self.observation_graph.add_signal(signal)
                    signals.append(signal)

                # Get shareholders
                shareholders = connector.get_company_shareholders(org_number)
                for shareholder in shareholders:
                    sig = EntitySignature(
                        entity_type="shareholder",
                        primary_id=shareholder.shareholder_id,
                        source=connector_name,
                        name=shareholder.shareholder_name,
                        additional_attrs={"ownership_percentage": shareholder.ownership_percentage},
                    )
                    self.entity_resolution.add_entity(sig)
                    resolved_count += 1

                # Get roles
                roles = connector.get_company_roles(org_number)
                for role in roles:
                    sig = EntitySignature(
                        entity_type="person",
                        primary_id=role.person_id or f"PERSON-{role.role_id}",
                        source=connector_name,
                        name=role.person_name,
                        additional_attrs={"role_type": role.role_type.value},
                    )
                    self.entity_resolution.add_entity(sig)
                    resolved_count += 1

                    # Add role signal
                    signal = Signal(
                        signal_id=f"SIG-ROLE-{scan_id}-{role.role_id}",
                        signal_type="organizational_role",
                        entity_id=org_number,
                        source=connector_name,
                        value={"person": role.person_name, "role": role.role_type.value},
                        confidence=0.90,
                        timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                    self.observation_graph.add_signal(signal)
                    signals.append(signal)

                # Get financials
                financials = connector.get_company_financials(org_number)
                if financials:
                    signal = Signal(
                        signal_id=f"SIG-FINANCIALS-{scan_id}-{connector_name}",
                        signal_type="financial_statement",
                        entity_id=org_number,
                        source=connector_name,
                        value=financials,
                        confidence=0.92,
                        timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                    self.observation_graph.add_signal(signal)
                    signals.append(signal)

                # Get grants
                grants = connector.get_company_grants(org_number)
                for grant in grants:
                    signal = Signal(
                        signal_id=f"SIG-GRANT-{scan_id}-{grant.get('grant_type', 'unknown')}",
                        signal_type="grant_award",
                        entity_id=org_number,
                        source=connector_name,
                        value=grant,
                        confidence=0.88,
                        timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
                    )
                    self.observation_graph.add_signal(signal)
                    signals.append(signal)

            except Exception as e:
                # Log error but continue with other connectors
                logger.error(f"Error scanning {org_number} via {connector_name}: {str(e)}")
                continue

        # Detect anomalies
        anomalies = self.observation_graph.detect_anomalous_patterns(org_number)

        # Build result
        result = ScanResult(
            scan_id=scan_id,
            entity_id=org_number,
            entity_type="company",
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
            total_signals=len(signals),
            resolved_entities=resolved_count,
            anomalies_detected=len(anomalies),
            sources_consulted=sources_consulted,
            status="success" if signals else "partial",
        )

        self._scan_history[scan_id] = result
        return result

    def scan_person(self, person_id: str) -> ScanResult:
        """Scan a person across all registered connectors."""
        scan_id = f"SCAN-PERSON-{person_id}-{datetime.now(timezone.utc).replace(tzinfo=None).timestamp()}"
        signals = []
        resolved_count = 0
        sources_consulted = []

        for connector_name, connector in self.connectors.items():
            try:
                if not connector.is_healthy():
                    continue

                sources_consulted.append(connector_name)

                # Get person holdings
                holdings = connector.get_person_holdings(person_id)
                if holdings:
                    for holding in holdings:
                        signal = Signal(
                            signal_id=f"SIG-HOLDING-{scan_id}-{holding.get('org_number', 'unknown')}",
                            signal_type="stock_holding",
                            entity_id=person_id,
                            source=connector_name,
                            value=holding,
                            confidence=0.85,
                            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
                        )
                        self.observation_graph.add_signal(signal)
                        signals.append(signal)

                        # Create entity signature for the holding
                        sig = EntitySignature(
                            entity_type="holding",
                            primary_id=f"{person_id}-{holding.get('org_number')}",
                            source=connector_name,
                            additional_attrs=holding,
                        )
                        self.entity_resolution.add_entity(sig)
                        resolved_count += 1

            except Exception as e:
                logger.error(f"Error scanning person {person_id} via {connector_name}: {str(e)}")
                continue

        result = ScanResult(
            scan_id=scan_id,
            entity_id=person_id,
            entity_type="person",
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
            total_signals=len(signals),
            resolved_entities=resolved_count,
            anomalies_detected=0,
            sources_consulted=sources_consulted,
            status="success" if signals else "partial",
        )

        self._scan_history[scan_id] = result
        return result

    def get_scan_result(self, scan_id: str) -> Optional[ScanResult]:
        """Get previous scan result."""
        return self._scan_history.get(scan_id)

    def get_entity_intelligence(self, entity_id: str) -> Dict[str, Any]:
        """Get accumulated intelligence on an entity from observation graph.

        Returns:
            Intelligence report
        """
        entity_signals = self.observation_graph.get_entity_signals(entity_id)
        anomalies = self.observation_graph.detect_anomalous_patterns(entity_id)
        related = self.observation_graph.get_related_entities(entity_id)

        return {
            "entity_id": entity_id,
            "signal_count": len(entity_signals),
            "signals": [
                {
                    "signal_id": s.signal_id,
                    "signal_type": s.signal_type,
                    "source": s.source,
                    "value": str(s.value)[:200],  # truncate for readability
                    "confidence": s.confidence,
                    "timestamp": s.timestamp.isoformat(),
                }
                for s in entity_signals
            ],
            "anomalies": anomalies,
            "related_entities": [
                {"entity_id": e_id, "relation": rel.value}
                for e_id, rel in related
            ],
            "resolution_status": self._get_entity_resolution_status(entity_id),
        }

    def _get_entity_resolution_status(self, entity_id: str) -> Dict[str, Any]:
        """Get entity resolution status."""
        # Find clusters containing this entity
        matching_clusters = []
        for cluster in self.entity_resolution.clusters.values():
            if cluster.primary_entity.primary_id == entity_id or \
               any(e.primary_id == entity_id for e in cluster.equivalent_entities):
                matching_clusters.append({
                    "cluster_id": cluster.cluster_id,
                    "canonical_name": cluster.primary_entity.name,
                    "entity_count": 1 + len(cluster.equivalent_entities),
                    "sources": [cluster.primary_entity.source] + [e.source for e in cluster.equivalent_entities],
                    "confidence": cluster.confidence,
                })

        return {
            "entity_id": entity_id,
            "cluster_count": len(matching_clusters),
            "clusters": matching_clusters,
        }

    def get_scanner_statistics(self) -> Dict[str, Any]:
        """Get scanner statistics."""
        return {
            "tenant_id": self.tenant_id,
            "connectors_registered": len(self.connectors),
            "connectors": list(self.connectors.keys()),
            "scans_performed": len(self._scan_history),
            "entity_resolution": self.entity_resolution.get_resolution_stats(),
            "observation_graph": self.observation_graph.get_graph_statistics(),
        }
