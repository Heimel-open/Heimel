"""Embedded governance primitives — stdlib-only, portable on-device.

This package is the on-device equivalent of the platform's core governance
primitives, dependency-free so they run on micro controllers and constrained
runtimes without compromising integrity:

- ``canonical`` — deterministic SHA-256 canonical digest (RFC 8785 subset)
- ``worm`` — append-only hash-chained audit log
- ``revocation`` — M-of-N guardian revocation with hash chain
- ``ratelimit`` — sliding-window rate limiter
- ``micro_admissibility`` — fail-closed signal fusion (micro-REHT evidence gate)
- ``embedded_approval`` — quorum-gated approval chain
- ``micro_consent`` — immutable consent ledger with withdrawal

Combined with ``valo_edge.runtime.micro_reht`` these give a full local
governance chain: propose → clear → enforce → record → revoke.
"""

from valo_edge.governance.canonical import (
    canonical_bytes,
    canonical_digest,
    digest_bytes,
    to_json_value,
    verify_canonical_digest,
)
from valo_edge.governance.embedded_approval import ApprovalChain, ApprovalRecord
from valo_edge.governance.micro_admissibility import (
    AdmissibilityVerdict,
    MicroAdmissibilityDecision,
    MicroAdmissibilityEngine,
    MicroSignal,
    SignalDisposition,
)
from valo_edge.governance.micro_consent import ConsentRecord, MicroConsentLedger
from valo_edge.governance.ratelimit import RateLimiter
from valo_edge.governance.revocation import RevocationLog
from valo_edge.governance.worm import WormLog

__all__ = [
    "AdmissibilityVerdict",
    "ApprovalChain",
    "ApprovalRecord",
    "ConsentRecord",
    "MicroAdmissibilityDecision",
    "MicroAdmissibilityEngine",
    "MicroConsentLedger",
    "MicroSignal",
    "RateLimiter",
    "RevocationLog",
    "SignalDisposition",
    "WormLog",
    "canonical_bytes",
    "canonical_digest",
    "digest_bytes",
    "to_json_value",
    "verify_canonical_digest",
]
