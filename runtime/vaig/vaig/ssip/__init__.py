"""Self-Scaling Integrity Protocol (SSIP) boundary.

SSIP handles governance integrity degradation, rollback and forensic recovery.
WHY Gate handles justification continuity before consequence commitment.
"""

from .deferment import DefermentMode, deferment_for_signal
from .evidence_pack import EvidencePack
from .reversion import ReversionLevel

__all__ = [
    "DefermentMode",
    "EvidencePack",
    "ReversionLevel",
    "deferment_for_signal",
]
