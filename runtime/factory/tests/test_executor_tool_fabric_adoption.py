import json
from pathlib import Path


ROOT = Path(__file__).parent.parent


def test_executor_pattern_is_adopted_without_authority():
    adoption = json.loads(
        (ROOT / "config" / "executor-tool-fabric-adoption.json").read_text(encoding="utf-8")
    )

    assert adoption["adopt_as"] == "provider_neutral_governed_tool_fabric_pattern"
    assert adoption["implementation_owner"] == "nsolland/valo-function-fabric"
    assert adoption["authority_effect"] == "none"
    assert adoption["dependency_policy"] == "pattern_adoption_no_required_executor_runtime_dependency"

    for protocol_pattern in (
        "mcp_openapi_graphql_custom_function_normalization",
        "provider_neutral_tool_discovery",
        "replaceable_protocol_adapters",
    ):
        assert protocol_pattern in adoption["adopted_patterns"]

    assert "provider_policy_as_final_authorization" in adoption["explicit_non_adoptions"]
    assert adoption["canonical_execution_chain"] == [
        "agent_or_provider",
        "tool_catalog_and_projection",
        "VAIG",
        "REHT",
        "RACS",
        "execution_gateway",
        "external_tool_or_api",
        "Veritas_receipt",
    ]
    assert (
        "REHT remains the sole final authorization boundary for consequence-bearing execution."
        in adoption["invariants"]
    )
    assert (
        "Execution-time authorization must be fresh; prior approval does not substitute for REHT re-check."
        in adoption["invariants"]
    )
