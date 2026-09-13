"""Portable c-MCP v1 contract surface.

This package defines binding and verification only. It does not execute tools
or grant authority.
"""

from .contract import (
    CMCP_VERSION,
    CMCPContractV1,
    CMCPInvocation,
    ProtocolStack,
    canonical_json,
)

__all__ = [
    "CMCP_VERSION",
    "CMCPContractV1",
    "CMCPInvocation",
    "ProtocolStack",
    "canonical_json",
]
