"""VAIG external adapter registry — only real, wired implementations."""

# ── Generic ──────────────────────────────────────────────────────────────────
from vaig.integrations.base import (
    ExternalAdapter,
    FunctionAdapter,
    RESTAdapter,
)

# ── Real implementations ──────────────────────────────────────────────────────
from vaig.integrations.openai_mod import OpenAIModerationAdapter
from vaig.integrations.perspective import PerspectiveToxicityAdapter
from vaig.integrations.detoxify_adapter import DetoxifyAdapter
from vaig.integrations.presidio import PresidioPIIAdapter
from vaig.integrations.external import AzureContentSafetyAdapter
from vaig.integrations.external import LangkitHallucinationAdapter
from vaig.integrations.external import LangkitToxicityAdapter

from vaig.integrations.recommend import recommend

__all__ = [
    "recommend",
    # generic
    "ExternalAdapter",
    "FunctionAdapter",
    "RESTAdapter",
    # real implementations
    "OpenAIModerationAdapter",
    "PerspectiveToxicityAdapter",
    "DetoxifyAdapter",
    "PresidioPIIAdapter",
    "AzureContentSafetyAdapter",
    "LangkitHallucinationAdapter",
    "LangkitToxicityAdapter",
]
