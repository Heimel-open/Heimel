"""
VAIG Swarm — anti-coercion / kidnapping-resistance authority layer.

STATUS: CONCEPT / NOT-AUDITED. This subpackage is a preserved prototype
restored from valo-platform's archived ``src/vaig`` (2026-08-05). None of
the cryptographic primitives here have been security-audited, and several
(``ring_sig``, ``vrf``, ``epoch``) are deliberately simplified reference
implementations, NOT production-grade cryptography:

- ``RingSignature`` proves only ring membership via a message hash; it is
  not an unforgeable ring signature (no Fiat–Shamir binding).
- ``VRF`` is an HMAC construction, not an ECVRF; ``verify`` trusts the
  caller-supplied "public key" as if it were the secret.
- ``EpochManager`` derives keys from hashing; use a CSPRNG-backed KDF for
  real deployments.

DO NOT use these primitives to protect real systems without a cryptographic
review or replacement by an audited library. The one production-hardened
component here is ``RevocationLog`` (WORM hash-chained M-of-N revocation).
"""

from .duress import DuressAuth
from .epoch import EpochManager
from .orchestrator import SwarmOrchestrator
from .revocation import RevocationLog
from .ring_sig import RingSignature
from .shamir import ShamirSecretSharing
from .time_lock import TimeLock
from .vrf import VRF

__all__ = [
    "DuressAuth",
    "EpochManager",
    "SwarmOrchestrator",
    "RevocationLog",
    "RingSignature",
    "ShamirSecretSharing",
    "TimeLock",
    "VRF",
]
