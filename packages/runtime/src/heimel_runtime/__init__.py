"""The public Heimel runtime composition root.

This package is deliberately small: the authoritative implementations remain
in the migrated runtime components, while this facade assembles their only
safe consequence path into one usable object.
"""

from .runtime import HeimelRuntime, RuntimeExecution

__all__ = ["HeimelRuntime", "RuntimeExecution"]
