from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class AuditReceipt:
    id: str
    ts: float
    prev: str
    hash: str
    prompt_sha256: Optional[str] = None
    response_sha256: Optional[str] = None
    prompt_enc: Optional[str] = None
    response_enc: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "AuditReceipt":
        known = {
            "id", "ts", "prev", "hash",
            "prompt_sha256", "response_sha256",
            "prompt_enc", "response_enc",
        }
        return cls(
            id=d.get("id", ""),
            ts=d.get("ts", 0.0),
            prev=d.get("prev", "genesis"),
            hash=d.get("hash", ""),
            prompt_sha256=d.get("prompt_sha256"),
            response_sha256=d.get("response_sha256"),
            prompt_enc=d.get("prompt_enc"),
            response_enc=d.get("response_enc"),
            extra={k: v for k, v in d.items() if k not in known},
        )
