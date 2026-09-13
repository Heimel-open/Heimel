"""WORM audit log runtime safety tests.

Verifies:
- append/verify round-trip (chain integrity)
- tamper detection (broken chain → verify False)
- Level 1: SHA-256 hashes only (no key)
- Level 2: encrypted content (with key)
- decrypt_entry round-trip
- decrypt_entry without key raises ValueError
- read_all returns entries in order
- thread-safe concurrent appends
"""

import hashlib
import json
import threading

import pytest

from vaig.worm import WORMLog


@pytest.fixture
def worm(tmp_path):
    return WORMLog(str(tmp_path / "audit.jsonl"))


@pytest.fixture
def worm_enc(tmp_path):
    return WORMLog(str(tmp_path / "audit_enc.jsonl"), encryption_key=b"testkey1234567890")


class TestWORMChainIntegrity:
    def test_empty_log_verifies(self, worm):
        assert worm.verify() is True

    def test_single_entry_verifies(self, worm):
        worm.append("e1", {"event": "test"})
        assert worm.verify() is True

    def test_two_entries_verify(self, worm):
        worm.append("e1", {"event": "a"})
        worm.append("e2", {"event": "b"})
        assert worm.verify() is True

    def test_ten_entries_verify(self, worm):
        for i in range(10):
            worm.append(f"e{i}", {"seq": i})
        assert worm.verify() is True

    def test_first_entry_prev_is_genesis(self, worm):
        worm.append("e1", {"x": 1})
        entries = worm.read_all()
        assert entries[0]["prev"] == "genesis"

    def test_chain_links_prev_to_prior_hash(self, worm):
        h1 = worm.append("e1", {"x": 1})
        worm.append("e2", {"x": 2})
        entries = worm.read_all()
        assert entries[1]["prev"] == h1

    def test_returned_hash_matches_stored_hash(self, worm):
        h = worm.append("e1", {"x": 1})
        entries = worm.read_all()
        assert entries[0]["hash"] == h


class TestWORMTamperDetection:
    def test_tamper_field_breaks_chain(self, worm):
        worm.append("e1", {"event": "original"})
        worm.append("e2", {"event": "second"})
        lines = worm.path.read_text().splitlines()
        entry = json.loads(lines[0])
        entry["event"] = "tampered"
        lines[0] = json.dumps(entry)
        worm.path.write_text("\n".join(lines) + "\n")
        assert worm.verify() is False

    def test_tamper_stored_hash_breaks_chain(self, worm):
        worm.append("e1", {"v": 1})
        lines = worm.path.read_text().splitlines()
        entry = json.loads(lines[0])
        entry["hash"] = "deadbeef" * 8
        lines[0] = json.dumps(entry)
        worm.path.write_text("\n".join(lines) + "\n")
        assert worm.verify() is False

    def test_tamper_prev_pointer_breaks_chain(self, worm):
        worm.append("e1", {"v": 1})
        worm.append("e2", {"v": 2})
        lines = worm.path.read_text().splitlines()
        entry = json.loads(lines[1])
        entry["prev"] = "wronghash" * 4
        lines[1] = json.dumps(entry)
        worm.path.write_text("\n".join(lines) + "\n")
        assert worm.verify() is False


class TestWORMLevel1:
    def test_prompt_sha256_stored(self, worm):
        worm.append("e1", {}, prompt="hello world", response="ok")
        entries = worm.read_all()
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert entries[0]["prompt_sha256"] == expected

    def test_response_sha256_stored(self, worm):
        worm.append("e1", {}, prompt="q", response="answer text")
        entries = worm.read_all()
        expected = hashlib.sha256(b"answer text").hexdigest()
        assert entries[0]["response_sha256"] == expected

    def test_no_encrypted_fields_without_key(self, worm):
        worm.append("e1", {}, prompt="q", response="a")
        entries = worm.read_all()
        assert "prompt_enc" not in entries[0]
        assert "response_enc" not in entries[0]

    def test_chain_with_prompt_response_verifies(self, worm):
        worm.append("e1", {}, prompt="What is the dose?", response="Take 500mg.")
        worm.append("e2", {}, prompt="Follow up?", response="Yes.")
        assert worm.verify() is True


class TestWORMLevel2:
    def test_encrypted_fields_present_with_key(self, worm_enc):
        worm_enc.append("e1", {}, prompt="secret prompt", response="secret response")
        entries = worm_enc.read_all()
        assert "prompt_enc" in entries[0]
        assert "response_enc" in entries[0]

    def test_decrypt_entry_roundtrip(self, worm_enc):
        worm_enc.append("e1", {}, prompt="secret prompt", response="secret response")
        entries = worm_enc.read_all()
        decrypted = worm_enc.decrypt_entry(entries[0])
        assert decrypted["prompt_plaintext"] == "secret prompt"
        assert decrypted["response_plaintext"] == "secret response"

    def test_sha256_also_present_with_key(self, worm_enc):
        worm_enc.append("e1", {}, prompt="p", response="r")
        entries = worm_enc.read_all()
        assert "prompt_sha256" in entries[0]
        assert "response_sha256" in entries[0]

    def test_decrypt_without_key_raises(self, worm):
        worm.append("e1", {}, prompt="q", response="a")
        entries = worm.read_all()
        with pytest.raises(ValueError):
            worm.decrypt_entry(entries[0])

    def test_encrypted_chain_verifies(self, worm_enc):
        for i in range(5):
            worm_enc.append(f"e{i}", {"i": i}, prompt=f"p{i}", response=f"r{i}")
        assert worm_enc.verify() is True


class TestWORMReadAll:
    def test_read_all_empty(self, worm):
        assert worm.read_all() == []

    def test_read_all_count(self, worm):
        for i in range(5):
            worm.append(f"e{i}", {"seq": i})
        assert len(worm.read_all()) == 5

    def test_read_all_order_preserved(self, worm):
        worm.append("e1", {"seq": 0})
        worm.append("e2", {"seq": 1})
        entries = worm.read_all()
        assert entries[0]["seq"] == 0
        assert entries[1]["seq"] == 1

    def test_read_all_nonexistent_file(self, tmp_path):
        w = WORMLog(str(tmp_path / "no_such_file.jsonl"))
        assert w.read_all() == []


class TestWORMConcurrency:
    def test_concurrent_appends_valid_chain(self, tmp_path):
        worm = WORMLog(str(tmp_path / "concurrent.jsonl"))
        errors: list = []

        def append_entries(start: int, count: int) -> None:
            try:
                for i in range(count):
                    worm.append(f"t{start}_{i}", {"v": start * 100 + i})
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=append_entries, args=(t, 5))
            for t in range(4)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        entries = worm.read_all()
        assert len(entries) == 20
        assert worm.verify() is True
