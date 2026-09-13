"""
VALO Pilot — VAIG wrapper for customer LLM pipeline.

Drop-in validation layer. Replace llm_call() with customer's API function.
WORM audit log starts from first inference.

Usage:
    from vaig_pilot import validated_call
    response, result = validated_call("Your prompt here")
"""

from __future__ import annotations

from typing import Any

import requests
from vaig import VAIGEnsemble

from config import AUDIT_LOG_PATH, L4_AUTO_TRIGGER, LLM_API_KEY, LLM_API_URL, LLM_MODEL

ensemble = VAIGEnsemble(
    log_path=AUDIT_LOG_PATH,
    l4_auto_trigger=L4_AUTO_TRIGGER,
)


def llm_call(prompt: str, temperature: float = 0.3) -> str:
    """Call an OpenAI-compatible or Ollama-compatible LLM endpoint."""
    headers = {"Authorization": f"Bearer {LLM_API_KEY}"} if LLM_API_KEY else {}
    headers["Content-Type"] = "application/json"

    if _looks_openai_chat_endpoint(LLM_API_URL):
        payload: dict[str, Any] = {
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
    else:
        payload = {
            "model": LLM_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }

    resp = requests.post(
        LLM_API_URL,
        json=payload,
        headers=headers,
        timeout=60,
    )
    resp.raise_for_status()
    return _extract_response_text(resp.json())


def validated_call(prompt: str):
    """
    Validated LLM call. Returns (response, ValidationResult).
    Logs every inference to tamper-evident WORM audit trail.
    """
    response = llm_call(prompt)

    result = ensemble.evaluate(
        prompt=prompt,
        response=response,
        generate_fn=llm_call,
    )

    return response, result


def audit_status() -> dict[str, object]:
    """Return and print current audit log statistics."""
    entries = ensemble.worm.read_all()
    total = len(entries)
    levels: dict[str, int] = {}
    for entry in entries:
        level = str(entry.get("level", entry.get("distrust_level", "UNKNOWN")))
        levels[level] = levels.get(level, 0) + 1

    stats: dict[str, object] = {
        "total": total,
        "levels": levels,
    }
    print(f"Total inferences : {total}")
    print(f"Levels           : {levels}")
    return stats


def _looks_openai_chat_endpoint(url: str) -> bool:
    return "/chat/completions" in url.rstrip("/")


def _extract_response_text(payload: dict[str, Any]) -> str:
    """Extract model text from OpenAI-compatible or Ollama-compatible responses."""
    if isinstance(payload.get("response"), str):
        return payload["response"]

    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                return message["content"]
            if isinstance(first.get("text"), str):
                return first["text"]

    raise ValueError("LLM response did not contain extractable text")
