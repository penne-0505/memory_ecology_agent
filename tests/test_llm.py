from __future__ import annotations

from io import BytesIO
from urllib.error import HTTPError

import pytest
from pydantic import BaseModel

from app.adapters.llm import (
    ClaudeMessagesClient,
    GeminiGenerateContentClient,
    LLMConfigurationError,
    LLMProviderError,
    MockLLMClient,
    OpenAICompatibleChatClient,
    StateSensitiveFakeLLMClient,
    UrllibJsonTransport,
    create_llm_client,
    openrouter_json_schema_payload,
)
from app.config import Settings


class FakeTransport:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post_json(self, url, headers, payload, timeout_seconds):
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "payload": payload,
                "timeout_seconds": timeout_seconds,
            }
        )
        return self.response


class RequiredJson(BaseModel):
    name: str
    score: float


def make_settings(tmp_path, provider: str, model: str | None = None) -> Settings:
    return Settings(
        project_root=tmp_path,
        db_path=tmp_path / "data" / "agent.db",
        world_root=tmp_path / "world",
        workspace_root=tmp_path / "agent_workspace",
        llm_provider=provider,
        llm_model=model,
    )


def test_inv003_complete_json_validates_with_pydantic():
    client = MockLLMClient(json_response={"name": "ok", "score": 0.5})
    result = client.complete_json("system", "user", RequiredJson)
    assert result.name == "ok"
    assert result.score == 0.5


def test_inv003_invalid_json_response_raises_before_state_update():
    client = MockLLMClient(json_response={"name": "missing-score"})
    with pytest.raises(Exception):
        client.complete_json("system", "user", RequiredJson)


def test_inv001_default_factory_uses_mock_without_network(settings):
    client = create_llm_client(settings)
    assert isinstance(client, MockLLMClient)


def test_state_sensitive_mock_factory_is_offline(tmp_path):
    client = create_llm_client(make_settings(tmp_path, "state_sensitive_mock"))
    assert isinstance(client, StateSensitiveFakeLLMClient)
    assert "state-sensitive-mock" in client.complete_text("Policy: {}", "hello")


def test_ac001_inv002_missing_real_provider_key_is_sanitized(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    with pytest.raises(LLMConfigurationError) as excinfo:
        create_llm_client(make_settings(tmp_path, "openai"))
    message = str(excinfo.value)
    assert "openai" in message
    assert "sk-" not in message


def test_ac001_factory_creates_all_real_provider_clients(tmp_path, monkeypatch):
    cases = [
        ("openai", "OPENAI_API_KEY", "OPENAI_MODEL", OpenAICompatibleChatClient),
        ("claude", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", ClaudeMessagesClient),
        ("gemini", "GEMINI_API_KEY", "GEMINI_MODEL", GeminiGenerateContentClient),
        (
            "openrouter",
            "OPENROUTER_API_KEY",
            "OPENROUTER_MODEL",
            OpenAICompatibleChatClient,
        ),
    ]
    for provider, key_name, model_name, expected_class in cases:
        monkeypatch.setenv(key_name, f"{provider}-key")
        monkeypatch.setenv(model_name, f"{provider}-model")
        client = create_llm_client(make_settings(tmp_path, provider), FakeTransport({}))
        assert isinstance(client, expected_class)


def test_ac002_inv003_openai_request_shape_and_text_parse(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    transport = FakeTransport(
        {"choices": [{"message": {"content": "hello from openai"}}]}
    )
    client = create_llm_client(make_settings(tmp_path, "openai"), transport)

    assert client.complete_text("system", "user") == "hello from openai"
    call = transport.calls[0]
    assert call["url"] == "https://api.openai.com/v1/chat/completions"
    assert call["headers"]["Authorization"] == "Bearer openai-key"
    assert call["payload"]["model"] == "gpt-test"
    assert call["payload"]["max_completion_tokens"] == 1024
    assert "max_tokens" not in call["payload"]
    assert call["payload"]["messages"] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "user"},
    ]


def test_ac002_inv003_openrouter_request_shape_and_attribution_headers(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "openrouter-test")
    monkeypatch.setenv("OPENROUTER_HTTP_REFERER", "https://example.invalid")
    monkeypatch.setenv("OPENROUTER_X_TITLE", "Memory Ecology Agent")
    transport = FakeTransport(
        {"choices": [{"message": {"content": "hello from openrouter"}}]}
    )
    client = create_llm_client(make_settings(tmp_path, "openrouter"), transport)

    assert client.complete_text("system", "user") == "hello from openrouter"
    call = transport.calls[0]
    assert call["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert call["headers"]["Authorization"] == "Bearer openrouter-key"
    assert call["headers"]["HTTP-Referer"] == "https://example.invalid"
    assert call["headers"]["X-Title"] == "Memory Ecology Agent"
    assert call["payload"]["model"] == "openrouter-test"
    assert call["payload"]["max_tokens"] == 1024
    assert "max_completion_tokens" not in call["payload"]


def test_openrouter_structured_output_extra_payload_is_sent(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "openrouter-test")
    transport = FakeTransport(
        {"choices": [{"message": {"content": '{"name":"ok","score":0.5}'}}]}
    )
    client = create_llm_client(
        make_settings(tmp_path, "openrouter"),
        transport,
        extra_payload=openrouter_json_schema_payload(
            RequiredJson,
            name="required_json",
            require_parameters=True,
        ),
    )

    result = client.complete_text_with_metadata("system", "user")
    payload = transport.calls[0]["payload"]

    assert payload["response_format"]["type"] == "json_schema"
    assert payload["response_format"]["json_schema"]["name"] == "required_json"
    assert payload["response_format"]["json_schema"]["strict"] is True
    schema = payload["response_format"]["json_schema"]["schema"]
    assert schema["required"] == ["name", "score"]
    assert schema["additionalProperties"] is False
    assert "default" not in str(schema)
    assert payload["structured_outputs"] is True
    assert payload["provider"] == {"require_parameters": True}
    assert result.response_metadata["structured_output_enabled"] is True
    assert result.response_metadata["structured_outputs"] is True
    assert result.response_metadata["provider_require_parameters"] is True
    assert result.response_metadata["token_parameter"] == "max_tokens"


def test_ac002_inv004_claude_request_shape_and_text_parse(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "claude-key")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-test")
    transport = FakeTransport({"content": [{"type": "text", "text": "hello claude"}]})
    client = create_llm_client(make_settings(tmp_path, "claude"), transport)

    assert client.complete_text("system", "user") == "hello claude"
    call = transport.calls[0]
    assert call["url"] == "https://api.anthropic.com/v1/messages"
    assert call["headers"]["x-api-key"] == "claude-key"
    assert call["headers"]["anthropic-version"] == "2023-06-01"
    assert call["payload"]["system"] == "system"
    assert call["payload"]["messages"] == [{"role": "user", "content": "user"}]
    assert call["payload"]["max_tokens"] == 1024


def test_ac002_inv005_gemini_request_shape_and_text_parse(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test")
    transport = FakeTransport(
        {"candidates": [{"content": {"parts": [{"text": "hello gemini"}]}}]}
    )
    client = create_llm_client(make_settings(tmp_path, "gemini"), transport)

    assert client.complete_text("system", "user") == "hello gemini"
    call = transport.calls[0]
    assert (
        call["url"]
        == "https://generativelanguage.googleapis.com/v1beta/models/gemini-test:generateContent"
    )
    assert call["headers"]["x-goog-api-key"] == "gemini-key"
    assert call["payload"]["contents"][0]["role"] == "user"
    assert call["payload"]["contents"][0]["parts"][0]["text"] == "system\n\nuser"
    assert call["payload"]["generationConfig"]["maxOutputTokens"] == 1024


def test_ac003_inv006_provider_complete_json_extracts_and_validates(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    transport = FakeTransport(
        {
            "choices": [
                {
                    "message": {
                        "content": '```json\n{"name": "ok", "score": 0.75}\n```'
                    }
                }
            ]
        }
    )
    client = create_llm_client(make_settings(tmp_path, "openai"), transport)

    result = client.complete_json("system", "user", RequiredJson)
    assert result.name == "ok"
    assert result.score == 0.75
    request_text = transport.calls[0]["payload"]["messages"][0]["content"]
    assert "Return only a JSON value" in request_text


def test_ac003_inv006_provider_complete_json_invalid_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    transport = FakeTransport({"choices": [{"message": {"content": "{}"}}]})
    client = create_llm_client(make_settings(tmp_path, "openai"), transport)

    with pytest.raises(Exception):
        client.complete_json("system", "user", RequiredJson)


def test_http_error_message_does_not_include_provider_body(monkeypatch):
    def raise_http_error(*args, **kwargs):
        raise HTTPError(
            url="https://api.example.invalid",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=BytesIO(b'{"error":"do not leak prompt or token-like details"}'),
        )

    monkeypatch.setattr("app.adapters.llm.urlopen", raise_http_error)
    transport = UrllibJsonTransport()

    with pytest.raises(LLMProviderError) as excinfo:
        transport.post_json(
            "https://api.example.invalid",
            {"Authorization": "Bearer secret"},
            {"prompt": "private"},
            1.0,
        )

    message = str(excinfo.value)
    assert "status=401" in message
    assert "secret" not in message
    assert "private" not in message
    assert "do not leak" not in message
