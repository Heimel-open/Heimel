import json

from valo_sdk import (
    CMCPInvocation,
    ProcurementProcedure,
    ProtocolStack,
    SurfaceConformanceObservationV1,
    evaluate_surface_conformance,
)
from valo_sdk.cli import main
from valo_sdk.demo import run_demo


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


def test_offline_end_to_end_demo_has_no_effect_path():
    result = run_demo()
    assert result["mal_decision"] == "IMPORT_FOR_LOCAL_REVIEW"
    assert result["c_mcp_verification"] == (True, "ok")
    assert result["conformance_passed"] is True
    assert result["authority_granted"] is False
    assert result["external_effect"] is False
