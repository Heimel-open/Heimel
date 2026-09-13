"""Provider-neutral subscription/enterprise entitlement selection.

This module never performs OAuth itself and never accepts raw credentials.
Provider adapters discover supported auth sources and pass only non-secret
observations into this layer. The result is a normalized execution-session
plan/receipt for the Factory orchestrator.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping, Sequence


class ProviderEntitlementError(ValueError):
    """Base error for entitlement/auth contract violations."""


class UnknownProviderError(ProviderEntitlementError):
    pass


class UnsupportedAuthSourceError(ProviderEntitlementError):
    pass


class NoSupportedAuthError(ProviderEntitlementError):
    pass


@dataclass(frozen=True)
class AuthCandidate:
    source_id: str
    auth_mode: str
    entitlement_kind: str
    is_fallback: bool = False


@dataclass(frozen=True)
class ProviderSpec:
    provider_id: str
    adapter_id: str
    product: str
    auth_candidates: tuple[AuthCandidate, ...]
    forbidden_source_ids: frozenset[str] = frozenset()

    def candidate(self, source_id: str) -> AuthCandidate | None:
        return next(
            (candidate for candidate in self.auth_candidates
             if candidate.source_id == source_id),
            None,
        )


@dataclass(frozen=True)
class AuthObservation:
    """Non-secret discovery result from a provider adapter."""

    source_id: str
    available: bool
    identity_ref: str | None = None
    entitlement_state: str = "unknown"
    entitlement_ref: str | None = None
    capabilities: tuple[str, ...] = ()
    quota: Mapping[str, int | float | str | None] | None = None
    session_ref: str | None = None

    def __post_init__(self) -> None:
        if self.entitlement_state not in {"active", "unknown", "unavailable"}:
            raise ProviderEntitlementError(
                f"invalid entitlement_state={self.entitlement_state!r}"
            )


@dataclass(frozen=True)
class ProviderEntitlement:
    provider_id: str
    adapter_id: str
    product: str
    auth_source: str
    auth_mode: str
    entitlement_kind: str
    entitlement_state: str
    identity_ref: str | None
    entitlement_ref: str | None
    capabilities: tuple[str, ...]
    quota: Mapping[str, int | float | str | None]
    session_ref: str | None
    fallback_used: bool
    authority_effect: str = "none"

    def as_dict(self) -> dict:
        return {
            "provider_id": self.provider_id,
            "adapter_id": self.adapter_id,
            "product": self.product,
            "auth_source": self.auth_source,
            "auth_mode": self.auth_mode,
            "entitlement_kind": self.entitlement_kind,
            "entitlement_state": self.entitlement_state,
            "identity_ref": self.identity_ref,
            "entitlement_ref": self.entitlement_ref,
            "capabilities": list(self.capabilities),
            "quota": dict(self.quota),
            "session_ref": self.session_ref,
            "fallback_used": self.fallback_used,
            "authority_effect": self.authority_effect,
        }


def _candidate(
    source_id: str,
    auth_mode: str,
    entitlement_kind: str,
    *,
    fallback: bool = False,
) -> AuthCandidate:
    return AuthCandidate(
        source_id=source_id,
        auth_mode=auth_mode,
        entitlement_kind=entitlement_kind,
        is_fallback=fallback,
    )


_PROVIDER_SPECS = {
    "openai_codex": ProviderSpec(
        provider_id="openai_codex",
        adapter_id="openai.codex",
        product="Codex / ChatGPT",
        auth_candidates=(
            _candidate(
                "chatgpt_account",
                "provider_account_login",
                "subscription",
            ),
            _candidate(
                "codex_device_code",
                "provider_device_code",
                "subscription",
            ),
            _candidate(
                "openai_enterprise",
                "enterprise_identity",
                "enterprise",
                fallback=True,
            ),
            _candidate(
                "openai_api",
                "api_credential",
                "metered_api",
                fallback=True,
            ),
        ),
    ),
    "anthropic_claude_code": ProviderSpec(
        provider_id="anthropic_claude_code",
        adapter_id="anthropic.claude-code",
        product="Claude Code / Claude",
        auth_candidates=(
            _candidate(
                "claude_account",
                "provider_account_login",
                "subscription",
            ),
            _candidate(
                "anthropic_enterprise",
                "enterprise_identity",
                "enterprise",
                fallback=True,
            ),
            _candidate(
                "anthropic_api",
                "api_credential",
                "metered_api",
                fallback=True,
            ),
        ),
    ),
    "google_antigravity": ProviderSpec(
        provider_id="google_antigravity",
        adapter_id="google.antigravity",
        product="Antigravity / Google",
        auth_candidates=(
            _candidate(
                "google_account_antigravity",
                "provider_account_oauth",
                "subscription",
            ),
            _candidate(
                "google_enterprise",
                "enterprise_identity",
                "enterprise",
                fallback=True,
            ),
            _candidate(
                "google_api",
                "api_credential",
                "metered_api",
                fallback=True,
            ),
        ),
        forbidden_source_ids=frozenset({
            "gemini_cli_oauth_reuse",
            "borrowed_google_oauth_session",
        }),
    ),
    "github_copilot": ProviderSpec(
        provider_id="github_copilot",
        adapter_id="github.copilot",
        product="GitHub Copilot",
        auth_candidates=(
            _candidate(
                "github_account_copilot",
                "provider_account_oauth",
                "subscription",
            ),
            _candidate(
                "github_enterprise",
                "enterprise_identity",
                "enterprise",
                fallback=True,
            ),
        ),
    ),
}

PROVIDER_SPECS: Mapping[str, ProviderSpec] = MappingProxyType(_PROVIDER_SPECS)


def provider_ids() -> tuple[str, ...]:
    return tuple(PROVIDER_SPECS)


def get_provider_spec(provider_id: str) -> ProviderSpec:
    try:
        return PROVIDER_SPECS[provider_id]
    except KeyError as exc:
        raise UnknownProviderError(provider_id) from exc


def select_entitlement(
    provider_id: str,
    observations: Sequence[AuthObservation] | Iterable[AuthObservation],
) -> ProviderEntitlement:
    """Select the highest-priority officially supported available auth source.

    Selection is deterministic and preference-ordered. Account/subscription
    sources come before fallback API/enterprise sources in each provider spec.
    No raw credential material crosses this contract.
    """

    spec = get_provider_spec(provider_id)
    by_source: dict[str, AuthObservation] = {}

    for observation in observations:
        if observation.source_id in by_source:
            raise ProviderEntitlementError(
                f"duplicate auth observation: {observation.source_id}"
            )
        if observation.source_id in spec.forbidden_source_ids and observation.available:
            raise UnsupportedAuthSourceError(
                f"{provider_id} forbids auth source {observation.source_id}"
            )
        candidate = spec.candidate(observation.source_id)
        if candidate is None:
            if observation.available:
                raise UnsupportedAuthSourceError(
                    f"{provider_id} does not support auth source "
                    f"{observation.source_id}"
                )
            continue
        by_source[observation.source_id] = observation

    for candidate in spec.auth_candidates:
        observation = by_source.get(candidate.source_id)
        if not observation or not observation.available:
            continue
        if observation.entitlement_state == "unavailable":
            continue

        capabilities = tuple(sorted(set(observation.capabilities)))
        quota = MappingProxyType(dict(observation.quota or {}))
        return ProviderEntitlement(
            provider_id=spec.provider_id,
            adapter_id=spec.adapter_id,
            product=spec.product,
            auth_source=candidate.source_id,
            auth_mode=candidate.auth_mode,
            entitlement_kind=candidate.entitlement_kind,
            entitlement_state=observation.entitlement_state,
            identity_ref=observation.identity_ref,
            entitlement_ref=observation.entitlement_ref,
            capabilities=capabilities,
            quota=quota,
            session_ref=observation.session_ref,
            fallback_used=candidate.is_fallback,
        )

    raise NoSupportedAuthError(
        f"no supported available auth source for {provider_id}"
    )
