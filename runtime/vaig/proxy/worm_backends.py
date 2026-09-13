"""WORM backend implementations — three trust levels.

Select via VALO_WORM_BACKEND environment variable:
  file   (default) — SHA-256 hash-chained local file (Nivå 1)
  s3               — AWS S3 Object Lock, COMPLIANCE mode (Nivå 2)
  azure            — Azure Blob immutable storage (Nivå 2)
  tpm              — TPM2-signed entries + file/cloud backend (Nivå 3)

Nivå 1: tamper-evident (chain breaks on tampering, detectable by auditor)
Nivå 2: tamper-proof (cloud provider hardware prevents deletion/overwrite)
Nivå 3: hardware-rooted (TPM2 HMAC proves code identity + tamper-proof storage)
"""
import hashlib
import hmac
import json
import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path


class FileBackend:
    """SHA-256 hash-chained local file. Tamper-evident, not tamper-proof."""
    level = 1
    description = "Local file — SHA-256 hash chain"

    def __init__(self):
        self.path = os.environ.get(
            "VALO_WORM_LOG",
            str(Path.home() / ".valo-proxy" / "worm.jsonl"),
        )
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)

    def write(self, entry: dict) -> None:
        with open(self.path, "a") as f:
            f.write(json.dumps(entry, separators=(",", ":")) + "\n")

    def tail(self, n: int = 20) -> list[dict]:
        try:
            with open(self.path) as f:
                lines = [l.strip() for l in f if l.strip()]
            return [json.loads(l) for l in lines[-n:]]
        except FileNotFoundError:
            return []

    def status(self) -> dict:
        try:
            size = Path(self.path).stat().st_size
        except FileNotFoundError:
            size = 0
        return {"backend": "file", "level": 1, "path": self.path, "size_bytes": size}


class S3Backend:
    """AWS S3 Object Lock in COMPLIANCE mode. Hardware-enforced immutability."""
    level = 2
    description = "AWS S3 Object Lock (COMPLIANCE) — hardware-enforced immutability"

    def __init__(self):
        try:
            import boto3
            self._boto3 = boto3
        except ImportError:
            raise RuntimeError("boto3 required: pip install boto3")
        self.bucket = os.environ.get("VALO_WORM_S3_BUCKET")
        if not self.bucket:
            raise RuntimeError("VALO_WORM_S3_BUCKET environment variable is required")
        self.prefix = os.environ.get("VALO_WORM_S3_PREFIX", "valo-worm/")
        self.retention_days = int(os.environ.get("VALO_WORM_S3_RETENTION_DAYS", "365"))
        self._s3 = boto3.client("s3")
        self._shadow = FileBackend()

    def write(self, entry: dict) -> None:
        entry_hash = entry.get("hash", hashlib.sha256(
            json.dumps(entry, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest())
        key = f"{self.prefix}{entry['ts']:.6f}_{entry_hash[:16]}.json"
        retain_until = datetime.now(timezone.utc) + timedelta(days=self.retention_days)
        self._s3.put_object(
            Bucket=self.bucket, Key=key,
            Body=json.dumps(entry, separators=(",", ":")).encode(),
            ContentType="application/json",
            ObjectLockMode="COMPLIANCE",
            ObjectLockRetainUntilDate=retain_until.isoformat(),
        )
        self._shadow.write(entry)

    def tail(self, n: int = 20) -> list[dict]:
        return self._shadow.tail(n)

    def status(self) -> dict:
        return {"backend": "s3", "level": 2, "bucket": self.bucket,
                "prefix": self.prefix, "retention_days": self.retention_days,
                "shadow_path": self._shadow.path}


class AzureBackend:
    """Azure Blob Storage with immutability policy."""
    level = 2
    description = "Azure Blob immutable storage — hardware-enforced immutability"

    def __init__(self):
        try:
            from azure.storage.blob import BlobServiceClient
            self._BlobServiceClient = BlobServiceClient
        except ImportError:
            raise RuntimeError("azure-storage-blob required: pip install azure-storage-blob")
        conn = os.environ.get("VALO_WORM_AZURE_CONNECTION_STRING")
        if not conn:
            raise RuntimeError("VALO_WORM_AZURE_CONNECTION_STRING is required")
        self.container = os.environ.get("VALO_WORM_AZURE_CONTAINER", "valo-worm")
        self._client = BlobServiceClient.from_connection_string(conn)
        self._container_client = self._client.get_container_client(self.container)
        self._shadow = FileBackend()

    def write(self, entry: dict) -> None:
        name = f"{entry['ts']:.6f}_{entry.get('hash','')[:16]}.json"
        blob = self._container_client.get_blob_client(name)
        blob.upload_blob(json.dumps(entry, separators=(",", ":")).encode(), overwrite=False)
        self._shadow.write(entry)

    def tail(self, n: int = 20) -> list[dict]:
        return self._shadow.tail(n)

    def status(self) -> dict:
        return {"backend": "azure", "level": 2, "container": self.container,
                "shadow_path": self._shadow.path}


class TPMBackend:
    """TPM2 HMAC-signed entries. Each entry proves machine identity.

    Uses tpm2_hmac CLI (tpm2-tools package). Falls back to software HMAC
    if TPM not available, logging fallback_mode: true in each entry.
    Writes to Nivå 2 or Nivå 1 inner backend (VALO_WORM_TPM_INNER_BACKEND).
    """
    level = 3
    description = "TPM2 HMAC-signed entries (hardware identity proof)"

    def __init__(self):
        self._tpm_available = shutil.which("tpm2_hmac") is not None
        if not self._tpm_available:
            import secrets
            self._software_key = secrets.token_bytes(32)
        inner = os.environ.get("VALO_WORM_TPM_INNER_BACKEND", "file")
        self._inner = {"s3": S3Backend, "azure": AzureBackend}.get(inner, FileBackend)()

    def _sign(self, entry_hash: str) -> dict:
        data = entry_hash.encode()
        if self._tpm_available:
            try:
                with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
                    f.write(data); tmpfile = f.name
                r = subprocess.run(
                    ["tpm2_hmac", "--key-context", "0x81000001", "--hex", "--output", "-", tmpfile],
                    capture_output=True, timeout=5,
                )
                os.unlink(tmpfile)
                if r.returncode == 0:
                    return {"method": "tpm2_hmac", "handle": "0x81000001",
                            "sig": r.stdout.strip().decode()}
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                pass
        sig = hmac.new(self._software_key, data, hashlib.sha256).hexdigest()
        return {"method": "software_hmac", "fallback_mode": True, "sig": sig}

    def write(self, entry: dict) -> None:
        entry["tpm_attestation"] = self._sign(entry.get("hash", ""))
        self._inner.write(entry)

    def tail(self, n: int = 20) -> list[dict]:
        return self._inner.tail(n)

    def status(self) -> dict:
        return {"backend": "tpm", "level": 3, "tpm_available": self._tpm_available,
                "inner_backend": self._inner.status()}


def create_backend():
    """Create WORM backend from VALO_WORM_BACKEND environment variable."""
    name = os.environ.get("VALO_WORM_BACKEND", "file").lower()
    backends = {"file": FileBackend, "s3": S3Backend, "azure": AzureBackend, "tpm": TPMBackend}
    if name not in backends:
        raise RuntimeError(f"Unknown VALO_WORM_BACKEND: {name}. Choose: {', '.join(backends)}")
    return backends[name]()
