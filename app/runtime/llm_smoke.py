"""Minimal LLM provider smoke path."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
import os
from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session

from app.adapters.clock import now_utc
from app.adapters.llm import (
    JsonTransport,
    LLMConfigurationError,
    LLMProviderError,
    MockLLMClient,
    create_llm_client,
)
from app.config import Settings
from app.db.json_utils import json_dumps
from app.db.models import Action, Outcome

SMOKE_MARKER = "provider-smoke-ok"
SMOKE_COMMAND_PATH = "python -m app.main llm smoke"
SMOKE_SYSTEM_PROMPT = (
    "You are verifying a provider connectivity smoke test. "
    f"Reply with exactly: {SMOKE_MARKER}"
)
SMOKE_USER_PROMPT = f"Reply with exactly: {SMOKE_MARKER}"
SKIPPED_NO_CREDENTIALS = "SKIPPED: no real provider credentials configured"

REAL_PROVIDER_KEY_ENV_NAMES = {
    "openai": ("OPENAI_API_KEY",),
    "claude": ("ANTHROPIC_API_KEY", "CLAUDE_API_KEY"),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
    "openrouter": ("OPENROUTER_API_KEY",),
}
REAL_PROVIDER_MODEL_ENV_NAMES = {
    "openai": ("OPENAI_MODEL",),
    "claude": ("ANTHROPIC_MODEL", "CLAUDE_MODEL"),
    "gemini": ("GEMINI_MODEL", "GOOGLE_MODEL"),
    "openrouter": ("OPENROUTER_MODEL",),
}
REAL_PROVIDERS = tuple(REAL_PROVIDER_KEY_ENV_NAMES)
OFFLINE_SMOKE_PROVIDERS = {"mock", "state_sensitive_mock"}
ALL_SECRET_ENV_NAMES = tuple(
    name for names in REAL_PROVIDER_KEY_ENV_NAMES.values() for name in names
)


@dataclass(frozen=True)
class LLMSmokeResult:
    status: str
    exit_code: int
    message: str
    provider: str | None
    model: str | None
    marker_present: bool
    latency_ms: int | None
    usage: dict[str, Any]
    response_metadata: dict[str, Any]
    action_id: int
    outcome_id: int
    selected_from_credentials: bool = False
    error_class: str | None = None
    error_message: str | None = None

    def cli_lines(self) -> list[str]:
        return [
            self.message,
            f"provider: {self.provider or '(none)'}",
            f"model: {self.model or '(none)'}",
            f"status: {self.status}",
            f"marker_present: {str(self.marker_present).lower()}",
            f"latency_ms: {self.latency_ms if self.latency_ms is not None else 'n/a'}",
            f"usage: {json_dumps(self.usage)}",
            f"action_id: {self.action_id}",
            f"outcome_id: {self.outcome_id}",
        ]


@dataclass(frozen=True)
class _ProviderSelection:
    provider: str | None
    selected_from_credentials: bool = False
    skip_reason: str | None = None


def _normalize_provider(provider: str) -> str:
    normalized = provider.strip().lower().replace("-", "_")
    aliases = {
        "anthropic": "claude",
        "google": "gemini",
        "state_aware_mock": "state_sensitive_mock",
    }
    return aliases.get(normalized, normalized)


def _env_first(environ: Mapping[str, str], names: tuple[str, ...]) -> str | None:
    for name in names:
        value = environ.get(name)
        if value:
            return value
    return None


def _providers_with_credentials(environ: Mapping[str, str]) -> list[str]:
    return [
        provider
        for provider in REAL_PROVIDERS
        if _env_first(environ, REAL_PROVIDER_KEY_ENV_NAMES[provider])
    ]


def _configured_model(
    settings: Settings,
    environ: Mapping[str, str],
    provider: str | None,
) -> str | None:
    if settings.llm_model:
        return settings.llm_model
    if provider in REAL_PROVIDER_MODEL_ENV_NAMES:
        return _env_first(environ, REAL_PROVIDER_MODEL_ENV_NAMES[provider])
    return None


def _select_smoke_provider(
    settings: Settings,
    environ: Mapping[str, str],
) -> _ProviderSelection:
    raw_explicit = environ.get("AGENT_LLM_PROVIDER", "")
    explicit = raw_explicit.strip() != ""
    if explicit:
        provider = _normalize_provider(raw_explicit)
        if provider in REAL_PROVIDERS or provider in OFFLINE_SMOKE_PROVIDERS:
            return _ProviderSelection(provider=provider)
        if provider == "manual":
            return _ProviderSelection(
                provider=provider,
                skip_reason="SKIPPED: manual provider cannot perform an automated smoke",
            )
        raise LLMConfigurationError(
            "AGENT_LLM_PROVIDER must be one of: mock, state_sensitive_mock, openai, claude, gemini, openrouter."
        )

    configured = _providers_with_credentials(environ)
    if not configured:
        return _ProviderSelection(provider=None, skip_reason=SKIPPED_NO_CREDENTIALS)
    if len(configured) > 1:
        providers = ", ".join(configured)
        raise LLMConfigurationError(
            "Multiple real provider credentials detected "
            f"({providers}); set AGENT_LLM_PROVIDER explicitly."
        )
    return _ProviderSelection(provider=configured[0], selected_from_credentials=True)


def _safe_json_value(value: Any, depth: int = 0) -> Any:
    if depth > 3:
        return "[truncated]"
    if isinstance(value, str):
        return value if len(value) <= 240 else f"{value[:237]}..."
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, dict):
        return {
            str(key)[:80]: _safe_json_value(item, depth + 1)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_safe_json_value(item, depth + 1) for item in value[:20]]
    return str(value)[:240]


def _safe_json_dict(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not value:
        return {}
    return _safe_json_value(dict(value))


def _sanitize_error_message(message: str, environ: Mapping[str, str]) -> str:
    sanitized = message
    for name in ALL_SECRET_ENV_NAMES:
        value = environ.get(name)
        if value:
            sanitized = sanitized.replace(value, "[redacted]")
    return sanitized if len(sanitized) <= 500 else f"{sanitized[:497]}..."


def _smoke_settings(settings: Settings, provider: str) -> Settings:
    return replace(
        settings,
        llm_provider=provider,
        llm_timeout_seconds=max(1.0, min(settings.llm_timeout_seconds, 15.0)),
        llm_max_tokens=max(1, min(settings.llm_max_tokens, 16)),
    )


def _provider_smoke_extra_payload(provider: str) -> dict[str, Any] | None:
    if provider == "openrouter":
        return {"reasoning": {"effort": "none", "exclude": True}}
    return None


def _persist_smoke_trace(
    session: Session,
    *,
    status: str,
    provider: str | None,
    model: str | None,
    selected_from_credentials: bool,
    marker_present: bool,
    latency_ms: int | None,
    usage: dict[str, Any],
    response_metadata: dict[str, Any],
    error_class: str | None = None,
    error_message: str | None = None,
) -> tuple[int, int]:
    payload = {
        "command_path": SMOKE_COMMAND_PATH,
        "provider": provider,
        "model": model,
        "status": status,
        "selected_from_credentials": selected_from_credentials,
        "response_marker_present": marker_present,
        "latency_ms": latency_ms,
        "usage": usage,
        "response_metadata": response_metadata,
        "error_class": error_class,
        "error_message": error_message,
        "created_at": now_utc().isoformat(),
    }
    action = Action(
        action_type="llm_provider_smoke",
        rationale="Verify one bounded LLM provider call without mutating cognition state.",
        related_concern_ids_json=json_dumps([]),
        input_probe_ids_json=json_dumps([]),
        payload_json=json_dumps(payload),
        external_effect="llm_provider" if provider in REAL_PROVIDERS else "internal",
        status="completed" if status in {"success", "skipped"} else "failed",
    )
    session.add(action)
    session.flush()
    outcome = Outcome(
        action_id=action.id,
        observed_result=f"LLM provider smoke {status}.",
        effect_on_concerns_json=json_dumps({}),
        effect_on_attention_policy_json=json_dumps(
            {
                "direct_effect": "none",
                "provider": provider,
                "status": status,
            }
        ),
    )
    session.add(outcome)
    session.flush()
    return action.id, outcome.id


def _result_with_trace(
    session: Session,
    *,
    status: str,
    exit_code: int,
    message: str,
    provider: str | None,
    model: str | None,
    selected_from_credentials: bool,
    marker_present: bool = False,
    latency_ms: int | None = None,
    usage: dict[str, Any] | None = None,
    response_metadata: dict[str, Any] | None = None,
    error_class: str | None = None,
    error_message: str | None = None,
) -> LLMSmokeResult:
    usage_payload = _safe_json_dict(usage)
    metadata_payload = _safe_json_dict(response_metadata)
    action_id, outcome_id = _persist_smoke_trace(
        session,
        status=status,
        provider=provider,
        model=model,
        selected_from_credentials=selected_from_credentials,
        marker_present=marker_present,
        latency_ms=latency_ms,
        usage=usage_payload,
        response_metadata=metadata_payload,
        error_class=error_class,
        error_message=error_message,
    )
    return LLMSmokeResult(
        status=status,
        exit_code=exit_code,
        message=message,
        provider=provider,
        model=model,
        marker_present=marker_present,
        latency_ms=latency_ms,
        usage=usage_payload,
        response_metadata=metadata_payload,
        action_id=action_id,
        outcome_id=outcome_id,
        selected_from_credentials=selected_from_credentials,
        error_class=error_class,
        error_message=error_message,
    )


def run_llm_provider_smoke(
    session: Session,
    settings: Settings,
    *,
    transport: JsonTransport | None = None,
    environ: Mapping[str, str] | None = None,
) -> LLMSmokeResult:
    env = environ if environ is not None else os.environ
    try:
        selection = _select_smoke_provider(settings, env)
    except LLMConfigurationError as exc:
        message = _sanitize_error_message(str(exc), env)
        return _result_with_trace(
            session,
            status="failed",
            exit_code=1,
            message=f"FAILED: {message}",
            provider=None,
            model=None,
            selected_from_credentials=False,
            error_class=exc.__class__.__name__,
            error_message=message,
        )

    provider = selection.provider
    model = _configured_model(settings, env, provider)
    if selection.skip_reason:
        return _result_with_trace(
            session,
            status="skipped",
            exit_code=0,
            message=selection.skip_reason,
            provider=provider,
            model=model,
            selected_from_credentials=selection.selected_from_credentials,
        )

    assert provider is not None
    started = perf_counter()
    try:
        if provider in OFFLINE_SMOKE_PROVIDERS:
            client = MockLLMClient(text_response=SMOKE_MARKER)
        else:
            client = create_llm_client(
                _smoke_settings(settings, provider),
                transport=transport,
                temperature=0.0,
                extra_payload=_provider_smoke_extra_payload(provider),
            )
        response = client.complete_text_with_metadata(
            SMOKE_SYSTEM_PROMPT,
            SMOKE_USER_PROMPT,
        )
    except (LLMConfigurationError, LLMProviderError) as exc:
        latency_ms = int((perf_counter() - started) * 1000)
        message = _sanitize_error_message(str(exc), env)
        return _result_with_trace(
            session,
            status="failed",
            exit_code=1,
            message=f"FAILED: {message}",
            provider=provider,
            model=model,
            selected_from_credentials=selection.selected_from_credentials,
            latency_ms=latency_ms,
            error_class=exc.__class__.__name__,
            error_message=message,
        )

    latency_ms = int((perf_counter() - started) * 1000)
    marker_present = SMOKE_MARKER in response.text.strip()
    result_model = response.model or model
    if not marker_present:
        message = f"provider response did not contain marker {SMOKE_MARKER}"
        return _result_with_trace(
            session,
            status="failed",
            exit_code=1,
            message=f"FAILED: {message}",
            provider=provider,
            model=result_model,
            selected_from_credentials=selection.selected_from_credentials,
            marker_present=False,
            latency_ms=latency_ms,
            usage=response.usage,
            response_metadata=response.response_metadata,
            error_class="LLMSmokeMarkerError",
            error_message=message,
        )

    return _result_with_trace(
        session,
        status="success",
        exit_code=0,
        message=f"OK: {SMOKE_MARKER}",
        provider=provider,
        model=result_model,
        selected_from_credentials=selection.selected_from_credentials,
        marker_present=True,
        latency_ms=latency_ms,
        usage=response.usage,
        response_metadata=response.response_metadata,
    )
