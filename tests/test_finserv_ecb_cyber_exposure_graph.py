"""QC tests for ECB Cyber Exposure Graph (issue #214).

Exercises: adding typed edges, querying them back, persistence round-trip,
and readiness_aggregate structure.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from src.valo_platform.finserv.ecb_cyber.exposure_graph import ExposureGraph

# ---------------------------------------------------------------------------
# Constants — synthetic Meridian Euro Bank scenario
# ---------------------------------------------------------------------------
SVC_TREASURY = "svc-treasury"
SVC_PAYMENTS = "svc-payments"
ASSET_RECON = "asset-recon"
ASSET_SWIFT = "asset-swift"
SUP_LEDGER_SYNC = "sup-ledger-sync"
SUP_SWIFT_NET = "sup-swift-net"
PROC_TREASURY_OPS = "proc-treasury-ops"
CTRL_FIDO2 = "ctrl-fido2"
CTRL_SIEM = "ctrl-siem"
CTRL_EDR = "ctrl-edr"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _populated_graph() -> ExposureGraph:
    """Build a standard graph used by several tests."""
    g = ExposureGraph()

    # CriticalService → SystemAsset
    g.link_service_to_asset(SVC_TREASURY, ASSET_RECON)
    g.link_service_to_asset(SVC_PAYMENTS, ASSET_SWIFT)

    # CriticalService → Supplier
    g.link_service_to_supplier(SVC_TREASURY, SUP_LEDGER_SYNC)
    g.link_service_to_supplier(SVC_PAYMENTS, SUP_SWIFT_NET)
    g.link_service_to_supplier(SVC_PAYMENTS, SUP_LEDGER_SYNC)

    # BusinessProcess → CriticalService
    g.link_process_to_service(PROC_TREASURY_OPS, SVC_TREASURY)
    g.link_process_to_service(PROC_TREASURY_OPS, SVC_PAYMENTS)

    # SystemAsset → Control
    g.link_asset_to_control(ASSET_RECON, CTRL_FIDO2)
    g.link_asset_to_control(ASSET_RECON, CTRL_SIEM)
    g.link_asset_to_control(ASSET_SWIFT, CTRL_EDR)

    # Supplier → SystemAsset
    g.link_supplier_to_asset(SUP_LEDGER_SYNC, ASSET_RECON)
    g.link_supplier_to_asset(SUP_SWIFT_NET, ASSET_SWIFT)

    return g


# ---------------------------------------------------------------------------
# Tests — add edges & query them back
# ---------------------------------------------------------------------------


def test_link_service_to_asset() -> None:
    g = ExposureGraph()
    g.link_service_to_asset(SVC_TREASURY, ASSET_RECON)
    assert g.assets_for_service(SVC_TREASURY) == [ASSET_RECON]


def test_link_service_to_supplier() -> None:
    g = ExposureGraph()
    g.link_service_to_supplier(SVC_TREASURY, SUP_LEDGER_SYNC)
    assert g.suppliers_for_service(SVC_TREASURY) == [SUP_LEDGER_SYNC]


def test_link_process_to_service() -> None:
    g = ExposureGraph()
    g.link_process_to_service(PROC_TREASURY_OPS, SVC_TREASURY)
    result = g.services_for_process(PROC_TREASURY_OPS)
    assert result == [SVC_TREASURY]


def test_link_asset_to_control() -> None:
    g = ExposureGraph()
    g.link_asset_to_control(ASSET_RECON, CTRL_FIDO2)
    assert g.controls_for_asset(ASSET_RECON) == [CTRL_FIDO2]


def test_link_supplier_to_asset() -> None:
    g = ExposureGraph()
    g.link_supplier_to_asset(SUP_LEDGER_SYNC, ASSET_RECON)
    result = g.assets_for_supplier(SUP_LEDGER_SYNC)
    assert result == [ASSET_RECON]


def test_full_graph_queries() -> None:
    """Verify all query types return expected results from the populated graph."""
    g = _populated_graph()

    # Assets per service
    assert sorted(g.assets_for_service(SVC_TREASURY)) == [ASSET_RECON]
    assert sorted(g.assets_for_service(SVC_PAYMENTS)) == [ASSET_SWIFT]

    # Suppliers per service
    assert sorted(g.suppliers_for_service(SVC_TREASURY)) == [SUP_LEDGER_SYNC]
    assert sorted(g.suppliers_for_service(SVC_PAYMENTS)) == [
        SUP_LEDGER_SYNC,
        SUP_SWIFT_NET,
    ]

    # Services per process
    assert sorted(g.services_for_process(PROC_TREASURY_OPS)) == [
        SVC_PAYMENTS,
        SVC_TREASURY,
    ]

    # Controls per asset
    assert sorted(g.controls_for_asset(ASSET_RECON)) == [
        CTRL_FIDO2,
        CTRL_SIEM,
    ]
    assert g.controls_for_asset(ASSET_SWIFT) == [CTRL_EDR]

    # Assets per supplier
    assert sorted(g.assets_for_supplier(SUP_LEDGER_SYNC)) == [ASSET_RECON]
    assert sorted(g.assets_for_supplier(SUP_SWIFT_NET)) == [ASSET_SWIFT]


# ---------------------------------------------------------------------------
# Tests — gap detection
# ---------------------------------------------------------------------------


def test_services_without_assets() -> None:
    """Services that have no depends_on_asset edges."""
    g = ExposureGraph()
    g.link_service_to_supplier(SVC_TREASURY, SUP_LEDGER_SYNC)  # no assets
    g.link_service_to_asset(SVC_PAYMENTS, ASSET_SWIFT)  # has asset
    assert g.services_without_assets() == [SVC_TREASURY]


def test_assets_without_controls() -> None:
    """Assets referenced in the graph but lacking has_control edges."""
    g = ExposureGraph()
    g.link_service_to_asset(SVC_TREASURY, ASSET_RECON)
    g.link_service_to_asset(SVC_TREASURY, ASSET_SWIFT)
    g.link_asset_to_control(ASSET_RECON, CTRL_FIDO2)
    assert g.assets_without_controls() == [ASSET_SWIFT]


def test_services_without_suppliers() -> None:
    g = ExposureGraph()
    g.link_service_to_asset(SVC_TREASURY, ASSET_RECON)  # no supplier
    g.link_service_to_supplier(SVC_PAYMENTS, SUP_LEDGER_SYNC)  # has supplier
    assert g.services_without_suppliers() == [SVC_TREASURY]


# ---------------------------------------------------------------------------
# Tests — persistence round-trip
# ---------------------------------------------------------------------------


def test_save_and_load_round_trip() -> None:
    g = _populated_graph()
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        tmp_path = f.name
    try:
        g.save(tmp_path)
        # Verify file exists and has JSON content
        raw = Path(tmp_path).read_text()
        data = json.loads(raw)
        assert len(data) > 0, "saved triples should not be empty"

        # Load into a fresh graph
        g2 = ExposureGraph.load(tmp_path)
        assert g2.assets_for_service(SVC_TREASURY) == [ASSET_RECON]
        assert sorted(g2.suppliers_for_service(SVC_PAYMENTS)) == [
            SUP_LEDGER_SYNC,
            SUP_SWIFT_NET,
        ]
        assert sorted(g2.controls_for_asset(ASSET_RECON)) == [
            CTRL_FIDO2,
            CTRL_SIEM,
        ]
        assert sorted(g2.services_for_process(PROC_TREASURY_OPS)) == [
            SVC_PAYMENTS,
            SVC_TREASURY,
        ]
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Tests — readiness_aggregate
# ---------------------------------------------------------------------------


def test_readiness_aggregate_empty_graph() -> None:
    g = ExposureGraph()
    agg = g.readiness_aggregate()
    assert agg["total_services"] == 0
    assert agg["total_assets"] == 0
    assert agg["total_suppliers"] == 0
    assert agg["total_controls"] == 0
    assert agg["services_without_assets"] == []
    assert agg["services_without_suppliers"] == []
    assert agg["assets_without_controls"] == []
    for v in agg["edge_counts"].values():
        assert v == 0


def test_readiness_aggregate_populated() -> None:
    g = _populated_graph()
    agg = g.readiness_aggregate()
    # 2 services, 2 assets, 2 suppliers, 3 controls
    assert agg["total_services"] == 2
    assert agg["total_assets"] == 2
    assert agg["total_suppliers"] == 2
    assert agg["total_controls"] == 3
    # Everyone covered
    assert agg["services_without_assets"] == []
    assert agg["services_without_suppliers"] == []
    assert agg["assets_without_controls"] == []
    # Edge counts
    assert agg["edge_counts"]["service_to_asset"] == 2
    assert agg["edge_counts"]["service_to_supplier"] == 3
    assert agg["edge_counts"]["process_to_service"] == 2
    assert agg["edge_counts"]["asset_to_control"] == 3
    assert agg["edge_counts"]["supplier_to_asset"] == 2
