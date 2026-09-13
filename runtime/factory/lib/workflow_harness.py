"""Provider-neutral, headless workflow harness for VALO Factory.

The harness owns orchestration only. Workflow primitives are independent of
provider, coding-agent harness and user interface. A caller selects a supported
model/provider and harness per invocation and may enter through any surface
(CLI, MCP, API, Workbench, voice, etc.).

Hard boundary: VAIG evaluates; REHT authorizes consequence-bearing execution;
RACS expresses the decision; Veritas records execution evidence. This module
does not expose an authority or execution surface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from lib.harness_provider_adapters import harness_ids
from lib.provider_entitlements import provider_ids


_PRIMITIVE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")
_AUTHORITY_PATH = ("vaig", "reht", "racs")


class WorkflowHarnessError(ValueError):
    """Base error for workflow-harness contract violations."""


class DuplicatePrimitiveError(WorkflowHarnessError):
    pass


class UnknownPrimitiveError(WorkflowHarnessError):
    pass


class UnsupportedProviderError(WorkflowHarnessError):
    pass


class UnsupportedHarnessError(WorkflowHarnessError):
    pass


@dataclass(frozen=True)
class WorkflowStep:
    """One provider-neutral workflow step.

    ``capability`` names what must be done; it does not name a provider, model,
    harness or concrete transport. Consequence-bearing steps declare the
    external governance path that must be satisfied before execution.
    """

    step_id: str
    capability: str
    consequence_bearing: bool = False
    authority_path: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not _PRIMITIVE_ID_RE.fullmatch(self.step_id):
            raise WorkflowHarnessError(f"invalid step_id={self.step_id!r}")
        if not self.capability.strip():
            raise WorkflowHarnessError("step capability must be non-empty")
        expected = _AUTHORITY_PATH if self.consequence_bearing else ()
        if self.authority_path != expected:
            raise WorkflowHarnessError(
                "authority_path must be empty for advisory steps and "
                "('vaig', 'reht', 'racs') for consequence-bearing steps"
            )


@dataclass(frozen=True)
class WorkflowPrimitive:
    """Canonical, provider- and harness-neutral workflow definition."""

    primitive_id: str
    version: int
    description: str
    steps: tuple[WorkflowStep, ...]
    required_capabilities: tuple[str, ...] = field(default_factory=tuple)
    authority_effect: str = "none"

    def __post_init__(self) -> None:
        if not _PRIMITIVE_ID_RE.fullmatch(self.primitive_id):
            raise WorkflowHarnessError(
                f"invalid primitive_id={self.primitive_id!r}"
            )
        if self.version < 1:
            raise WorkflowHarnessError("version must be >= 1")
        if not self.description.strip():
            raise WorkflowHarnessError("description must be non-empty")
        if not self.steps:
            raise WorkflowHarnessError("workflow primitive requires at least one step")
        step_ids = [step.step_id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            raise WorkflowHarnessError("workflow step_id values must be unique")
        if self.authority_effect != "none":
            raise WorkflowHarnessError("workflow primitives never grant authority")
        for capability in self.required_capabilities:
            if not capability.strip():
                raise WorkflowHarnessError(
                    "required_capabilities entries must be non-empty"
                )

    @property
    def canonical_ref(self) -> str:
        return f"{self.primitive_id}@{self.version}"

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, Any]:
        return {
            "primitive_id": self.primitive_id,
            "version": self.version,
            "description": self.description,
            "steps": [
                {
                    "step_id": step.step_id,
                    "capability": step.capability,
                    "consequence_bearing": step.consequence_bearing,
                    "authority_path": list(step.authority_path),
                }
                for step in self.steps
            ],
            "required_capabilities": list(self.required_capabilities),
            "authority_effect": self.authority_effect,
        }


@dataclass(frozen=True)
class WorkflowInvocation:
    """Headless invocation plan.

    This is an orchestration receipt/plan, not an execution permit.
    """

    invocation_id: str
    run_id: str
    primitive_ref: str
    primitive_digest: str
    surface_id: str
    provider_id: str
    harness_id: str
    actor_ref: str
    context_ref: str | None
    input_digest: str
    required_capabilities: tuple[str, ...]
    authority_effect: str = "none"

    def as_dict(self) -> dict[str, Any]:
        return {
            "invocation_id": self.invocation_id,
            "run_id": self.run_id,
            "primitive_ref": self.primitive_ref,
            "primitive_digest": self.primitive_digest,
            "surface_id": self.surface_id,
            "provider_id": self.provider_id,
            "harness_id": self.harness_id,
            "actor_ref": self.actor_ref,
            "context_ref": self.context_ref,
            "input_digest": self.input_digest,
            "required_capabilities": list(self.required_capabilities),
            "authority_effect": self.authority_effect,
        }


class HeadlessWorkflowHarness:
    """Registry + invocation planner for canonical workflow primitives."""

    def __init__(self, primitives: Sequence[WorkflowPrimitive] = ()) -> None:
        self._primitives: dict[str, WorkflowPrimitive] = {}
        for primitive in primitives:
            self.register(primitive)

    def register(self, primitive: WorkflowPrimitive) -> None:
        ref = primitive.canonical_ref
        if ref in self._primitives:
            raise DuplicatePrimitiveError(ref)
        self._primitives[ref] = primitive

    def resolve(self, primitive_ref: str) -> WorkflowPrimitive:
        try:
            return self._primitives[primitive_ref]
        except KeyError as exc:
            raise UnknownPrimitiveError(primitive_ref) from exc

    def primitive_refs(self) -> tuple[str, ...]:
        return tuple(sorted(self._primitives))

    def invoke(
        self,
        primitive_ref: str,
        *,
        run_id: str,
        surface_id: str,
        provider_id: str,
        actor_ref: str,
        inputs: Mapping[str, Any],
        context_ref: str | None = None,
        harness_id: str = "native",
    ) -> WorkflowInvocation:
        """Create a provider- and harness-bound, surface-neutral invocation plan.

        Provider and harness selection happen here, outside the primitive
        definition. No execution occurs.
        """

        primitive = self.resolve(primitive_ref)
        if provider_id not in provider_ids():
            raise UnsupportedProviderError(provider_id)
        if harness_id not in harness_ids():
            raise UnsupportedHarnessError(harness_id)
        for field_name, value in (
            ("run_id", run_id),
            ("surface_id", surface_id),
            ("actor_ref", actor_ref),
        ):
            if not value.strip():
                raise WorkflowHarnessError(f"{field_name} must be non-empty")

        return WorkflowInvocation(
            invocation_id=_invocation_id(
                run_id=run_id,
                primitive_ref=primitive_ref,
                surface_id=surface_id,
                provider_id=provider_id,
                harness_id=harness_id,
                actor_ref=actor_ref,
                context_ref=context_ref,
                inputs=inputs,
            ),
            run_id=run_id,
            primitive_ref=primitive_ref,
            primitive_digest=primitive.digest,
            surface_id=surface_id,
            provider_id=provider_id,
            harness_id=harness_id,
            actor_ref=actor_ref,
            context_ref=context_ref,
            input_digest=_digest(inputs),
            required_capabilities=tuple(
                sorted(set(primitive.required_capabilities))
            ),
        )

    @property
    def has_authority_surface(self) -> bool:
        return False

    @property
    def has_execution_surface(self) -> bool:
        return False


def _invocation_id(
    *,
    run_id: str,
    primitive_ref: str,
    surface_id: str,
    provider_id: str,
    harness_id: str,
    actor_ref: str,
    context_ref: str | None,
    inputs: Mapping[str, Any],
) -> str:
    payload = {
        "run_id": run_id,
        "primitive_ref": primitive_ref,
        "surface_id": surface_id,
        "provider_id": provider_id,
        "actor_ref": actor_ref,
        "context_ref": context_ref,
        "input_digest": _digest(inputs),
    }
    # Preserve legacy native invocation IDs while ensuring any non-native
    # harness choice is cryptographically bound to the invocation identity.
    if harness_id != "native":
        payload["harness_id"] = harness_id
    return f"wf-{_digest(payload)[:24]}"


def _digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


AUTHORITY_PATH = _AUTHORITY_PATH
SUPPORTED_SURFACE_EXAMPLES = (
    "cli",
    "mcp",
    "api",
    "workbench",
    "voice",
)


__all__ = [
    "AUTHORITY_PATH",
    "DuplicatePrimitiveError",
    "HeadlessWorkflowHarness",
    "SUPPORTED_SURFACE_EXAMPLES",
    "UnknownPrimitiveError",
    "UnsupportedHarnessError",
    "UnsupportedProviderError",
    "WorkflowHarnessError",
    "WorkflowInvocation",
    "WorkflowPrimitive",
    "WorkflowStep",
]
