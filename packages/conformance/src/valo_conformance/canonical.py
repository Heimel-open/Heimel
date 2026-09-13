from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from hashlib import sha256
from typing import Any

import rfc8785
from pydantic import BaseModel


def _json_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _json_value(value.model_dump(mode="json", exclude_none=False))
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z") if value.utcoffset() else value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported_conformance_value:{type(value).__name__}")


def canonical_digest(value: Any) -> str:
    return f"sha256:{sha256(rfc8785.dumps(_json_value(value))).hexdigest()}"
