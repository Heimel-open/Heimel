"""Tests for crypto remediation: WORM AEAD encryption."""

import pytest

from vaig.worm import WORMLog


def test_worm_encrypts_same_plaintext_to_distinct_ciphertext(tmp_path):
    worm = WORMLog(str(tmp_path / "audit.jsonl"), encryption_key=b"k" * 32)
    worm.append("e1", {}, prompt="same secret", response="same secret")
    worm.append("e2", {}, prompt="same secret", response="same secret")
    entries = worm.read_all()
    assert entries[0]["prompt_enc"] != entries[1]["prompt_enc"]
    assert entries[0]["prompt_nonce"] != entries[1]["prompt_nonce"]
    assert worm.verify() is True
    assert worm.decrypt_entry(entries[0])["prompt_plaintext"] == "same secret"


def test_worm_decrypt_rejects_tampered_ciphertext(tmp_path):
    worm = WORMLog(str(tmp_path / "audit.jsonl"), encryption_key=b"k" * 32)
    worm.append("e1", {}, prompt="secret prompt")
    entry = worm.read_all()[0]
    tampered = dict(entry)
    tampered["prompt_enc"] = tampered["prompt_enc"][:-1] + (
        "A" if not tampered["prompt_enc"].endswith("A") else "B"
    )
    with pytest.raises(Exception):
        worm.decrypt_entry(tampered)
