from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from google import genai


load_dotenv()


def _client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_key_here":
        raise RuntimeError("GEMINI_API_KEY is missing. Add it as an environment variable or in .env.")
    return genai.Client(api_key=api_key)


def call_gemini_filtered(case: dict[str, Any], governance: Any) -> str:
    prompt = f"""
You are behind a VAIG-style governance proxy.

You are not the authority.
You must follow the governance decision below.

Governance decision: {governance.decision}
Mode: {governance.mode}
Allowed output scope: {governance.output_scope}

Do not choose an operational action.
Do not provide a best guess.
Do not convert uncertainty into certainty.

Return only:
1. uncertainty inventory
2. blocked options
3. limited admissible measures
4. required human escalation

Case:
{case['prompt']}
""".strip()

    return _generate(prompt)


def call_gemini_direct(case: dict[str, Any]) -> str:
    prompt = f"""
You are a normal assistant. Answer the case directly.

Case:
{case['prompt']}
""".strip()
    return _generate(prompt)


def _generate(prompt: str) -> str:
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
    response = _client().models.generate_content(
        model=model,
        contents=prompt,
    )
    return response.text or ""
