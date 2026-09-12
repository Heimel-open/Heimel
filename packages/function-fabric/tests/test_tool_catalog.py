import pytest

from valo_function_fabric.tool_catalog import ToolCatalog, ToolDescriptor, ToolProtocol


def test_catalog_normalizes_multiple_tool_protocols_without_authority():
    catalog = ToolCatalog()
    for protocol in ToolProtocol:
        catalog.register(
            ToolDescriptor(
                tool_id=f"demo.{protocol.value}",
                protocol=protocol,
                endpoint_ref=f"registry://demo/{protocol.value}",
                operation="read",
            )
        )

    assert [item.protocol for item in catalog.list()] == sorted(ToolProtocol, key=lambda p: p.value)
    for tool in catalog.list():
        projected = catalog.project(tool.tool_id, "agent")
        assert projected["authority_effect"] == "none"
        assert projected["final_authorization_boundary"] == "REHT"


def test_consequence_bearing_tool_requires_authority_scope():
    with pytest.raises(ValueError, match="authority scope"):
        ToolDescriptor(
            tool_id="payments.send",
            protocol=ToolProtocol.OPENAPI,
            endpoint_ref="openapi://payments",
            operation="POST /payments",
            mutates_external_state=True,
            consequence_bearing=True,
        )


def test_credentials_are_references_not_secret_values():
    ToolDescriptor(
        tool_id="crm.lookup",
        protocol=ToolProtocol.GRAPHQL,
        endpoint_ref="graphql://crm",
        credential_ref="secret://vault/crm/service-account",
        operation="query Customer",
    )

    with pytest.raises(ValueError, match="secret location"):
        ToolDescriptor(
            tool_id="bad.secret",
            protocol=ToolProtocol.CUSTOM,
            endpoint_ref="custom://bad",
            credential_ref="token=plaintext",
            operation="invoke",
        )


def test_projection_never_carries_allow_or_approval_as_authority():
    catalog = ToolCatalog()
    catalog.register(
        ToolDescriptor(
            tool_id="prod.deploy",
            protocol=ToolProtocol.MCP,
            endpoint_ref="mcp://deployment",
            credential_ref="secret://vault/deploy/bot",
            operation="deploy",
            mutates_external_state=True,
            consequence_bearing=True,
            required_authority_scope="production.deploy",
        )
    )

    projected = catalog.project("prod.deploy", "mcp")
    assert "allow" not in projected
    assert "approved" not in projected
    assert projected["required_authority_scope"] == "production.deploy"
    assert projected["final_authorization_boundary"] == "REHT"

