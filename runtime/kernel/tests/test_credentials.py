from __future__ import annotations

from pathlib import Path

import pytest

from valo_kernel.credentials import (
    CredentialStoreError,
    EncryptedFileCredentialStore,
)


def test_encrypted_file_credential_store_survives_restart(tmp_path: Path) -> None:
    directory = tmp_path / "credentials"
    passphrase = b"test-passphrase"
    payload = b"valo-domain-binding"

    first = EncryptedFileCredentialStore(directory)
    public_key = first.create_credential("device-1", passphrase)
    signature = first.sign("device-1", payload, passphrase)

    second = EncryptedFileCredentialStore(directory)
    assert second.public_key("device-1") == public_key
    assert second.verify("device-1", payload, signature) is True
    assert second.verify("device-1", b"tampered", signature) is False


def test_credential_store_never_overwrites_existing_key(tmp_path: Path) -> None:
    store = EncryptedFileCredentialStore(tmp_path / "credentials")
    store.create_credential("device-1", b"first-passphrase")

    with pytest.raises(CredentialStoreError, match="already exists"):
        store.create_credential("device-1", b"second-passphrase")


def test_wrong_passphrase_fails_closed(tmp_path: Path) -> None:
    store = EncryptedFileCredentialStore(tmp_path / "credentials")
    store.create_credential("device-1", b"correct-passphrase")

    with pytest.raises(CredentialStoreError, match="unlock failed"):
        store.sign("device-1", b"payload", b"wrong-passphrase")


def test_credential_identifier_cannot_escape_store(tmp_path: Path) -> None:
    store = EncryptedFileCredentialStore(tmp_path / "credentials")

    with pytest.raises(CredentialStoreError, match="invalid characters"):
        store.create_credential("../authority-root", b"passphrase")
