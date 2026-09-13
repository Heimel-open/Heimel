"""Provider-neutral base for governed Allemannsdata MCP acquisition."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .allemannsdata_http_client import AllemannsdataHTTPClient


logger = logging.getLogger(__name__)


class MCPConnectorBase(ABC):
    """Base class for MCP acquisition adapters.

    Connector responses are candidates with provenance. They are not verified
    facts and do not grant admissibility or authority.
    """

    def __init__(
        self,
        mcp_server_name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.server_name = mcp_server_name
        self.api_key = api_key
        self.last_update = datetime.now(timezone.utc)
        self._health = True
        self._tool_registry: Dict[str, Dict[str, Any]] = {}
        self._http_client = AllemannsdataHTTPClient(
            base_url=base_url,
            api_key=api_key,
        )
        self.register_tools()

    def get_connector_name(self) -> str:
        return self.server_name

    def is_healthy(self) -> bool:
        return self._health

    def get_last_updated(self) -> datetime:
        return self.last_update

    def get_last_acquisition_receipt(self) -> Optional[Dict[str, Any]]:
        """Expose the transport acquisition receipt without evaluating it."""

        return self._http_client.get_last_acquisition_receipt()

    @abstractmethod
    def register_tools(self) -> None:
        """Populate the closed tool registry."""

    def call_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
    ) -> Any:
        if tool_name not in self._tool_registry:
            raise ValueError(f"Tool '{tool_name}' not registered in {self.server_name}")

        tool_def = self._tool_registry[tool_name]
        for param in tool_def.get("required_params", []):
            if param not in params:
                raise ValueError(f"Missing required parameter: {param}")

        try:
            server_name = self.server_name.lower()
            result = self._http_client.call_tool(server_name, tool_name, params)
            self.last_update = datetime.now(timezone.utc)
            logger.debug(
                "Tool '%s' called successfully on %s",
                tool_name,
                self.server_name,
            )
            return result
        except Exception:
            self._health = False
            logger.exception(
                "Error calling tool '%s' on %s",
                tool_name,
                self.server_name,
            )
            raise

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": name,
                "description": tool_def.get("description", ""),
                "parameters": tool_def.get("parameters", {}),
            }
            for name, tool_def in self._tool_registry.items()
        ]

    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        return self._tool_registry.get(tool_name)


__all__ = ["MCPConnectorBase"]
