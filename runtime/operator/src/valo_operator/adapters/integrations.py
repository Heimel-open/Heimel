"""Concrete production integrations: Operator Gateway/Veritas pairs bound to
real external services over HTTP.

Each integration is PURE TRANSPORT + OBSERVATION — it carries no authorization
logic (acceptance criterion 9): the Operator contract flows through unchanged.
The effect lives in the external service's own state, verified by reading it
back independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .http_gateway import HttpGateway
from .http_veritas import HttpVeritas


@dataclass(frozen=True)
class Integration:
    """A gateway + veritas pair bound to one external service."""

    name: str
    gateway: HttpGateway
    veritas: HttpVeritas


def notification_integration(base_url: str) -> Integration:
    return Integration(
        name="notifier",
        gateway=HttpGateway(base_url, endpoint="/"),
        veritas=HttpVeritas(base_url, records_endpoint="/records/"),
    )


def ledger_integration(base_url: str) -> Integration:
    return Integration(
        name="ledger",
        gateway=HttpGateway(base_url, endpoint="/"),
        veritas=HttpVeritas(base_url, records_endpoint="/entries/"),
    )


def spawn_service(
    module: str,
    landing: str | None = None,
    mode: str | None = None,
    landing_by_action: dict[str, str] | None = None,
    ready_prefix: str = "READY",
) -> Any:
    """Spawn one standalone external service as a SEPARATE process. Returns a
    handle with .base_url and .stop(). The effect lives in that process."""
    import json
    import os
    import re
    import subprocess
    import sys
    import time

    env = dict(os.environ)
    if landing:
        env["NOTIFIER_LANDING"] = landing
    if landing_by_action:
        env["NOTIFIER_LANDING_BY_ACTION"] = json.dumps(landing_by_action)
    if mode:
        env["LEDGER_MODE"] = mode
    proc = subprocess.Popen(
        [sys.executable, "-m", module, "0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=env,
        text=True,
    )
    deadline = time.time() + 15
    line = None
    while time.time() < deadline:
        line = proc.stdout.readline()  # type: ignore[union-attr]
        if line:
            break
        if proc.poll() is not None:
            raise RuntimeError(f"service {module} exited early")
    if not line:
        proc.kill()
        raise RuntimeError(f"service {module} did not become ready")
    match = re.search(rf"({ready_prefix})\s+([\d.]+):(\d+)", line)
    if not match:
        proc.kill()
        raise RuntimeError(f"unexpected service output: {line!r}")
    host, port = match.group(2), match.group(3)
    base_url = f"http://{host}:{port}"

    class _Handle:
        def __init__(self) -> None:
            self.base_url = base_url

        def stop(self) -> None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    return _Handle()
