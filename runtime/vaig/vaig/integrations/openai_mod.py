"""OpenAI Moderation API adapter (free endpoint, no model charge)."""

import os

from vaig.integrations.base import ExternalAdapter


class OpenAIModerationAdapter(ExternalAdapter):
    name = "openai_moderation"
    _import = "openai"

    def _call(self, prompt: str, response: str) -> float:
        import openai

        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        result = client.moderations.create(input=response)
        scores = vars(result.results[0].category_scores)
        return max(float(v) for v in scores.values())
