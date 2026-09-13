"""Judge providers — turn a JudgeSpec into a concrete model call.

Hosted (OpenAI-compatible), local (Ollama/vLLM) and deterministic providers
share one interface so the multiverse can run any mix of public, private and
self-trained judges behind the same ``judge_fn``.
"""

from __future__ import annotations

import os
from typing import Callable, Mapping, Protocol

import requests

from vaig.judge.spec import JudgeSpec

DEFAULT_CHAT_URL = "https://api.openai.com/v1/chat/completions"


class JudgeProvider(Protocol):
    """Anything that turns a prompt into a judge verdict for a spec."""

    def complete(self, prompt: str, spec: JudgeSpec) -> str:
        ...


class HTTPJudgeProvider:
    """OpenAI-compatible chat-completions judge over HTTP(S).

    Works for hosted APIs (OpenAI) and local servers exposing the same
    interface (Ollama, vLLM, LM Studio). The API key comes from
    ``VAIG_JUDGE_API_KEY`` or ``OPENAI_API_KEY``.
    """

    def __init__(
        self,
        api_key_env: str = "VAIG_JUDGE_API_KEY",
        default_url: str = DEFAULT_CHAT_URL,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.api_key_env = api_key_env
        self.default_url = default_url
        self.timeout_seconds = timeout_seconds

    def complete(self, prompt: str, spec: JudgeSpec) -> str:
        url = spec.endpoint or self.default_url
        # Accept a base URL (e.g. NVIDIA NIM https://host/v1) or a full path;
        # never POST to a bare base.
        if not url.rstrip("/").endswith("/chat/completions"):
            url = url.rstrip("/") + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        key = os.environ.get(self.api_key_env) or os.environ.get("OPENAI_API_KEY")
        if key:
            headers["Authorization"] = f"Bearer {key}"

        payload: dict = {
            "model": spec.model_id,
            "messages": [
                {"role": "system", "content": "You are a strict safety judge."},
                {"role": "user", "content": prompt},
            ],
            "temperature": spec.temperature,
            "max_tokens": spec.max_tokens,
        }
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout_seconds)
                if resp.status_code >= 500:
                    last_error = RuntimeError(f"judge {resp.status_code} for {spec.model_id}")
                    import time

                    time.sleep(2 * (attempt + 1))
                    continue
                resp.raise_for_status()
                break
            except requests.exceptions.RequestException as exc:
                last_error = exc
                if attempt == 2:
                    raise
                import time

                time.sleep(2 * (attempt + 1))
        else:
            raise last_error  # type: ignore[misc]
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"unexpected judge response from {spec.model_id}") from exc


class DeterministicJudgeProvider:
    """Controllable judge for tests and offline simulation.

    ``respond`` maps a spec (or spec + prompt) to a fixed verdict string, so
    the multiverse behaviour is deterministic and auditable offline.
    """

    def __init__(
        self,
        respond: Callable[[str, JudgeSpec], str],
    ) -> None:
        self._respond = respond

    def complete(self, prompt: str, spec: JudgeSpec) -> str:
        return self._respond(prompt, spec)


class VerdictMapProvider(DeterministicJudgeProvider):
    """Deterministic judge that returns a fixed verdict per judge identity.

    Useful to simulate disagreement: two specs with the same model but
    different temperature can return different verdicts, exactly like the real
    sampling variance we want the multiverse to surface.
    """

    def __init__(self, verdicts: Mapping[str, str], default: str = "INCONCLUSIVE") -> None:
        super().__init__(lambda prompt, spec: verdicts.get(spec.stable_id, default))


def build_generate_fn(
    model_id: str | None = None,
    endpoint: str | None = None,
    api_key_env: str = "NVIDIA_API_KEY",
) -> "Callable[[str], str]":
    """Build a ``generate_fn`` (prompt -> response) from the environment.

    Uses the same NVIDIA/OpenAI-compatible convention as the judge: reads
    NVIDIA_API_KEY (or NVAPI_KEY), NVIDIA_BASE_URL and VAIG_GENERATE_MODEL.
    Raises when no key is configured — the caller decides whether to run on
    the model or fail closed.
    """
    import os

    from vaig.judge.factory import JudgeFactory
    from vaig.judge.spec import JudgeSpec

    key = os.environ.get(api_key_env) or os.environ.get("NVAPI_KEY")
    if not key:
        raise RuntimeError("no NVIDIA_API_KEY configured for generate_fn")
    spec = JudgeSpec(
        provider="nvidia-generate",
        model_id=model_id or os.environ.get(
            "VAIG_GENERATE_MODEL", "meta/llama-3.3-70b-instruct"
        ),
        model_version="free-tier",
        temperature=float(os.environ.get("VAIG_GENERATE_TEMPERATURE", "0.6")),
        endpoint=endpoint or os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        provenance="public",
    )
    return JudgeFactory(HTTPJudgeProvider(api_key_env=api_key_env)).build(spec)
