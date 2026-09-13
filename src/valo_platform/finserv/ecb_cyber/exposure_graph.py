"""Exposure Graph — ECB Cyber Action Plan exposure and readiness model.

Wraps the existing KnowledgeGraph (triple store) behind a typed ExposureGraph
that models the ECB cyber-exposure edges:

    CriticalService  ──depends_on_asset──► SystemAsset
    CriticalService  ──depends_on_supplier──► Supplier
    BusinessProcess  ──relies_on_service──► CriticalService
    SystemAsset      ──has_control──► Control
    Supplier         ──supplies_asset──► SystemAsset

Persistence via JSON file (MVP; database later).

Design: Issue #214, Index DESIGN.md §3.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from src.valo_platform.semantics.knowledge_graph import KnowledgeGraph

# ---------------------------------------------------------------------------
# Edge-type constants (mapped to KnowledgeGraph predicates)
# ---------------------------------------------------------------------------
_PRED_DEPENDS_ON_ASSET = "depends_on_asset"
_PRED_DEPENDS_ON_SUPPLIER = "depends_on_supplier"
_PRED_RELIES_ON_SERVICE = "relies_on_service"
_PRED_HAS_CONTROL = "has_control"
_PRED_SUPPLIES_ASSET = "supplies_asset"

_EVIDENCE_ID = "ecb_exposure_graph"  # shared evidence-id placeholder


class ExposureGraph:
    """Typed exposure graph wrapping KnowledgeGraph.

    Wraps the platform's triple-store KnowledgeGraph with ECB-specific edge
    helpers and traversal queries.  All facts are stored inside a single
    KnowledgeGraph instance — no second graph engine is introduced.
    """

    def __init__(self) -> None:
        self._kg = KnowledgeGraph()

    # ------------------------------------------------------------------
    # Typed edge helpers
    # ------------------------------------------------------------------

    def link_service_to_asset(self, service_id: str, asset_id: str) -> None:
        """Record that CriticalService *depends on* SystemAsset."""
        self._kg.add_fact(
            subject=service_id,
            predicate=_PRED_DEPENDS_ON_ASSET,
            object_=asset_id,
            evidence_id=_EVIDENCE_ID,
        )

    def link_service_to_supplier(self, service_id: str, supplier_id: str) -> None:
        """Record that CriticalService *depends on* Supplier."""
        self._kg.add_fact(
            subject=service_id,
            predicate=_PRED_DEPENDS_ON_SUPPLIER,
            object_=supplier_id,
            evidence_id=_EVIDENCE_ID,
        )

    def link_process_to_service(self, process_id: str, service_id: str) -> None:
        """Record that BusinessProcess *relies on* CriticalService."""
        self._kg.add_fact(
            subject=process_id,
            predicate=_PRED_RELIES_ON_SERVICE,
            object_=service_id,
            evidence_id=_EVIDENCE_ID,
        )

    def link_asset_to_control(self, asset_id: str, control_id: str) -> None:
        """Record that SystemAsset *has* Control."""
        self._kg.add_fact(
            subject=asset_id,
            predicate=_PRED_HAS_CONTROL,
            object_=control_id,
            evidence_id=_EVIDENCE_ID,
        )

    def link_supplier_to_asset(self, supplier_id: str, asset_id: str) -> None:
        """Record that Supplier *supplies* SystemAsset."""
        self._kg.add_fact(
            subject=supplier_id,
            predicate=_PRED_SUPPLIES_ASSET,
            object_=asset_id,
            evidence_id=_EVIDENCE_ID,
        )

    # ------------------------------------------------------------------
    # Traversal queries
    # ------------------------------------------------------------------

    def assets_for_service(self, service_id: str) -> List[str]:
        """Return SystemAsset IDs that a CriticalService depends on."""
        return [
            f.object
            for f in self._kg.query(
                subject=service_id, predicate=_PRED_DEPENDS_ON_ASSET
            )
        ]

    def suppliers_for_service(self, service_id: str) -> List[str]:
        """Return Supplier IDs that a CriticalService depends on."""
        return [
            f.object
            for f in self._kg.query(
                subject=service_id, predicate=_PRED_DEPENDS_ON_SUPPLIER
            )
        ]

    def services_for_process(self, process_id: str) -> List[str]:
        """Return CriticalService IDs that a BusinessProcess relies on."""
        return [
            f.object
            for f in self._kg.query(
                subject=process_id, predicate=_PRED_RELIES_ON_SERVICE
            )
        ]

    def controls_for_asset(self, asset_id: str) -> List[str]:
        """Return Control IDs assigned to a SystemAsset."""
        return [
            f.object
            for f in self._kg.query(
                subject=asset_id, predicate=_PRED_HAS_CONTROL
            )
        ]

    def assets_for_supplier(self, supplier_id: str) -> List[str]:
        """Return SystemAsset IDs that a Supplier provides."""
        return [
            f.object
            for f in self._kg.query(
                subject=supplier_id, predicate=_PRED_SUPPLIES_ASSET
            )
        ]

    def services_without_assets(self) -> List[str]:
        """Return CriticalService IDs that have no linked SystemAssets."""
        all_services: Set[str] = set()
        linked_services: Set[str] = set()

        for f in self._kg.get_facts_by_predicate(_PRED_DEPENDS_ON_ASSET):
            all_services.add(f.subject)
            linked_services.add(f.subject)
        for f in self._kg.get_facts_by_predicate(_PRED_DEPENDS_ON_SUPPLIER):
            all_services.add(f.subject)

        return sorted(all_services - linked_services)

    def services_without_suppliers(self) -> List[str]:
        """Return CriticalService IDs that have no linked Suppliers."""
        all_services: Set[str] = set()
        linked_services: Set[str] = set()

        for f in self._kg.get_facts_by_predicate(_PRED_DEPENDS_ON_SUPPLIER):
            all_services.add(f.subject)
            linked_services.add(f.subject)
        for f in self._kg.get_facts_by_predicate(_PRED_DEPENDS_ON_ASSET):
            all_services.add(f.subject)

        return sorted(all_services - linked_services)

    def assets_without_controls(self) -> List[str]:
        """Return SystemAsset IDs that have no linked Controls."""
        all_assets: Set[str] = set()
        controlled_assets: Set[str] = set()

        for f in self._kg.get_facts_by_predicate(_PRED_DEPENDS_ON_ASSET):
            all_assets.add(f.object)
        for f in self._kg.get_facts_by_predicate(_PRED_SUPPLIES_ASSET):
            all_assets.add(f.object)
        for f in self._kg.get_facts_by_predicate(_PRED_HAS_CONTROL):
            controlled_assets.add(f.subject)

        return sorted(all_assets - controlled_assets)

    def readiness_aggregate(self) -> Dict[str, Any]:
        """Return aggregated counts and gaps for the dashboard.

        Structure consumed by issue #219 (dashboard).
        """
        all_services: Set[str] = set()
        for f in self._kg.query(predicate=_PRED_DEPENDS_ON_ASSET):
            all_services.add(f.subject)
        for f in self._kg.query(predicate=_PRED_DEPENDS_ON_SUPPLIER):
            all_services.add(f.subject)

        all_assets: Set[str] = set()
        for f in self._kg.query(predicate=_PRED_DEPENDS_ON_ASSET):
            all_assets.add(f.object)
        for f in self._kg.query(predicate=_PRED_SUPPLIES_ASSET):
            all_assets.add(f.object)

        all_suppliers: Set[str] = set()
        for f in self._kg.query(predicate=_PRED_DEPENDS_ON_SUPPLIER):
            all_suppliers.add(f.object)

        all_controls: Set[str] = set()
        for f in self._kg.query(predicate=_PRED_HAS_CONTROL):
            all_controls.add(f.object)

        return {
            "total_services": len(all_services),
            "total_assets": len(all_assets),
            "total_suppliers": len(all_suppliers),
            "total_controls": len(all_controls),
            "services_without_assets": self.services_without_assets(),
            "services_without_suppliers": self.services_without_suppliers(),
            "assets_without_controls": self.assets_without_controls(),
            "edge_counts": {
                "service_to_asset": len(
                    list(
                        self._kg.get_facts_by_predicate(
                            _PRED_DEPENDS_ON_ASSET
                        )
                    )
                ),
                "service_to_supplier": len(
                    list(
                        self._kg.get_facts_by_predicate(
                            _PRED_DEPENDS_ON_SUPPLIER
                        )
                    )
                ),
                "process_to_service": len(
                    list(
                        self._kg.get_facts_by_predicate(
                            _PRED_RELIES_ON_SERVICE
                        )
                    )
                ),
                "asset_to_control": len(
                    list(
                        self._kg.get_facts_by_predicate(_PRED_HAS_CONTROL)
                    )
                ),
                "supplier_to_asset": len(
                    list(
                        self._kg.get_facts_by_predicate(
                            _PRED_SUPPLIES_ASSET
                        )
                    )
                ),
            },
        }

    # ------------------------------------------------------------------
    # JSON-file persistence (MVP)
    # ------------------------------------------------------------------

    def save(self, path: str | Path) -> None:
        """Persist the graph to a JSON file.

        Serialises all triples from the underlying KnowledgeGraph.
        """
        triples = self._kg.export_as_triples()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(triples, indent=2, default=str))

    @classmethod
    def load(cls, path: str | Path) -> ExposureGraph:
        """Reconstruct an ExposureGraph from a JSON file saved by *save*."""
        graph = cls()
        triples = json.loads(Path(path).read_text())
        for t in triples:
            graph._kg.add_fact(
                subject=t["subject"],
                predicate=t["predicate"],
                object_=t["object"],
                evidence_id=t.get("evidence", _EVIDENCE_ID),
                certainty=t.get("certainty", 1.0),
                source=t.get("source", "unknown"),
            )
        return graph
