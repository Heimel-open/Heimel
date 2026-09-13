"""Detoxify (HuggingFace) toxicity adapter — fully open source, runs locally."""

from vaig.integrations.base import ExternalAdapter


class DetoxifyAdapter(ExternalAdapter):
    name = "detoxify_toxicity"
    _import = "detoxify"

    _model = None  # class-level cache so the model loads once per process

    def _call(self, prompt: str, response: str) -> float:
        if DetoxifyAdapter._model is None:
            from detoxify import Detoxify
            DetoxifyAdapter._model = Detoxify("original")

        results = DetoxifyAdapter._model.predict(response)
        return max(float(v) for v in results.values())
