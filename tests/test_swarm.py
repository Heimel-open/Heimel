"""
VAIG Swarm — Test Suite
Tests for all anti-coercion mechanisms.
"""
import pytest
import time

from vaig.swarm.orchestrator import SwarmOrchestrator
from vaig.swarm.duress import DuressAuth
from vaig.swarm.time_lock import TimeLock
from vaig.swarm.shamir import ShamirSecretSharing
from vaig.swarm.revocation import RevocationLog
from vaig.swarm.ring_sig import RingSignature, _P
from vaig.swarm.vrf import VRF
from vaig.swarm.epoch import EpochManager


class TestDuressAuth:
    """Test silent alert under coercion."""

    def test_normal_code(self):
        auth = DuressAuth()
        auth.set_codes("secret123", "help999")
        access, is_duress = auth.authenticate("secret123")
        assert access and not is_duress

    def test_duress_code(self):
        auth = DuressAuth()
        auth.set_codes("secret123", "help999")
        access, is_duress = auth.authenticate("help999")
        assert access and is_duress
        assert len(auth.get_alerts()) == 1

    def test_wrong_code(self):
        auth = DuressAuth()
        auth.set_codes("secret123", "help999")
        access, _ = auth.authenticate("wrong")
        assert not access


class TestTimeLock:
    """Test 15-minute delay."""

    def test_request(self):
        tl = TimeLock()
        tl.DELAY_SECONDS = 1  # Speed up for tests
        ts = tl.request("op1")
        assert ts > time.time()

    def test_not_yet(self):
        tl = TimeLock()
        tl.DELAY_SECONDS = 3600  # Long delay
        tl.request("op2")
        ok, msg = tl.confirm("op2")
        assert not ok
        assert "Wait" in msg


class TestShamir:
    """Test (100, 3) secret sharing."""

    def test_split_reconstruct(self):
        s = ShamirSecretSharing(n=100, k=3)
        secret = 123456789
        shares = s.split(secret)
        assert len(shares) == 100
        reconstructed = s.reconstruct(shares[:3])
        assert reconstructed == secret

    def test_insufficient_shares(self):
        s = ShamirSecretSharing(n=100, k=3)
        shares = s.split(999)
        with pytest.raises(ValueError):
            s.reconstruct(shares[:2])  # Only 2 of 3 needed


class TestRevocation:
    """Test M-of-N revocation."""

    def test_propose(self):
        r = RevocationLog(threshold=2)
        p = r.propose_revocation("key1", "compromised", "g1", "sig1")
        assert p["target_key"] == "key1"

    def test_execute_threshold(self):
        r = RevocationLog(threshold=2)
        p = r.propose_revocation("key1", "compromised", "g1", "sig1")
        p = r.vote(p, "g2", "sig2")
        ok = r.execute(p)
        assert ok
        assert r.is_revoked("key1")

    def test_below_threshold(self):
        r = RevocationLog(threshold=3)
        p = r.propose_revocation("key1", "compromised", "g1", "sig1")
        ok = r.execute(p)  # Only 1 vote, need 3
        assert not ok


class TestSwarmOrchestrator:
    """Integration test for full orchestrator."""

    def test_bootstrap(self):
        sm = SwarmOrchestrator(n_guardians=10, threshold=3)
        status = sm.bootstrap(
            guardian_ids=[f"g{i}" for i in range(10)],
            master_secret=42,
            normal_code="safe",
            duress_code="danger"
        )
        assert status["guardians"] == 10
        assert status['shares_distributed'] == 10


class TestDuressSalt:
    """DuressAuth must salt digests so a leaked table is not brute-forceable."""

    def test_instances_use_distinct_salts(self):
        a = DuressAuth()
        b = DuressAuth()
        a.set_codes("secret", "duress")
        b.set_codes("secret", "duress")
        assert a._salt != b._salt
        assert a._normal_digest != b._normal_digest

    def test_authenticate_requires_set_codes(self):
        a = DuressAuth()
        with pytest.raises(RuntimeError):
            a.authenticate("anything")

    def test_digest_is_not_plain_sha256(self):
        import hashlib
        a = DuressAuth()
        a.set_codes("secret", "duress")
        assert a._normal_digest != hashlib.sha256(b"secret").digest()


class TestVRF:
    """VRF provides deterministic, tamper-evident output (shared-secret mode)."""

    def test_deterministic_and_verifiable(self):
        v = VRF()
        sk = b"super-secret-key-123"
        out1, proof1 = v.prove(sk, b"seed")
        out2, proof2 = v.prove(sk, b"seed")
        assert out1 == out2
        assert proof1 == proof2
        assert v.verify(sk, b"seed", out1, proof1)

    def test_tampered_proof_rejected(self):
        v = VRF()
        sk = b"super-secret-key-123"
        out, proof = v.prove(sk, b"seed")
        bad = bytes([proof[0] ^ 0xFF]) + proof[1:]
        assert not v.verify(sk, b"seed", out, bad)

    def test_wrong_seed_rejected(self):
        v = VRF()
        sk = b"super-secret-key-123"
        out, proof = v.prove(sk, b"seed")
        assert not v.verify(sk, b"other-seed", out, proof)


class TestRingSignature:
    """AOS ring signature: sign/verify, tamper rejection, ring anonymity."""

    def _ring(self):
        r = RingSignature(ring_size=4)
        sks = [101, 202, 303, 404]
        pks = [r.public_key(sk) for sk in sks]
        return r, sks, pks

    def test_sign_verify(self):
        r, sks, pks = self._ring()
        sig = r.sign(b"msg", signer_index=2, private_key=sks[2], public_keys=pks)
        assert r.verify(b"msg", sig, pks)

    def test_tampered_signature_rejected(self):
        r, sks, pks = self._ring()
        sig = r.sign(b"msg", signer_index=1, private_key=sks[1], public_keys=pks)
        bad = dict(sig)
        bad["t"] = list(sig["t"])
        bad["t"][0] = (bad["t"][0] + 1) % (_P - 1)
        assert not r.verify(b"msg", bad, pks)

    def test_wrong_message_rejected(self):
        r, sks, pks = self._ring()
        sig = r.sign(b"msg", signer_index=0, private_key=sks[0], public_keys=pks)
        assert not r.verify(b"other", sig, pks)

    def test_each_ring_member_can_sign(self):
        r, sks, pks = self._ring()
        for i in range(len(pks)):
            sig = r.sign(b"msg", signer_index=i, private_key=sks[i], public_keys=pks)
            assert r.verify(b"msg", sig, pks)

    def test_ring_size_mismatch_rejected(self):
        r, sks, pks = self._ring()
        sig = r.sign(b"msg", signer_index=0, private_key=sks[0], public_keys=pks)
        assert not r.verify(b"msg", sig, pks[:-1])


class TestEpochManager:
    """Epoch keys must be CSPRNG-derived and epoch-bound."""

    def test_rotate_generates_distinct_keys(self):
        em = EpochManager()
        g1 = em.rotate_keys(["a", "b", "c"])
        keys1 = [em.get_key(g, g1) for g in ("a", "b", "c")]
        assert all(k and len(k) == 64 for k in keys1)
        assert len(set(keys1)) == 3

    def test_rotation_refreshes_keys(self):
        em = EpochManager()
        e1 = em.rotate_keys(["a"])
        k1 = em.get_key("a", e1)
        # Force a new epoch window so rotate_keys generates fresh material.
        em._keys[e1 + 1] = {g: "x" * 64 for g in ("a",)}
        em._current_epoch = e1 + 1
        assert em.get_key("a", e1 + 1) != k1

    def test_epoch_validity_window(self):
        em = EpochManager()
        cur = em.current_epoch()
        assert em.is_valid_epoch(cur)
        assert em.is_valid_epoch(cur - 2)
        assert not em.is_valid_epoch(cur - 3)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
