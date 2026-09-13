from dataclasses import dataclass, field
from typing import Any


@dataclass
class AuditReceipt:
    """Portable receipt shape; persistence and WORM implementation stay external."""

    id: str
    ts: float
    prev: str
    hash: str
    prompt_sha256: str | None = None
    response_sha256: str | None = None
    prompt_enc: str | None = None
    response_enc: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AuditReceipt":
        known = {
            "id", "ts", "prev", "hash", "prompt_sha256", "response_sha256",
            "prompt_enc", "response_enc",
        }
        return cls(
            id=value.get("id", ""),
            ts=value.get("ts", 0.0),
            prev=value.get("prev", "genesis"),
            hash=value.get("hash", ""),
            prompt_sha256=value.get("prompt_sha256"),
            response_sha256=value.get("response_sha256"),
            prompt_enc=value.get("prompt_enc"),
            response_enc=value.get("response_enc"),
            extra={key: item for key, item in value.items() if key not in known},
        )
