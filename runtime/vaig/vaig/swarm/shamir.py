"""
VAIG Swarm — Shamir Secret Sharing (100, 3)
Threshold scheme: any 3 of 100 guardians can reconstruct the secret.
Uses Lagrange interpolation in GF(2^256).
"""
import random
import hashlib
from typing import List, Tuple

class ShamirSecretSharing:
    """
    (n, k) threshold scheme:
      - Split secret into n shares
      - Any k shares can reconstruct
      - k-1 shares reveal ZERO information (information-theoretic security)

    Default: (100, 3) — 100 guardians, threshold 3
    """

    def __init__(self, n: int = 100, k: int = 3, prime: int = None):
        self.n = n
        self.k = k
        self.prime = prime or (2**256 - 189)  # Large prime near 2^256

    def split(self, secret: int) -> List[Tuple[int, int]]:
        """Split secret into n shares. Returns [(x, y), ...]."""
        # Generate random polynomial of degree k-1 where f(0) = secret
        coeffs = [secret] + [random.randrange(1, self.prime) for _ in range(self.k - 1)]

        shares = []
        for x in range(1, self.n + 1):
            y = sum(c * pow(x, i, self.prime) for i, c in enumerate(coeffs)) % self.prime
            shares.append((x, y))
        return shares

    def reconstruct(self, shares: List[Tuple[int, int]]) -> int:
        """Reconstruct secret from k shares using Lagrange interpolation."""
        if len(shares) < self.k:
            raise ValueError(f"Need {self.k} shares, got {len(shares)}")

        secret = 0
        for i, (x_i, y_i) in enumerate(shares[:self.k]):
            numerator = 1
            denominator = 1
            for j, (x_j, _) in enumerate(shares[:self.k]):
                if i != j:
                    numerator = (numerator * (-x_j)) % self.prime
                    denominator = (denominator * (x_i - x_j)) % self.prime

            lagrange_coeff = (numerator * pow(denominator, -1, self.prime)) % self.prime
            secret = (secret + y_i * lagrange_coeff) % self.prime

        return secret
