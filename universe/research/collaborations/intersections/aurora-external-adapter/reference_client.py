from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class AuroraAdapterError(RuntimeError):
    pass


@dataclass(frozen=True)
class AuroraAssessment:
    governance: str
    response_text: str
    session_id: str | None
    audit_id: str | None
    turn: int | None
    raw_aurora: dict[str, Any]
    raw_response: dict[str, Any]

    @property
    def admitted(self) -> bool:
        return self.governance in {"PASS", "SOFT_CORRECT"}

    @property
    def non_admit(self) -> bool:
        return self.governance in {"CONTAIN", "FORCE_REVISE", "HARD_STOP"}


class AuroraLensClient:
    """Thin external client for an independently deployed Aurora-Lens service.

    This client does not reproduce Aurora policy or modify Aurora outcomes.
    It transports an OpenAI-compatible request and requires the native
    `aurora` governance block in the response.
    """

    def __init__(self, base_url: str, *, api_key: str | None = None, timeout_s: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_s = timeout_s

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health", None, {})

    def assess(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str = "aurora-lens",
        session_id: str | None = None,
        operator_detail: bool = False,
        extra_body: dict[str, Any] | None = None,
    ) -> AuroraAssessment:
        body: dict[str, Any] = {"model": model, "messages": messages, "stream": False}
        if extra_body:
            body.update(extra_body)

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if session_id:
            headers["X-Aurora-Session-Id"] = session_id
        if operator_detail:
            headers["X-Aurora-Operator-Detail"] = "true"

        payload = self._request("POST", "/v1/chat/completions", body, headers)
        aurora = payload.get("aurora")
        if not isinstance(aurora, dict):
            raise AuroraAdapterError("Aurora response missing required 'aurora' governance block")

        governance = str(aurora.get("governance") or "").upper().strip()
        allowed = {"PASS", "SOFT_CORRECT", "CONTAIN", "FORCE_REVISE", "HARD_STOP"}
        if governance not in allowed:
            raise AuroraAdapterError(f"Unknown or missing Aurora governance outcome: {governance!r}")

        choices = payload.get("choices")
        text = ""
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, dict):
                message = first.get("message")
                if isinstance(message, dict):
                    content = message.get("content")
                    if content is not None:
                        text = str(content)

        turn_raw = aurora.get("turn")
        turn = turn_raw if isinstance(turn_raw, int) else None
        return AuroraAssessment(
            governance=governance,
            response_text=text,
            session_id=_opt_str(aurora.get("session_id")),
            audit_id=_opt_str(aurora.get("audit_id")),
            turn=turn,
            raw_aurora=aurora,
            raw_response=payload,
        )

    def _request(self, method: str, path: str, body: dict[str, Any] | None, headers: dict[str, str]) -> dict[str, Any]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(self.base_url + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise AuroraAdapterError(f"Aurora HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise AuroraAdapterError(f"Aurora unavailable: {exc.reason}") from exc

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AuroraAdapterError("Aurora returned non-JSON response") from exc
        if not isinstance(parsed, dict):
            raise AuroraAdapterError("Aurora returned non-object JSON")
        return parsed


def _opt_str(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None
