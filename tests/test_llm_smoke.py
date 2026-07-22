from __future__ import annotations

from sqlalchemy import select

from app.adapters.llm import LLMProviderError
from app.cli.commands import main
from app.db.json_utils import json_loads
from app.db.models import Action, CoreProfile
from app.runtime.llm_smoke import (
    SKIPPED_NO_CREDENTIALS,
    SMOKE_MARKER,
    run_llm_provider_smoke,
)


PROVIDER_ENV_NAMES = [
    "AGENT_LLM_PROVIDER",
    "AGENT_LLM_MODEL",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_MODEL",
    "CLAUDE_API_KEY",
    "CLAUDE_MODEL",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "GOOGLE_API_KEY",
    "GOOGLE_MODEL",
    "OPENROUTER_API_KEY",
    "OPENROUTER_MODEL",
]


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


class FailingTransport:
    def __init__(self, error_message: str):
        self.error_message = error_message
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
        raise LLMProviderError(self.error_message)


def clear_provider_env(monkeypatch) -> None:
    for name in PROVIDER_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def latest_smoke_payload(session):
    action = session.scalars(
        select(Action)
        .where(Action.action_type == "llm_provider_smoke")
        .order_by(Action.id.desc())
        .limit(1)
    ).one()
    return action, json_loads(action.payload_json, {})


def test_ac008_llm_smoke_skips_without_credentials_and_network(
    seeded_session, settings, monkeypatch
):
    clear_provider_env(monkeypatch)
    transport = FakeTransport({})

    result = run_llm_provider_smoke(
        seeded_session,
        settings,
        transport=transport,
    )

    assert result.status == "skipped"
    assert result.exit_code == 0
    assert result.message == SKIPPED_NO_CREDENTIALS
    assert transport.calls == []
    _, payload = latest_smoke_payload(seeded_session)
    assert payload["status"] == "skipped"
    assert payload["provider"] is None
    assert "api_key" not in str(payload).lower()


def test_ac007_inv011_mock_smoke_succeeds_without_core_profile_mutation(
    seeded_session, settings, monkeypatch
):
    clear_provider_env(monkeypatch)
    monkeypatch.setenv("AGENT_LLM_PROVIDER", "mock")
    before = seeded_session.scalar(select(CoreProfile).order_by(CoreProfile.id)).content

    result = run_llm_provider_smoke(seeded_session, settings)

    after = seeded_session.scalar(select(CoreProfile).order_by(CoreProfile.id)).content
    assert result.status == "success"
    assert result.provider == "mock"
    assert result.marker_present is True
    assert result.message == f"OK: {SMOKE_MARKER}"
    assert after == before
    _, payload = latest_smoke_payload(seeded_session)
    assert payload["status"] == "success"
    assert payload["response_marker_present"] is True
    assert payload["usage"] == {}


def test_ac010_real_smoke_fake_transport_traces_usage_without_secret(
    seeded_session, settings, monkeypatch
):
    clear_provider_env(monkeypatch)
    monkeypatch.setenv("AGENT_LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    transport = FakeTransport(
        {
            "choices": [
                {
                    "message": {"content": f"\n{SMOKE_MARKER}\n"},
                    "finish_reason": "stop",
                }
            ],
            "model": "gpt-test-response",
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 3,
                "total_tokens": 15,
            },
        }
    )

    result = run_llm_provider_smoke(
        seeded_session,
        settings,
        transport=transport,
    )

    assert result.status == "success"
    assert result.provider == "openai"
    assert result.model == "gpt-test-response"
    assert result.usage["total_tokens"] == 15
    call = transport.calls[0]
    assert call["payload"]["max_completion_tokens"] == 16
    assert call["payload"]["temperature"] == 0.0
    assert call["timeout_seconds"] == 15.0
    assert call["headers"]["Authorization"] == "Bearer openai-secret-key"
    _, payload = latest_smoke_payload(seeded_session)
    payload_text = str(payload)
    assert payload["usage"]["total_tokens"] == 15
    assert payload["response_metadata"]["finish_reason"] == "stop"
    assert "openai-secret-key" not in payload_text
    assert "Authorization" not in payload_text
    assert "messages" not in payload_text


def test_ac010_openrouter_smoke_disables_reasoning_for_marker_check(
    seeded_session, settings, monkeypatch
):
    clear_provider_env(monkeypatch)
    monkeypatch.setenv("AGENT_LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-secret-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-pro")
    transport = FakeTransport(
        {
            "choices": [{"message": {"content": SMOKE_MARKER}}],
            "model": "deepseek/deepseek-v4-pro-20260423",
            "usage": {"total_tokens": 9},
        }
    )

    result = run_llm_provider_smoke(
        seeded_session,
        settings,
        transport=transport,
    )

    assert result.status == "success"
    call = transport.calls[0]
    assert call["payload"]["reasoning"] == {"effort": "none", "exclude": True}
    _, payload = latest_smoke_payload(seeded_session)
    assert payload["status"] == "success"
    assert "openrouter-secret-key" not in str(payload)


def test_ac010_provider_error_is_sanitized_in_output_and_trace(
    seeded_session, settings, monkeypatch
):
    clear_provider_env(monkeypatch)
    monkeypatch.setenv("AGENT_LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    transport = FailingTransport("provider error contained openai-secret-key")

    result = run_llm_provider_smoke(
        seeded_session,
        settings,
        transport=transport,
    )

    assert result.status == "failed"
    assert result.exit_code == 1
    assert "openai-secret-key" not in result.message
    assert "[redacted]" in result.message
    _, payload = latest_smoke_payload(seeded_session)
    assert payload["status"] == "failed"
    assert payload["error_class"] == "LLMProviderError"
    assert "openai-secret-key" not in str(payload)


def test_ac009_multiple_credentials_require_explicit_provider(
    seeded_session, settings, monkeypatch
):
    clear_provider_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-secret-key")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-test")

    result = run_llm_provider_smoke(seeded_session, settings)

    assert result.status == "failed"
    assert result.exit_code == 1
    assert "Multiple real provider credentials detected" in result.message
    assert "set AGENT_LLM_PROVIDER explicitly" in result.message
    _, payload = latest_smoke_payload(seeded_session)
    assert payload["status"] == "failed"
    assert "openai-secret-key" not in str(payload)
    assert "anthropic-secret-key" not in str(payload)


def test_ac008_cli_llm_smoke_reports_skipped_without_credentials(
    tmp_path, monkeypatch, capsys
):
    clear_provider_env(monkeypatch)

    exit_code = main(["--project-root", str(tmp_path), "llm", "smoke"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert SKIPPED_NO_CREDENTIALS in output
    assert "status: skipped" in output
    assert "api_key" not in output.lower()
