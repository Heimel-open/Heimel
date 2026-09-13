"""Isolated external monitor adapters: Wigolo and WorldMonitor.

These are acquisition adapters only (per issue #812). They pull external
observations from Wigolo (web/brand monitoring) and WorldMonitor (global
event/world monitoring) and surface them as provenance-tagged candidates.

Design rules (mirrors #878 source-integrity contract):
- No fabricated values. Missing upstream data is an error, never a placeholder.
- Every observation carries a raw payload digest (SHA-256) + canonical form.
- Responses are normalized fail-closed: malformed/unmappable payloads raise.
- Connector identity never grants truth, independence or authority.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from .mcp_connector_base import MCPConnectorBase

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 20


def _canonical_digest(payload: Any) -> str:
    """Stable SHA-256 digest of a JSON-serializable payload (RFC 8785 ordering)."""
    try:
        text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except (TypeError, ValueError):
        text = repr(payload)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class _ExternalMonitorBase(MCPConnectorBase):
    """Shared acquisition logic for isolated external monitors."""

    # Subclasses set these.
    source_name: str = "external-monitor"
    default_base_url: str = ""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        # Bypass MCPConnectorBase's AllemannsdataHTTPClient wiring; we talk
        # directly to the external source over HTTP.
        self.server_name = self.source_name
        self.api_key = api_key
        self.base_url = base_url or self.default_base_url
        self.timeout = timeout
        self.last_update = datetime.now(timezone.utc).replace(tzinfo=None)
        self._health = True
        self._tool_registry: Dict[str, Dict[str, Any]] = {}
        self.register_tools()

    def register_tools(self) -> None:
        self._tool_registry = {
            "fetch_observations": {
                "description": f"Fetch observations from {self.source_name}",
                "required_params": ["query"],
                "parameters": {"query": "search/topic query"},
            }
        }

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        if tool_name != "fetch_observations":
            raise ValueError(f"Tool '{tool_name}' not supported by {self.source_name}")
        return self.fetch_observations(params.get("query", ""))

    def fetch_observations(self, query: str) -> List[Dict[str, Any]]:
        """Pull external observations. Fail-closed: raises on any error.

        Returns a list of candidate observations, each with provenance +
        raw digest. Never synthesizes missing fields.
        """
        if not self.base_url:
            raise ValueError(f"{self.source_name}: no base_url configured")
        if not query:
            raise ValueError(f"{self.source_name}: empty query is not permitted")

        url = f"{self.base_url.rstrip('/')}/observations"
        try:
            resp = httpx.get(
                url,
                params={"q": query},
                headers=self._headers(),
                timeout=self.timeout,
            )
            resp.raise_for_status()
            payload = resp.json()
        except Exception as e:  # network / decode / HTTP error
            logger.error(f"{self.source_name} fetch failed for '{query}': {e}")
            raise

        items = payload.get("observations") if isinstance(payload, dict) else None
        if not isinstance(items, list):
            raise ValueError(f"{self.source_name}: unexpected payload shape (no 'observations' list)")

        candidates: List[Dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError(f"{self.source_name}: non-dict observation rejected (fail-closed)")
            # No fabrication: only pass through fields the source actually returned.
            digest = _canonical_digest(item)
            candidates.append(
                {
                    "source": self.source_name,
                    "query": query,
                    "raw_digest": digest,
                    "payload": item,  # unmapped upstream payload, preserved
                    "provenance": {
                        "source": self.source_name,
                        "endpoint": url,
                        "raw_digest": digest,
                    },
                }
            )
        self.last_update = self.last_update  # unchanged; real timestamp set on success below
        from datetime import datetime, timezone

        self.last_update = datetime.now(timezone.utc).replace(tzinfo=None)
        return candidates


class WigoloConnector(_ExternalMonitorBase):
    """Isolated adapter for Wigolo (web/brand monitoring)."""

    source_name = "Wigolo"
    default_base_url = ""


class WorldMonitorConnector(_ExternalMonitorBase):
    """Isolated adapter for WorldMonitor (global event/world monitoring)."""

    source_name = "WorldMonitor"
    default_base_url = ""
