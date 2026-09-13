from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class FunctionRef(BaseModel):
    """Pinned function identity: id + version."""

    function_id: str
    version: str

    model_config = ConfigDict(extra="forbid", frozen=True)

    @property
    def identity(self) -> str:
        return f"{self.function_id}@{self.version}"


def parse_identity(identity: str) -> FunctionRef:
    """Parse 'valo.finance.pay@1.0.0' into a pinned FunctionRef."""
    if "@" not in identity:
        raise ValueError(f"function identity must be pinned with a version: {identity}")
    function_id, version = identity.rsplit("@", 1)
    if not function_id or not version:
        raise ValueError(f"malformed function identity: {identity}")
    return FunctionRef(function_id=function_id, version=version)
