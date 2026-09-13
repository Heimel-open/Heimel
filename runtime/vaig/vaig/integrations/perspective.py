"""Perspective API (Google/Jigsaw) toxicity adapter."""

import os

import requests

from vaig.integrations.base import ExternalAdapter

_URL = "https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze"


class PerspectiveToxicityAdapter(ExternalAdapter):
    name = "perspective_toxicity"
    _import = ""  # requests is stdlib-adjacent, always present

    def _call(self, prompt: str, response: str) -> float:
        key = os.environ.get("PERSPECTIVE_API_KEY", "")
        if not key:
            return 0.0

        payload = {
            "comment": {"text": response},
            "requestedAttributes": {"TOXICITY": {}},
        }
        resp = requests.post(
            _URL,
            params={"key": key},
            json=payload,
            timeout=self.timeout_seconds,
        )
        resp.raise_for_status()
        return float(
            resp.json()["attributeScores"]["TOXICITY"]["summaryScore"]["value"]
        )
