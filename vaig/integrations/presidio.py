"""Microsoft Presidio PII detection adapter — fully open source, runs locally."""

from vaig.integrations.base import ExternalAdapter


class PresidioPIIAdapter(ExternalAdapter):
    name = "presidio_pii"
    _import = "presidio_analyzer"

    def _call(self, prompt: str, response: str) -> float:
        from presidio_analyzer import AnalyzerEngine

        engine = AnalyzerEngine()
        prompt_hits = engine.analyze(text=prompt, language="en")
        response_hits = engine.analyze(text=response, language="en")
        return min(1.0, max(len(prompt_hits), len(response_hits)) * 0.25)
