"""Provider-neutral tool catalog inspired by Executor's integration model.

This layer discovers and describes tools. It never authorizes or executes them.
Consequence-bearing execution must pass through the canonical VALO chain and
REHT remains the sole final authorization boundary.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

PROGRAMMATIC_DISPATCH_PATH = ("Workflow ISA", "REHT", "RACS", "Gateway", "Veritas")


class ToolProtocol(StrEnum):
    MCP = "mcp"
    OPENAPI = "openapi"
    GRAPHQL = "graphql"
    CUSTOM = "custom"


class ToolDescriptor(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: str = Field(min_length=1)
    protocol: ToolProtocol
    endpoint_ref: str = Field(min_length=1)
    credential_ref: str | None = None
    operation: str = Field(min_length=1)
    mutates_external_state: bool = False
    consequence_bearing: bool = False
    required_authority_scope: str | None = None
    authority_effect: str = "none"
    final_authorization_boundary: str = "REHT"

    @model_validator(mode="after")
    def enforce_governance_boundary(self) -> ToolDescriptor:
        if self.authority_effect != "none":
            raise ValueError("tool metadata cannot grant authority")
        if self.final_authorization_boundary != "REHT":
            raise ValueError("REHT must remain the final authorization boundary")
        if self.consequence_bearing and not self.required_authority_scope:
            raise ValueError("consequence-bearing tools require an authority scope")
        if self.credential_ref and any(
            marker in self.credential_ref.lower()
            for marker in ("bearer ", "api_key=", "token=", "password=")
        ):
            raise ValueError("credential_ref must reference a secret location, not contain a secret")
        return self


class ProgrammaticToolCall(BaseModel):
    """Non-authoritative call envelope produced by agent-generated code.

    The envelope is deliberately not executable. A runtime outside Function
    Fabric must dispatch it through Workflow ISA and the canonical execution
    governance chain. Each consequence-bearing call requires a fresh state
    check at execution time; a prior permit is never carried as authority.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_id: str = Field(min_length=1)
    protocol: ToolProtocol
    endpoint_ref: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    arguments: dict[str, object] = Field(default_factory=dict)
    mutates_external_state: bool = False
    consequence_bearing: bool = False
    required_authority_scope: str | None = None
    authority_effect: str = "none"
    final_authorization_boundary: str = "REHT"
    dispatch_path: tuple[str, ...] = PROGRAMMATIC_DISPATCH_PATH
    direct_execution: bool = False
    state_recheck_required: bool = True

    @model_validator(mode="after")
    def enforce_programmatic_boundary(self) -> ProgrammaticToolCall:
        if self.authority_effect != "none":
            raise ValueError("programmatic calls cannot grant authority")
        if self.final_authorization_boundary != "REHT":
            raise ValueError("REHT must remain the final authorization boundary")
        if self.dispatch_path != PROGRAMMATIC_DISPATCH_PATH:
            raise ValueError("programmatic calls must use the canonical dispatch path")
        if self.direct_execution:
            raise ValueError("programmatic calls cannot execute tools directly")
        if self.consequence_bearing and not self.required_authority_scope:
            raise ValueError("consequence-bearing calls require an authority scope")
        if (self.consequence_bearing or self.mutates_external_state) and not self.state_recheck_required:
            raise ValueError("effectful programmatic calls require execution-time state re-check")
        return self


class ProgrammaticToolStub:
    """Callable agent surface that can only construct governed call envelopes."""

    def __init__(self, catalog: ToolCatalog, tool_id: str) -> None:
        self._catalog = catalog
        self.tool_id = tool_id
        self._catalog.resolve(tool_id)

    def __call__(self, **arguments: object) -> ProgrammaticToolCall:
        return self._catalog.compose_programmatic(self.tool_id, arguments)


class ToolCatalog:
    """Version-local catalog. Discovery is non-authoritative and deterministic."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDescriptor] = {}

    def register(self, tool: ToolDescriptor) -> None:
        if tool.tool_id in self._tools:
            raise ValueError(f"tool already registered: {tool.tool_id}")
        self._tools[tool.tool_id] = tool

    def resolve(self, tool_id: str) -> ToolDescriptor:
        try:
            return self._tools[tool_id]
        except KeyError as exc:
            raise KeyError(f"unknown tool: {tool_id}") from exc

    def list(self) -> tuple[ToolDescriptor, ...]:
        return tuple(self._tools[key] for key in sorted(self._tools))

    def project(self, tool_id: str, surface: str) -> dict[str, object]:
        """Project one canonical descriptor to an agent/tool surface.

        The projection deliberately carries no approval/allow decision. Surface
        policy may hide or request approval for a tool, but cannot authorize it.
        Programmatic composition is an exposure mode, never an execution bypass.
        """
        if surface not in {"mcp", "cli", "sdk", "agent", "programmatic"}:
            raise ValueError(f"unsupported projection surface: {surface}")
        tool = self.resolve(tool_id)
        projection: dict[str, object] = {
            "tool_id": tool.tool_id,
            "surface": surface,
            "protocol": tool.protocol.value,
            "endpoint_ref": tool.endpoint_ref,
            "operation": tool.operation,
            "mutates_external_state": tool.mutates_external_state,
            "consequence_bearing": tool.consequence_bearing,
            "required_authority_scope": tool.required_authority_scope,
            "authority_effect": "none",
            "final_authorization_boundary": "REHT",
        }
        if surface == "programmatic":
            projection.update(
                {
                    "programmatic_composition": True,
                    "direct_execution": False,
                    "state_recheck_required": True,
                    "dispatch_path": PROGRAMMATIC_DISPATCH_PATH,
                }
            )
        return projection

    def programmatic_stub(self, tool_id: str) -> ProgrammaticToolStub:
        """Expose a callable stub for agent-generated orchestration code."""
        return ProgrammaticToolStub(self, tool_id)

    def compose_programmatic(
        self,
        tool_id: str,
        arguments: dict[str, object] | None = None,
    ) -> ProgrammaticToolCall:
        """Lower one PTC call to a non-authoritative governed envelope."""
        tool = self.resolve(tool_id)
        return ProgrammaticToolCall(
            tool_id=tool.tool_id,
            protocol=tool.protocol,
            endpoint_ref=tool.endpoint_ref,
            operation=tool.operation,
            arguments=dict(arguments or {}),
            mutates_external_state=tool.mutates_external_state,
            consequence_bearing=tool.consequence_bearing,
            required_authority_scope=tool.required_authority_scope,
        )
