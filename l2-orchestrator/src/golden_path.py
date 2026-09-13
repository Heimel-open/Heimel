import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional


class RacsGoldenPathRuntime:
    """
    Runtime wrapper for the Rust RACS -> AI-PLS golden path bridge.

    This keeps the Python runtime on a single explicit execution path:
    permit JSON -> bridge CLI -> receipt JSON.
    """

    def __init__(self, command: Optional[list[str]] = None):
        self._command = command or self._default_command()

    def _default_command(self) -> list[str]:
        repo_root = Path(__file__).resolve().parents[2]
        manifest = repo_root / "ai-pls-racs-bridge" / "Cargo.toml"
        cargo = os.environ.get("CARGO", "cargo")
        target_dir = Path(os.environ.get("CARGO_TARGET_DIR", repo_root / "target"))
        if not target_dir.is_absolute():
            target_dir = repo_root / target_dir
        binary_name = "ai-pls-racs-bridge.exe" if sys.platform == "win32" else "ai-pls-racs-bridge"
        binary = target_dir / "debug" / binary_name
        if not binary.is_file():
            completed = subprocess.run(
                [cargo, "build", "--quiet", "--manifest-path", str(manifest), "--bin", "ai-pls-racs-bridge"],
                cwd=repo_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if completed.returncode != 0 or not binary.is_file():
                detail = completed.stderr.decode("utf-8", errors="replace").strip()
                raise RuntimeError(detail or "golden path bridge build failed")
        return [str(binary)]

    def process_permit(
        self,
        permit: dict[str, Any],
        trusted_issuer: dict[str, Any],
        now_epoch_ms: Optional[int] = None,
        revocation_registry_path: Optional[str] = None,
    ) -> dict[str, Any]:
        request = {
            "permit": permit,
            "trusted_issuer": trusted_issuer,
            "now_epoch_ms": now_epoch_ms,
            "revocation_registry_path": revocation_registry_path,
        }
        completed = subprocess.run(
            self._command,
            input=json.dumps(request).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                completed.stderr.decode("utf-8", errors="replace").strip() or "golden path bridge failed"
            )
        stdout = completed.stdout.decode("utf-8")
        try:
            return json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"invalid_response:{stdout.strip() or '<empty>'}") from exc
