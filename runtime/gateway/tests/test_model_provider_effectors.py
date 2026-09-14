import pytest

from valo_gateway.tool_adapters import (
    AzureOpenAIEffectTool,
    BedrockEffectTool,
    GroqEffectTool,
    HuggingFaceEffectTool,
    OllamaEffectTool,
    OpenRouterEffectTool,
    TogetherEffectTool,
    VertexAIEffectTool,
)


@pytest.mark.parametrize(
    ("tool_type", "provider"),
    [
        (OpenRouterEffectTool, "openrouter"),
        (BedrockEffectTool, "aws-bedrock"),
        (AzureOpenAIEffectTool, "azure-openai"),
        (VertexAIEffectTool, "vertex-ai"),
        (TogetherEffectTool, "together"),
        (GroqEffectTool, "groq"),
        (HuggingFaceEffectTool, "huggingface"),
        (OllamaEffectTool, "ollama"),
    ],
)
def test_model_provider_effectors_are_boundary_only(tool_type, provider):
    calls = []
    tool = tool_type(lambda operation, parameters: calls.append((operation, parameters)))

    assert tool.provider == provider
    with pytest.raises(PermissionError, match="NO_DIRECT_EFFECT_PATH"):
        tool.invoke({"operation": "model.invoke", "model": "example"})
    assert calls == []
