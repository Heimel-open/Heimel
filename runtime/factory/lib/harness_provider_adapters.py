"""Replaceable coding-agent harness contracts for VALO Factory.

Harness selection is separate from model/provider selection. A harness may
orchestrate a provider, but it never creates authority. This module plans only;
it does not authorize, execute, merge, deploy, or attest success.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from types import MappingProxyType
from typing import Mapping


class HarnessProviderError(ValueError):
    pass


class UnknownHarnessProviderError(HarnessProviderError):
    pass


class UnsupportedHarnessModeError(HarnessProviderError):
    pass


class UnsupportedHarnessProviderMappingError(HarnessProviderError):
    pass


@dataclass(frozen=True)
class HarnessProviderSpec:
    harness_id: str
    product: str
    binary: str | None
    upstream_ref: str | None
    self_development_allowed: bool = False
    authority_effect: str = "none"


@dataclass(frozen=True)
class HarnessExecutionPlan:
    harness_id: str
    provider_id: str
    execution_mode: str
    prompt_digest: str
    command_surface: tuple[str, ...]
    prompt_transport: str
    self_development_allowed: bool
    authority_effect: str = "none"

    def as_dict(self) -> dict:
        return {
            "harness_id": self.harness_id,
            "provider_id": self.provider_id,
            "execution_mode": self.execution_mode,
            "prompt_digest": self.prompt_digest,
            "command_surface": list(self.command_surface),
            "prompt_transport": self.prompt_transport,
            "self_development_allowed": self.self_development_allowed,
            "authority_effect": self.authority_effect,
        }


_HARNESS_SPECS = {
    "native": HarnessProviderSpec(
        harness_id="native",
        product="VALO native provider adapter path",
        binary=None,
        upstream_ref=None,
    ),
    "jcode": HarnessProviderSpec(
        harness_id="jcode",
        product="jcode coding-agent harness",
        binary="jcode",
        upstream_ref="1jehuang/jcode@dd8755f7e71f0673911d481b625b8a559c81a8b6",
    ),
    "muse_code": HarnessProviderSpec(
        harness_id="muse_code",
        product="Meta Muse Code coding-agent harness",
        binary=None,
        upstream_ref=(
            "https://research.meta.ai/blog/introducing-muse-code-and-muse-spark-1-2"
        ),
    ),
}

HARNESS_PROVIDER_SPECS: Mapping[str, HarnessProviderSpec] = MappingProxyType(
    _HARNESS_SPECS
)

# Keep VALO provider identity stable while allowing jcode to route to the
# corresponding upstream runtime. Harness choice never replaces provider_id.
_JCODE_PROVIDER_MAP = MappingProxyType(
    {
        "openai_codex": "openai",
        "anthropic_claude_code": "claude",
        "google_antigravity": "antigravity",
        "github_copilot": "copilot",
    }
)


def harness_ids() -> tuple[str, ...]:
    return tuple(HARNESS_PROVIDER_SPECS)


def get_harness_spec(harness_id: str) -> HarnessProviderSpec:
    try:
        return HARNESS_PROVIDER_SPECS[harness_id]
    except KeyError as exc:
        raise UnknownHarnessProviderError(harness_id) from exc


def plan_harness_execution(
    harness_id: str,
    provider_id: str,
    prompt: str,
    *,
    execution_mode: str = "workspace_write",
) -> HarnessExecutionPlan:
    """Return a bounded harness command plan without executing it.

    External harnesses fail closed unless their exact non-interactive command
    surface and execution-mode controls are documented and conformance-tested.
    Registering a harness identity is therefore separate from enabling it.
    """
    spec = get_harness_spec(harness_id)
    if not prompt.strip():
        raise HarnessProviderError("prompt must not be empty")

    if harness_id == "native":
        return HarnessExecutionPlan(
            harness_id=harness_id,
            provider_id=provider_id,
            execution_mode=execution_mode,
            prompt_digest=_digest(prompt),
            command_surface=(),
            prompt_transport="delegated_to_provider_adapter",
            self_development_allowed=False,
        )

    if harness_id == "muse_code":
        raise UnsupportedHarnessModeError(
            "Muse Code is registered as a replaceable harness identity but remains "
            "fail-closed until a bounded non-interactive CLI contract and execution-mode "
            "controls are documented and conformance-tested"
        )

    if execution_mode != "workspace_write":
        raise UnsupportedHarnessModeError(
            "jcode is gated to workspace_write until a documented read-only "
            "wrapper contract is conformance-tested"
        )

    try:
        upstream_provider = _JCODE_PROVIDER_MAP[provider_id]
    except KeyError as exc:
        raise UnsupportedHarnessProviderMappingError(provider_id) from exc

    return HarnessExecutionPlan(
        harness_id="jcode",
        provider_id=provider_id,
        execution_mode=execution_mode,
        prompt_digest=_digest(prompt),
        command_surface=(
            "jcode",
            "--quiet",
            "--no-update",
            "--no-selfdev",
            "--provider",
            upstream_provider,
            "run",
            "--json",
            "<PROMPT>",
        ),
        prompt_transport="argument",
        self_development_allowed=False,
    )


def _digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__ = [
    "HARNESS_PROVIDER_SPECS",
    "HarnessExecutionPlan",
    "HarnessProviderError",
    "HarnessProviderSpec",
    "UnknownHarnessProviderError",
    "UnsupportedHarnessModeError",
    "UnsupportedHarnessProviderMappingError",
    "get_harness_spec",
    "harness_ids",
    "plan_harness_execution",
]
