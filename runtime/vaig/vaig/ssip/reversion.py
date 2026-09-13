"""Reversion levels for SSIP."""

from enum import Enum


class ReversionLevel(str, Enum):
    """Escalating reversion actions.

    Automatic movement is escalation-only. Downgrade requires forensic review
    and manual approval by the appropriate authority chain.
    """

    NONE = "NONE"
    SOFT_REVERSION = "SOFT_REVERSION"
    HARD_REVERSION = "HARD_REVERSION"
    CATASTROPHIC_LOCKDOWN = "CATASTROPHIC_LOCKDOWN"
