"""Local relAIon node runtime.

The node owns continuity-bearing local state. Surfaces and capability providers are
replaceable peripherals and never own canonical identity or memory.
"""

from __future__ import annotations

import json
import os
import platform
import socket
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from paios.memory import CanonicalMemory
from paios.seed import DevelopmentalSeed, DevelopmentalState


NODE_SCHEMA = "relaion-node/v1"
DEFAULT_NODE_NAME = "Alpha"


class CapabilityProvider(Protocol):
    """Replaceable capability boundary. Providers receive scoped requests only."""

    provider_id: str

    def health(self) -> bool: ...


@dataclass(frozen=True)
class NodeIdentity:
    node_name: str
    seed_id: str
    identity_root: str
    lineage_root: str
    born_at: str
    governance_contract: str
    schema: str = NODE_SCHEMA


class RelAIonNode:
    """Continuity-bearing local runtime for one relAIon node."""

    def __init__(self, state_dir: Path, node_name: str = DEFAULT_NODE_NAME) -> None:
        self.state_dir = state_dir.expanduser().resolve()
        self.node_name = node_name
        self.identity_path = self.state_dir / "identity.json"
        self.memory_path = self.state_dir / "memory.jsonl"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.memory = CanonicalMemory(self.memory_path)
        self._identity = self._load_or_birth()
        self.development: DevelopmentalState = self._seed_from_identity().awaken()

    @property
    def identity(self) -> NodeIdentity:
        return self._identity

    def _load_or_birth(self) -> NodeIdentity:
        if self.identity_path.exists():
            data = json.loads(self.identity_path.read_text())
            identity = NodeIdentity(**data)
            if identity.node_name != self.node_name:
                raise ValueError(
                    f"state belongs to node {identity.node_name!r}, not {self.node_name!r}"
                )
            return identity

        now = datetime.now(timezone.utc)
        host = socket.gethostname()
        birth_material = f"{self.node_name}:{host}:{now.isoformat()}"
        import hashlib

        root = hashlib.sha256(birth_material.encode()).hexdigest()
        identity = NodeIdentity(
            node_name=self.node_name,
            seed_id=f"seed-{root[:16]}",
            identity_root=f"id-{root}",
            lineage_root=f"lineage-{root}",
            born_at=now.isoformat(),
            governance_contract=os.environ.get(
                "RELAION_GOVERNANCE_CONTRACT", "reht://required"
            ),
        )
        self._atomic_write_identity(identity)
        return identity

    def _atomic_write_identity(self, identity: NodeIdentity) -> None:
        tmp = self.identity_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(identity), indent=2) + "\n")
        os.chmod(tmp, 0o600)
        tmp.replace(self.identity_path)

    def _seed_from_identity(self) -> DevelopmentalSeed:
        return DevelopmentalSeed(
            seed_id=self.identity.seed_id,
            identity_root=self.identity.identity_root,
            lineage_root=self.identity.lineage_root,
            born_at=datetime.fromisoformat(self.identity.born_at),
            governance_contract=self.identity.governance_contract,
        )

    def health(self) -> dict[str, object]:
        return {
            "ok": True,
            "schema": NODE_SCHEMA,
            "node": self.identity.node_name,
            "identity_root": self.identity.identity_root,
            "memory_records": self.memory.count(),
            "hostname": socket.gethostname(),
            "platform": platform.system().lower(),
            "provider_required_for_continuity": False,
            "reht_required_for_effects": True,
        }
