"""Named stubs for known tools not yet fully wired."""

import os

import requests

from vaig.integrations.base import ExternalAdapter


class LangkitHallucinationAdapter(ExternalAdapter):
    name = "langkit_hallucination"
    _import = "langkit"

    def _call(self, prompt: str, response: str) -> float:
        from langkit.hallucination import hallucination
        score = hallucination(response, context=prompt)
        # None means model could not evaluate — return neutral 0.5, not 0.0 (safe)
        return float(score) if score is not None else 0.5


class LangkitToxicityAdapter(ExternalAdapter):
    name = "langkit_toxicity"
    _import = "langkit"

    def _call(self, prompt: str, response: str) -> float:
        from langkit.toxicity import toxicity
        score = toxicity(response)
        # None means the model could not evaluate — return neutral 0.5, not 0.0 (safe)
        return float(score) if score is not None else 0.5


class AzureContentSafetyAdapter(ExternalAdapter):
    """
    Azure Content Safety REST adapter.

    Requires:
      AZURE_CONTENT_SAFETY_KEY      — subscription key
      AZURE_CONTENT_SAFETY_ENDPOINT — e.g. https://<resource>.cognitiveservices.azure.com
    """

    name = "azure_content_safety"
    _import = "azure.ai.contentsafety"

    _API_VERSION = "2023-10-01"

    def _call(self, prompt: str, response: str) -> float:
        key = os.environ.get("AZURE_CONTENT_SAFETY_KEY", "")
        endpoint = os.environ.get("AZURE_CONTENT_SAFETY_ENDPOINT", "").rstrip("/")
        if not key or not endpoint:
            return 0.0

        url = f"{endpoint}/contentsafety/text:analyze?api-version={self._API_VERSION}"
        headers = {"Ocp-Apim-Subscription-Key": key, "Content-Type": "application/json"}
        payload = {"text": response}

        resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout_seconds)
        resp.raise_for_status()
        categories = resp.json().get("categoriesAnalysis", [])

        # Severity is 0–7; normalise to 0.0–1.0
        if not categories:
            return 0.0
        return max(item.get("severity", 0) for item in categories) / 7.0
