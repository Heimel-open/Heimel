from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .contracts import GovernedWorkspaceEnvelope, canonical_digest

UHP_PROTOCOL_VERSION = "2026-08-11"
UHP_WORKER_BOUNDARY_INSTRUCTION = (
    "Produce candidate work, artifacts, and proposed actions only. "
    "Do not perform consequence-bearing external actions. "
    "Any proposed effect requires fresh VALO authorization outside this harness."
)


class UHPConformanceClass(StrEnum):
    CORE = "core"
    EXTENDED = "extended"
    FULL = "full"


class UHPTaskStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    INCOMPLETE = "incomplete"
    CANCELLED = "cancelled"


class UHPAdapterManifest(BaseModel):
    schema_version: Literal["uhp_adapter_manifest.v1"] = "uhp_adapter_manifest.v1"
    adapter_id: Literal["uhp.worker.reference.v1"] = "uhp.worker.reference.v1"
    protocol: Literal["Unified Harness Protocol"] = "Unified Harness Protocol"
    protocol_version: Literal["2026-08-11"] = UHP_PROTOCOL_VERSION
    role: Literal["WORKER_TRANSPORT_PROJECTION"] = "WORKER_TRANSPORT_PROJECTION"
    migration_target: Literal["valo-external-adapters"] = "valo-external-adapters"
    actual_network_io: Literal[False] = False
    can_execute_external_effects: Literal[False] = False
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    uhp_conformance_is_execution_governance: Literal[False] = False
    uhp_tool_policy_is_authority: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)


UHP_ADAPTER_MANIFEST = UHPAdapterManifest()


class UHPDiscoveryDocument(BaseModel):
    object: Literal["uhp.discovery"] = "uhp.discovery"
    protocol: Literal["uhp"] = "uhp"
    versions: tuple[str, ...]
    default_version: str
    conformance_class: UHPConformanceClass
    capabilities: dict[str, bool]
    implementation: dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow", frozen=True)

    @model_validator(mode="after")
    def validate_discovery(self) -> UHPDiscoveryDocument:
        if not self.versions:
            raise ValueError("UHP discovery versions must not be empty")
        if self.default_version not in self.versions:
            raise ValueError("UHP default version must be present in versions")
        if UHP_PROTOCOL_VERSION not in self.versions:
            raise ValueError(
                f"UHP server does not support required version {UHP_PROTOCOL_VERSION}"
            )
        if self.conformance_class in {
            UHPConformanceClass.EXTENDED,
            UHPConformanceClass.FULL,
        }:
            required = ("files_input", "files_output", "session_listing")
            missing = [name for name in required if not self.capabilities.get(name, False)]
            if missing:
                raise ValueError(
                    "UHP conformance class contradicts capabilities: "
                    + ", ".join(missing)
                )
        return self

    def supports(self, capability: str) -> bool:
        return bool(self.capabilities.get(capability, False))


class UHPHarnessDescriptor(BaseModel):
    id: str = Field(pattern=r"^chrn_[A-Za-z0-9_-]+$")
    object: Literal["harness"] = "harness"
    name: str
    base: str
    base_label: str | None = Field(default=None, alias="baseLabel")
    default_model: str | None = Field(default=None, alias="defaultModel")
    system_prompt: str | None = Field(default=None, alias="systemPrompt")
    mcp_servers: tuple[dict[str, Any], ...] = Field(default=(), alias="mcpServers")
    skills: tuple[dict[str, Any], ...] = ()
    disabled_tools: tuple[str, ...] = Field(default=(), alias="disabledTools")
    max_step: int | None = Field(default=None, alias="maxStep", ge=1)
    timeout_seconds: int | None = Field(default=None, alias="timeoutSeconds", ge=1)
    created_at: int = Field(alias="createdAt", ge=0)

    model_config = ConfigDict(extra="allow", frozen=True, populate_by_name=True)

    @model_validator(mode="after")
    def validate_harness(self) -> UHPHarnessDescriptor:
        if not self.name.strip():
            raise ValueError("UHP harness name is required")
        if not self.base.strip():
            raise ValueError("UHP harness base is required")
        return self

    @property
    def descriptor_digest(self) -> str:
        return canonical_digest(self.model_dump(mode="json", by_alias=True))

    @property
    def tool_enforcement_assurance(self) -> Literal["UNVERIFIED_BY_UHP"]:
        return "UNVERIFIED_BY_UHP"


class UHPHttpRequestProjection(BaseModel):
    schema_version: Literal["uhp_http_request_projection.v1"] = (
        "uhp_http_request_projection.v1"
    )
    method: Literal["GET", "POST", "DELETE"]
    path: str
    protocol_version: Literal["2026-08-11"] = UHP_PROTOCOL_VERSION
    requires_bearer_auth: bool
    headers: dict[str, str]
    body: dict[str, Any] | None = None
    request_digest: str = ""
    actual_network_io: Literal[False] = False
    can_execute_external_effects: Literal[False] = False
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"request_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_projection(self) -> UHPHttpRequestProjection:
        if not self.path.startswith("/v1/"):
            raise ValueError("UHP request path must stay under /v1/")
        lowered = {key.lower(): value for key, value in self.headers.items()}
        if "authorization" in lowered:
            raise ValueError("UHP request projection must not persist bearer credentials")
        if lowered.get("uhp-version") != UHP_PROTOCOL_VERSION:
            raise ValueError("UHP request projection must pin protocol version")
        if self.request_digest and self.request_digest != self.computed_digest:
            raise ValueError("UHP request projection digest mismatch")
        return self


class UHPWorkerTaskBinding(BaseModel):
    schema_version: Literal["uhp_worker_task_binding.v1"] = "uhp_worker_task_binding.v1"
    request_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    adapter_id: Literal["uhp.worker.reference.v1"] = "uhp.worker.reference.v1"
    workspace_id: str
    workspace_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    work_unit_id: str
    tenant_id: str
    purpose_id: str
    projection_id: str
    projection_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    worker_id: str
    harness_id: str = Field(pattern=r"^chrn_[A-Za-z0-9_-]+$")
    harness_base: str
    harness_descriptor_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    requested_model: str | None = None
    input_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    instruction_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    previous_response_id: str | None = None
    idempotency_key: str
    effect_isolation_ref: str
    effect_isolation_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    max_step: int | None = Field(default=None, ge=1)
    timeout_seconds: int | None = Field(default=None, ge=1)
    constructed_at: datetime
    binding_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    can_execute_external_effects: Literal[False] = False
    requires_fresh_authority_evaluation: Literal[True] = True

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"binding_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_binding(self) -> UHPWorkerTaskBinding:
        required = (
            self.workspace_id,
            self.work_unit_id,
            self.tenant_id,
            self.purpose_id,
            self.projection_id,
            self.worker_id,
            self.harness_base,
            self.idempotency_key,
            self.effect_isolation_ref,
        )
        if any(not value or not value.strip() for value in required):
            raise ValueError("UHP worker binding identity and isolation evidence are required")
        if self.previous_response_id is not None and not self.previous_response_id.startswith(
            "resp_"
        ):
            raise ValueError("previous_response_id must be a UHP response id")
        if self.binding_digest and self.binding_digest != self.computed_digest:
            raise ValueError("UHP worker task binding digest mismatch")
        return self


class UHPArtifactReference(BaseModel):
    container_id: str
    file_id: str
    filename: str
    download_url: str
    trust: Literal["ATTACKER_INFLUENCED"] = "ATTACKER_INFLUENCED"
    authoritative_state: Literal[False] = False
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("container_id", "file_id")
    @classmethod
    def prevent_path_traversal(cls, value: str) -> str:
        lowered = value.lower()
        if not value or "/" in value or "\\" in value or ".." in value or "%2e" in lowered:
            raise ValueError("UHP artifact identifiers must not contain path traversal syntax")
        return value


class UHPWorkerResultEvidence(BaseModel):
    schema_version: Literal["uhp_worker_result_evidence.v1"] = (
        "uhp_worker_result_evidence.v1"
    )
    request_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    binding_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    workspace_id: str
    workspace_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    worker_id: str
    harness_id: str
    harness_base: str
    response_id: str
    session_id: str
    status: UHPTaskStatus
    actual_model: str
    requested_model: str | None = None
    model_fallback: bool = False
    model_fallback_reason: str | None = None
    response_protocol_version: Literal["2026-08-11"] = UHP_PROTOCOL_VERSION
    output_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    response_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_refs: tuple[UHPArtifactReference, ...] = ()
    observed_tool_calls: tuple[str, ...] = ()
    observed_at: datetime
    evidence_digest: str = ""
    worker_output_role: Literal["CANDIDATE_ONLY"] = "CANDIDATE_ONLY"
    artifact_trust: Literal["ATTACKER_INFLUENCED"] = "ATTACKER_INFLUENCED"
    tool_enforcement_assurance: Literal["UNVERIFIED_BY_UHP"] = "UNVERIFIED_BY_UHP"
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    can_execute_external_effects: Literal[False] = False
    completed_is_clearance: Literal[False] = False
    requires_fresh_authority_evaluation: Literal[True] = True
    requires_model_readmission: bool = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"evidence_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_evidence(self) -> UHPWorkerResultEvidence:
        required = (
            self.workspace_id,
            self.worker_id,
            self.harness_id,
            self.harness_base,
            self.response_id,
            self.session_id,
            self.actual_model,
        )
        if any(not value or not value.strip() for value in required):
            raise ValueError("UHP worker result identity is required")
        if not self.response_id.startswith("resp_"):
            raise ValueError("response_id must be a UHP response id")
        expected_readmission = bool(
            self.requested_model and self.actual_model != self.requested_model
        )
        if self.requires_model_readmission != expected_readmission:
            raise ValueError("model readmission flag does not match actual model substitution")
        if self.model_fallback != expected_readmission:
            raise ValueError("model fallback evidence does not match requested/actual model")
        if self.model_fallback and not self.model_fallback_reason:
            raise ValueError("model fallback requires a reason")
        if self.evidence_digest and self.evidence_digest != self.computed_digest:
            raise ValueError("UHP worker result evidence digest mismatch")
        return self


def _seal_projection(projection: UHPHttpRequestProjection) -> UHPHttpRequestProjection:
    return UHPHttpRequestProjection.model_validate(
        {
            **projection.model_dump(mode="python"),
            "request_digest": projection.computed_digest,
        }
    )


def build_uhp_discovery_request() -> UHPHttpRequestProjection:
    return _seal_projection(
        UHPHttpRequestProjection(
            method="GET",
            path="/v1/uhp",
            requires_bearer_auth=False,
            headers={"UHP-Version": UHP_PROTOCOL_VERSION},
        )
    )


def record_uhp_discovery(
    *,
    payload: dict[str, Any],
    response_headers: dict[str, str],
) -> UHPDiscoveryDocument:
    version = _header(response_headers, "UHP-Version")
    if version != UHP_PROTOCOL_VERSION:
        raise ValueError("UHP discovery response protocol version mismatch")
    return UHPDiscoveryDocument.model_validate(payload)


def build_uhp_worker_task(
    *,
    workspace: GovernedWorkspaceEnvelope,
    discovery: UHPDiscoveryDocument,
    harness: UHPHarnessDescriptor,
    worker_id: str,
    input_text: str,
    effect_isolation_ref: str,
    effect_isolation_digest: str,
    constructed_at: datetime,
    requested_model: str | None = None,
    previous_response_id: str | None = None,
    instructions: str | None = None,
    max_step: int | None = None,
    timeout_seconds: int | None = None,
) -> tuple[UHPWorkerTaskBinding, UHPHttpRequestProjection]:
    if workspace.workspace_digest != workspace.computed_digest:
        raise ValueError("governed workspace must be sealed before UHP projection")
    if constructed_at.tzinfo is None or constructed_at.utcoffset() is None:
        raise ValueError("constructed_at must be timezone-aware")
    if not (workspace.projection.projected_at <= constructed_at < workspace.spec.expires_at):
        raise ValueError("governed workspace is not fresh for UHP worker projection")
    if not input_text or not input_text.strip():
        raise ValueError("UHP worker input must not be empty")
    if not worker_id or not worker_id.strip():
        raise ValueError("worker_id is required")
    if not effect_isolation_ref or not effect_isolation_ref.strip():
        raise ValueError("effect isolation evidence reference is required")
    if len(effect_isolation_digest) != 64 or any(
        ch not in "0123456789abcdef" for ch in effect_isolation_digest
    ):
        raise ValueError("effect isolation evidence digest must be lowercase SHA-256")
    if UHP_PROTOCOL_VERSION not in discovery.versions:
        raise ValueError("UHP protocol version is not admitted")
    if not discovery.supports("idempotency"):
        raise ValueError("UHP server must advertise idempotency for governed worker execution")
    if previous_response_id is not None and not discovery.supports("sessions"):
        raise ValueError("UHP server must advertise sessions before continuation")

    projection_digest = canonical_digest(workspace.projection.model_dump(mode="json"))
    input_digest = canonical_digest({"input": input_text})
    effective_instructions = _effective_instructions(instructions)
    instruction_digest = canonical_digest({"instructions": effective_instructions})
    harness_digest = harness.descriptor_digest
    stable_request = {
        "workspace_digest": workspace.workspace_digest,
        "projection_digest": projection_digest,
        "worker_id": worker_id,
        "harness_id": harness.id,
        "harness_descriptor_digest": harness_digest,
        "requested_model": requested_model,
        "input_digest": input_digest,
        "instruction_digest": instruction_digest,
        "previous_response_id": previous_response_id,
        "effect_isolation_digest": effect_isolation_digest,
    }
    request_id = canonical_digest(stable_request)
    idempotency_key = f"valo-uhp-{request_id}"

    unsealed = UHPWorkerTaskBinding(
        request_id=request_id,
        workspace_id=workspace.spec.workspace_id,
        workspace_digest=workspace.workspace_digest,
        work_unit_id=workspace.spec.work_unit_id,
        tenant_id=workspace.spec.tenant_id,
        purpose_id=workspace.spec.purpose_id,
        projection_id=workspace.projection.projection_id,
        projection_digest=projection_digest,
        worker_id=worker_id,
        harness_id=harness.id,
        harness_base=harness.base,
        harness_descriptor_digest=harness_digest,
        requested_model=requested_model,
        input_digest=input_digest,
        instruction_digest=instruction_digest,
        previous_response_id=previous_response_id,
        idempotency_key=idempotency_key,
        effect_isolation_ref=effect_isolation_ref,
        effect_isolation_digest=effect_isolation_digest,
        max_step=max_step,
        timeout_seconds=timeout_seconds,
        constructed_at=constructed_at,
    )
    binding = UHPWorkerTaskBinding.model_validate(
        {
            **unsealed.model_dump(mode="python"),
            "binding_digest": unsealed.computed_digest,
        }
    )

    body: dict[str, Any] = {
        "input": input_text,
        "metadata": {
            "harness_id": harness.id,
            "valo_request_id": request_id,
            "valo_workspace_id": workspace.spec.workspace_id,
            "valo_workspace_digest": workspace.workspace_digest,
            "valo_worker_id": worker_id,
        },
        "stream": False,
        "store": True,
        "instructions": effective_instructions,
    }
    if requested_model is not None:
        body["model"] = requested_model
    if previous_response_id is not None:
        body["previous_response_id"] = previous_response_id
    if max_step is not None:
        body["max_step"] = max_step
    if timeout_seconds is not None:
        body["timeout_seconds"] = timeout_seconds

    projection = _seal_projection(
        UHPHttpRequestProjection(
            method="POST",
            path="/v1/responses",
            requires_bearer_auth=True,
            headers={
                "Content-Type": "application/json",
                "UHP-Version": UHP_PROTOCOL_VERSION,
                "Idempotency-Key": idempotency_key,
            },
            body=body,
        )
    )
    return binding, projection


def record_uhp_worker_result(
    *,
    binding: UHPWorkerTaskBinding,
    response_payload: dict[str, Any],
    response_headers: dict[str, str],
    observed_at: datetime,
) -> UHPWorkerResultEvidence:
    if binding.binding_digest != binding.computed_digest:
        raise ValueError("UHP worker task binding is unsealed or tampered")
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("observed_at must be timezone-aware")
    version = _header(response_headers, "UHP-Version")
    if version != UHP_PROTOCOL_VERSION:
        raise ValueError("UHP worker response protocol version mismatch")

    response_id = _required_string(response_payload, "id")
    status = UHPTaskStatus(_required_string(response_payload, "status"))
    actual_model = _required_string(response_payload, "model")
    metadata = response_payload.get("metadata")
    if not isinstance(metadata, dict):
        raise TypeError("UHP response metadata must be an object")
    session_id = _required_string(metadata, "session_id")
    returned_harness = metadata.get("harness_id")
    if returned_harness is not None and returned_harness != binding.harness_id:
        raise ValueError("UHP response harness binding mismatch")

    requested_model = binding.requested_model
    model_fallback = bool(requested_model and actual_model != requested_model)
    reported_fallback = metadata.get("model_fallback")
    if model_fallback and reported_fallback is not True:
        raise ValueError("UHP model substitution was not explicitly reported")
    fallback_reason = metadata.get("model_fallback_reason") if model_fallback else None
    if model_fallback and (not isinstance(fallback_reason, str) or not fallback_reason.strip()):
        raise ValueError("UHP model substitution did not include a reason")

    output = response_payload.get("output")
    if not isinstance(output, list):
        raise TypeError("UHP response output must be an array")
    artifacts = _extract_artifacts(output)
    tool_calls = _extract_tool_calls(output)

    unsealed = UHPWorkerResultEvidence(
        request_id=binding.request_id,
        binding_digest=binding.binding_digest,
        workspace_id=binding.workspace_id,
        workspace_digest=binding.workspace_digest,
        worker_id=binding.worker_id,
        harness_id=binding.harness_id,
        harness_base=binding.harness_base,
        response_id=response_id,
        session_id=session_id,
        status=status,
        actual_model=actual_model,
        requested_model=requested_model,
        model_fallback=model_fallback,
        model_fallback_reason=fallback_reason,
        output_digest=canonical_digest(output),
        response_digest=canonical_digest(response_payload),
        artifact_refs=artifacts,
        observed_tool_calls=tool_calls,
        observed_at=observed_at,
        requires_model_readmission=model_fallback,
    )
    return UHPWorkerResultEvidence.model_validate(
        {
            **unsealed.model_dump(mode="python"),
            "evidence_digest": unsealed.computed_digest,
        }
    )


def build_uhp_cancel_request(
    *, binding: UHPWorkerTaskBinding, response_id: str
) -> UHPHttpRequestProjection:
    if binding.binding_digest != binding.computed_digest:
        raise ValueError("UHP worker task binding is unsealed or tampered")
    _require_safe_id(response_id, "response_id")
    if not response_id.startswith("resp_"):
        raise ValueError("response_id must be a UHP response id")
    return _seal_projection(
        UHPHttpRequestProjection(
            method="POST",
            path=f"/v1/responses/{response_id}/cancel",
            requires_bearer_auth=True,
            headers={"UHP-Version": UHP_PROTOCOL_VERSION},
        )
    )


def build_uhp_artifact_list_request(
    *, evidence: UHPWorkerResultEvidence
) -> UHPHttpRequestProjection:
    if evidence.evidence_digest != evidence.computed_digest:
        raise ValueError("UHP worker result evidence is unsealed or tampered")
    _require_safe_id(evidence.session_id, "session_id")
    return _seal_projection(
        UHPHttpRequestProjection(
            method="GET",
            path=f"/v1/sessions/{evidence.session_id}/files",
            requires_bearer_auth=True,
            headers={"UHP-Version": UHP_PROTOCOL_VERSION},
        )
    )


def build_uhp_artifact_content_request(
    *, artifact: UHPArtifactReference
) -> UHPHttpRequestProjection:
    _require_safe_id(artifact.container_id, "container_id")
    _require_safe_id(artifact.file_id, "file_id")
    return _seal_projection(
        UHPHttpRequestProjection(
            method="GET",
            path=(
                f"/v1/containers/{artifact.container_id}/files/"
                f"{artifact.file_id}/content"
            ),
            requires_bearer_auth=True,
            headers={"UHP-Version": UHP_PROTOCOL_VERSION},
        )
    )


def _effective_instructions(instructions: str | None) -> str:
    if instructions is None or not instructions.strip():
        return UHP_WORKER_BOUNDARY_INSTRUCTION
    return f"{UHP_WORKER_BOUNDARY_INSTRUCTION}\n\nTask guidance:\n{instructions.strip()}"


def _header(headers: dict[str, str], name: str) -> str | None:
    wanted = name.lower()
    for key, value in headers.items():
        if key.lower() == wanted:
            return value
    return None


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"UHP response field {key} is required")
    return value


def _require_safe_id(value: str, field_name: str) -> None:
    lowered = value.lower()
    if not value or "/" in value or "\\" in value or ".." in value or "%2e" in lowered:
        raise ValueError(f"{field_name} contains unsafe path syntax")


def _extract_artifacts(output: list[Any]) -> tuple[UHPArtifactReference, ...]:
    artifacts: list[UHPArtifactReference] = []
    seen: set[tuple[str, str]] = set()
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            annotations = part.get("annotations")
            if not isinstance(annotations, list):
                continue
            for annotation in annotations:
                if not isinstance(annotation, dict):
                    continue
                if annotation.get("type") != "container_file_citation":
                    continue
                artifact = UHPArtifactReference(
                    container_id=_required_string(annotation, "container_id"),
                    file_id=_required_string(annotation, "file_id"),
                    filename=_required_string(annotation, "filename"),
                    download_url=_required_string(annotation, "download_url"),
                )
                key = (artifact.container_id, artifact.file_id)
                if key not in seen:
                    artifacts.append(artifact)
                    seen.add(key)
    return tuple(artifacts)


def _extract_tool_calls(output: list[Any]) -> tuple[str, ...]:
    calls: list[str] = []
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "function_call":
            continue
        name = item.get("name")
        if isinstance(name, str) and name.strip():
            calls.append(name)
    return tuple(calls)
