"""
VAIG Swarm — Verifiable Random Function (VRF)
Deterministic random output that can be publicly verified.
Used for: active set rotation, leader election.

STATUS: CONCEPT — HMAC-based construction, NOT an ECVRF. It provides
pseudorandomness and tamper-evidence for a fixed secret key, but it does NOT
provide the public-verifiability property of a true VRF: ``verify`` uses the
caller-supplied key as the HMAC secret, so it is only meaningful when the key
is held by a trusted verifier. Replace with an audited ECVRF implementation
before any real use.
"""
import hashlib
import hmac
from typing import Tuple


class VRF:
    """
    HMAC-SHA256 based deterministic output with tamper-evident proof.

      - prove(secret_key, seed) -> (output, proof)
      - verify(key, seed, output, proof) -> bool

    NOTE: not a public-key VRF. ``verify`` recomputes the HMAC with the same
    key used to sign, so it detects tampering but requires the key to be
    shared with the verifier. See the module docstring.
    """

    def prove(self, secret_key: bytes, seed: bytes) -> Tuple[bytes, bytes]:
        """Generate VRF output and proof."""
        output = hmac.new(secret_key, seed + b"output", hashlib.sha256).digest()
        proof = hmac.new(secret_key, seed + b"proof", hashlib.sha256).digest()
        return output, proof

    def verify(self, key: bytes, seed: bytes, output: bytes, proof: bytes) -> bool:
        """Verify output/proof against the key.

        The key must be the same bytes used in ``prove`` (shared-secret mode).
        """
        expected_output = hmac.new(key, seed + b"output", hashlib.sha256).digest()
        expected_proof = hmac.new(key, seed + b"proof", hashlib.sha256).digest()
        return hmac.compare_digest(output, expected_output) and hmac.compare_digest(proof, expected_proof)
