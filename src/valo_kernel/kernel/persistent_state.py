from __future__ import annotations

import hashlib

from ..contracts.persistent_state import PersistentStateBinding, PersistentStateKind
from ..contracts.workspace import GovernedWorkspaceEnvelope, ProjectedObject
from .errors import FailClosedError


def persistent_content_digest(content: str | bytes) -> str:
    raw = content.encode("utf-8") if isinstance(content, str) else content
    return hashlib.sha256(raw).hexdigest()


def _source_object(
    workspace: GovernedWorkspaceEnvelope,
    source_ref: str,
) -> ProjectedObject:
    sources = {item.ref: item for item in workspace.projection.objects}
    source = sources.get(source_ref)
    if source is None:
        raise FailClosedError("persistent state source is outside governed projection")
    if source.collection != "evidence":
        raise FailClosedError("persistent state must originate from admitted evidence")
    return source


def _validate_admitted_content(source: ProjectedObject, content_digest: str) -> None:
    if source.payload.get("status") != "ADMITTED":
        raise FailClosedError("persistent state evidence is not admitted")
    if source.payload.get("integrity_hash") != content_digest:
        raise FailClosedError("persistent state content differs from admitted evidence")


def seal_persistent_state_binding(
    workspace: GovernedWorkspaceEnvelope,
    *,
    persistent_ref: str,
    state_kind: PersistentStateKind,
    content: str | bytes,
    source_ref: str,
) -> PersistentStateBinding:
    if workspace.workspace_digest != workspace.computed_digest:
        raise FailClosedError("workspace is unsealed")
    source = _source_object(workspace, source_ref)
    content_digest = persistent_content_digest(content)
    _validate_admitted_content(source, content_digest)
    provisional = PersistentStateBinding(
        persistent_ref=persistent_ref,
        state_kind=state_kind,
        content_digest=content_digest,
        workspace_id=workspace.spec.workspace_id,
        workspace_digest=workspace.workspace_digest,
        source_state_root=workspace.projection.source_state_root,
        source_ref=source_ref,
        source_object_digest=source.payload_digest,
        purpose_id=workspace.spec.purpose_id,
    )
    return provisional.model_copy(
        update={"binding_digest": provisional.computed_digest}
    )


def verify_persistent_state_binding(
    workspace: GovernedWorkspaceEnvelope,
    binding: PersistentStateBinding,
    content: str | bytes,
) -> None:
    if workspace.workspace_digest != workspace.computed_digest:
        raise FailClosedError("workspace is unsealed")
    if binding.binding_digest != binding.computed_digest:
        raise FailClosedError("persistent state binding is unsealed")
    if (
        binding.workspace_id != workspace.spec.workspace_id
        or binding.workspace_digest != workspace.workspace_digest
    ):
        raise FailClosedError("persistent state is bound to another workspace")
    if binding.source_state_root != workspace.projection.source_state_root:
        raise FailClosedError("persistent state is bound to another state root")
    if binding.purpose_id != workspace.spec.purpose_id:
        raise FailClosedError("persistent state purpose binding mismatch")
    source = _source_object(workspace, binding.source_ref)
    if source.payload_digest != binding.source_object_digest:
        raise FailClosedError("persistent state source object changed")
    actual_digest = persistent_content_digest(content)
    if actual_digest != binding.content_digest:
        raise FailClosedError("persistent state content digest mismatch")
    _validate_admitted_content(source, actual_digest)
