from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .base import FunctionTool


ProviderDispatch = Callable[[str, dict[str, Any]], Any]


class ProviderEffectTool(FunctionTool):
    """Boundary-only provider effector."""

    def __init__(
        self,
        provider: str,
        dispatch: ProviderDispatch,
        *,
        capabilities: list[str] | None = None,
    ) -> None:
        if not provider:
            raise ValueError("provider must be explicit")
        self.provider = provider
        self._dispatch_provider = dispatch
        super().__init__(
            f"{provider}-effect",
            self._dispatch,
            capabilities=capabilities,
        )

    def _dispatch(self, operation: str, **parameters: Any) -> Any:
        if not isinstance(operation, str) or not operation:
            raise ValueError("provider operation must be explicit")
        return self._dispatch_provider(operation, dict(parameters))


class GitHubEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("github", dispatch)


class StripeEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("stripe", dispatch)


class SlackEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("slack", dispatch)


class GoogleWorkspaceEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("google-workspace", dispatch)


class GmailEffectTool(GoogleWorkspaceEffectTool):
    """Explicit Gmail alias while keeping one Workspace provider boundary."""


class DatabaseEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("database", dispatch)


class AWSEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("aws", dispatch)


class AzureEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("azure", dispatch)


class GCPEffectTool(ProviderEffectTool):
    def __init__(self, dispatch: ProviderDispatch) -> None:
        super().__init__("gcp", dispatch)
