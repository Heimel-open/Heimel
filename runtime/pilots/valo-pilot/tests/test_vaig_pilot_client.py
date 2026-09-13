"""Tests for VALO Pilot LLM client compatibility."""

from unittest.mock import MagicMock, patch

import pytest

import vaig_pilot


def test_extract_ollama_response():
    assert vaig_pilot._extract_response_text({"response": "hello"}) == "hello"


def test_extract_openai_chat_response():
    payload = {"choices": [{"message": {"content": "hello chat"}}]}
    assert vaig_pilot._extract_response_text(payload) == "hello chat"


def test_extract_openai_legacy_text_response():
    payload = {"choices": [{"text": "hello text"}]}
    assert vaig_pilot._extract_response_text(payload) == "hello text"


def test_extract_response_rejects_empty_payload():
    with pytest.raises(ValueError, match="extractable text"):
        vaig_pilot._extract_response_text({"choices": []})


def test_llm_call_uses_openai_chat_payload(monkeypatch):
    monkeypatch.setattr(vaig_pilot, "LLM_API_URL", "https://api.openai.com/v1/chat/completions")
    monkeypatch.setattr(vaig_pilot, "LLM_MODEL", "gpt-test")
    monkeypatch.setattr(vaig_pilot, "LLM_API_KEY", "secret")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
    mock_resp.raise_for_status = MagicMock()

    with patch("vaig_pilot.requests.post", return_value=mock_resp) as post:
        assert vaig_pilot.llm_call("hello") == "ok"

    kwargs = post.call_args.kwargs
    assert kwargs["json"]["messages"] == [{"role": "user", "content": "hello"}]
    assert "prompt" not in kwargs["json"]
    assert kwargs["headers"]["Authorization"] == "Bearer secret"
    mock_resp.raise_for_status.assert_called_once()


def test_llm_call_uses_ollama_payload(monkeypatch):
    monkeypatch.setattr(vaig_pilot, "LLM_API_URL", "http://localhost:11434/api/generate")
    monkeypatch.setattr(vaig_pilot, "LLM_MODEL", "llama3")
    monkeypatch.setattr(vaig_pilot, "LLM_API_KEY", "")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": "ok"}
    mock_resp.raise_for_status = MagicMock()

    with patch("vaig_pilot.requests.post", return_value=mock_resp) as post:
        assert vaig_pilot.llm_call("hello") == "ok"

    kwargs = post.call_args.kwargs
    assert kwargs["json"]["prompt"] == "hello"
    assert kwargs["json"]["stream"] is False
    assert "Authorization" not in kwargs["headers"]
    mock_resp.raise_for_status.assert_called_once()
