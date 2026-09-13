import json

from valo_sdk import (
    CMCPInvocation,
    ProcurementProcedure,
    ProtocolStack,
    SurfaceConformanceObservationV1,
    evaluate_surface_conformance,
)
from valo_sdk.cli import main


def test_sdk_exposes_contracts_without_runtime_client():
    assert ProcurementProcedure("p", "t", "OPEN_PROCEDURE", "PLANNED").schema_version == "v1"
    assert ProtocolStack(transport="http", interaction_protocols=["mcp"]).transport == "http"
    assert CMCPInvocation.__name__ == "CMCPInvocation"


def test_sdk_conformance_api_remains_authority_neutral():
    report = evaluate_surface_conformance(SurfaceConformanceObservationV1(
        surface_id="x", surface_type="ui", creates_authority=True,
    ))
    assert report.passed is False
    assert report.can_issue_clearance is False


def test_cli_lists_contract_surface(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["valo-contracts", "list"])
    main()
    payload = json.loads(capsys.readouterr().out)
    assert "CMCPContractV1" in payload["contracts"]
    assert payload["network"] is False
    assert payload["authority"] is False
