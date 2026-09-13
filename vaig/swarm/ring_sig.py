"""
VAIG Swarm — Anonymous Ring Signatures
Any guardian can sign on behalf of the ring (all guardians) without revealing identity.

STATUS: CONCEPT — reference implementation of the AOS (Abe–Ohkubo–Suzuki)
ring signature over a multiplicative group Z_p^*. Mathematically coherent and
self-consistent, but NOT audited; use a reviewed library before production.

Properties:
  - Unforgeability: only a holder of a private key whose public key is in the
    ring can produce a valid signature.
  - Anonymity: a verifier cannot tell WHICH ring member signed.
"""
import hashlib
import secrets
from typing import List

# RFC 3526 group 14 (2048-bit MODP), a well-known safe prime.
_P = int(
    "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74"
    "020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F1437"
    "4FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
    "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF05"
    "98DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB"
    "9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
    "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF695581718"
    "3995497CEA956AE515D2261898FA051015728E5A8AACAA68FFFFFFFFFFFFFFFF",
    16,
)
_ORDER = _P - 1
_G = 2


class RingSignature:
    """
    AOS ring signature over Z_p^*.

    Each public key is ``g^sk mod p``. The signature binds a random challenge
    chain to the ring, the message and a commitment that only the signer can
    close (because it requires ``sk``).
    """

    def __init__(self, ring_size: int = 100, p: int = _P, g: int = _G):
        self.ring_size = ring_size
        self.p = p
        self.g = g

    @staticmethod
    def _hash(p: int, message: bytes, ring: List[bytes], commitment: bytes) -> int:
        """Hash (message || ring || commitment) into Z_{p-1}."""
        h = hashlib.sha256(message + b"".join(ring) + commitment).digest()
        return int.from_bytes(h, "big") % (p - 1)

    def public_key(self, private_key: int) -> int:
        """Derive the public key g^sk mod p for a private key."""
        return pow(self.g, private_key, self.p)

    def sign(
        self,
        message: bytes,
        signer_index: int,
        private_key: int,
        public_keys: List[int],
    ) -> dict:
        """Create a ring signature.

        Args:
            message: bytes to sign.
            signer_index: index of the signer within public_keys.
            private_key: signer's secret exponent.
            public_keys: ring of public keys (ints mod p).
        """
        n = len(public_keys)
        ring = [pk.to_bytes((self.p.bit_length() + 7) // 8, "big") for pk in public_keys]
        order = _ORDER

        e = [0] * n
        t = [0] * n

        # Choose a random nonce for the signer.
        u = secrets.randbelow(order)

        # Build the challenge chain, starting after the signer.
        s = signer_index
        e[(s + 1) % n] = self._hash(self.p, message, ring, pow(self.g, u, self.p).to_bytes((self.p.bit_length() + 7) // 8, "big"))

        for i in range(1, n):
            j = (s + i) % n
            k = (s + i + 1) % n
            t[j] = secrets.randbelow(order)
            r = (pow(self.g, t[j], self.p) * pow(public_keys[j], e[j], self.p)) % self.p
            e[k] = self._hash(self.p, message, ring, r.to_bytes((self.p.bit_length() + 7) // 8, "big"))

        # Close the ring: t_s = u - e_s * sk (mod p-1).
        t[s] = (u - e[s] * private_key) % order

        return {
            "e0": e[0],
            "t": t,
            "ring_size": n,
        }

    def verify(self, message: bytes, signature: dict, public_keys: List[int]) -> bool:
        """Verify a ring signature.

        Replays the challenge chain; the signature is valid iff the chain
        closes back to e0.
        """
        n = len(public_keys)
        if signature.get("ring_size") != n:
            return False
        e = signature.get("e0")
        t = signature.get("t")
        if len(t) != n or not isinstance(e, int):
            return False

        ring = [pk.to_bytes((self.p.bit_length() + 7) // 8, "big") for pk in public_keys]

        for i in range(n):
            r = (pow(self.g, t[i], self.p) * pow(public_keys[i], e, self.p)) % self.p
            e = self._hash(self.p, message, ring, r.to_bytes((self.p.bit_length() + 7) // 8, "big"))

        return e == signature["e0"]
