"""LLM provider abstraction and provider implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import json
import logging
import os
from copy import deepcopy
import re
from typing import Any, TypeVar
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from pydantic import BaseModel, ValidationError

from app.config import Settings

SchemaT = TypeVar("SchemaT", bound=BaseModel)
logger = logging.getLogger(__name__)


class LLMProviderError(RuntimeError):
    """Provider failure with a sanitized message."""


class LLMConfigurationError(LLMProviderError):
    """Provider configuration is missing or invalid."""


@dataclass(frozen=True)
class LLMProviderConfig:
    provider: str
    api_key: str
    model: str
    base_url: str
    timeout_seconds: float
    max_tokens: int
    extra_headers: dict[str, str] | None = None
    extra_payload: dict[str, Any] | None = None
    temperature: float | None = None


@dataclass(frozen=True)
class LLMTextResult:
    provider: str
    model: str | None
    text: str
    usage: dict[str, Any] = field(default_factory=dict)
    response_metadata: dict[str, Any] = field(default_factory=dict)


class JsonTransport(ABC):
    @abstractmethod
    def post_json(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        raise NotImplementedError


class UrllibJsonTransport(JsonTransport):
    def post_json(
        self,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        request = Request(url, data=data, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            raise LLMProviderError(f"LLM provider HTTP error status={exc.code}") from exc
        except URLError as exc:
            raise LLMProviderError(f"LLM provider network error: {exc.reason}") from exc
        try:
            loaded = json.loads(body)
        except json.JSONDecodeError as exc:
            raise LLMProviderError("LLM provider returned non-JSON response") from exc
        if not isinstance(loaded, dict):
            raise LLMProviderError("LLM provider returned a non-object JSON response")
        return loaded


class LLMClient(ABC):
    @abstractmethod
    def complete_text(self, system: str, user: str) -> str:
        raise NotImplementedError

    def complete_text_with_metadata(self, system: str, user: str) -> LLMTextResult:
        return LLMTextResult(
            provider=self.__class__.__name__,
            model=None,
            text=self.complete_text(system, user),
        )

    @abstractmethod
    def complete_json(self, system: str, user: str, schema: type[SchemaT]) -> SchemaT:
        raise NotImplementedError


class MockLLMClient(LLMClient):
    """Deterministic client for tests and offline CLI runs."""

    def __init__(
        self,
        text_response: str | None = None,
        json_response: dict[str, Any] | BaseModel | None = None,
    ) -> None:
        self.text_response = text_response
        self.json_response = json_response

    def complete_text(self, system: str, user: str) -> str:
        if self.text_response is not None:
            return self.text_response
        system_hint = system.splitlines()[0] if system.splitlines() else "context"
        return (
            "[mock-response] I used the current trace context before answering. "
            f"system_hint={system_hint!r}; user={user[:160]!r}"
        )

    def complete_text_with_metadata(self, system: str, user: str) -> LLMTextResult:
        return LLMTextResult(
            provider="mock",
            model=None,
            text=self.complete_text(system, user),
        )

    def complete_json(self, system: str, user: str, schema: type[SchemaT]) -> SchemaT:
        if isinstance(self.json_response, schema):
            return self.json_response
        if self.json_response is None:
            payload: dict[str, Any] = {}
        elif isinstance(self.json_response, BaseModel):
            payload = self.json_response.model_dump()
        else:
            payload = self.json_response
        try:
            return schema.model_validate(payload)
        except ValidationError:
            logger.exception("llm_json_validation_failed schema=%s", schema.__name__)
            raise


class StateSensitiveFakeLLMClient(LLMClient):
    """Deterministic fake that changes text when selected state changes."""

    def complete_text(self, system: str, user: str) -> str:
        lines = system.splitlines()
        concern_lines = [line for line in lines if line.startswith("- concern#")]
        memory_lines = [line for line in lines if line.startswith("- memory#")]
        policy_line = next((line for line in lines if line.startswith("Policy:")), "")
        parts = [
            "[state-sensitive-mock]",
            f"user={user[:80]!r}",
            f"selected_concerns={len(concern_lines)}",
            f"selected_memories={len(memory_lines)}",
        ]
        if concern_lines:
            first = concern_lines[0].split(":", 1)[-1].strip().lower()
            label = "lifecycle/digest trace" if any(
                word in first for word in ["lifecycle", "digest", "concern", "trace"]
            ) else first[:60]
            parts.append(f"Selected concern influence: unresolved {label}.")
        else:
            parts.append("Selected concern influence: none.")
        if memory_lines:
            parts.append("Selected memory influence: prior observation digest is active.")
        if "local_file" in policy_line:
            parts.append("Policy influence: traceability before expansion.")
        if "mention_internal_state" in policy_line:
            parts.append("Response policy influence: internal-state mention is bounded.")
        return " ".join(parts)

    def complete_text_with_metadata(self, system: str, user: str) -> LLMTextResult:
        return LLMTextResult(
            provider="state_sensitive_mock",
            model=None,
            text=self.complete_text(system, user),
        )

    def complete_json(self, system: str, user: str, schema: type[SchemaT]) -> SchemaT:
        return MockLLMClient(json_response={}).complete_json(system, user, schema)


class ManualLLMClient(LLMClient):
    """Provider stub that makes missing real LLM integration explicit."""

    def complete_text(self, system: str, user: str) -> str:
        return (
            "[manual-llm-stub] No external provider is configured. "
            "Use MockLLMClient or add a provider implementation."
        )

    def complete_text_with_metadata(self, system: str, user: str) -> LLMTextResult:
        return LLMTextResult(
            provider="manual",
            model=None,
            text=self.complete_text(system, user),
        )

    def complete_json(self, system: str, user: str, schema: type[SchemaT]) -> SchemaT:
        raise RuntimeError("ManualLLMClient cannot produce structured JSON.")


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
            elif isinstance(item, str):
                parts.append(item)
        return "".join(parts)
    return ""


def _extract_json(text: str) -> Any:
    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", stripped, flags=re.DOTALL)
    candidate = fenced.group(1).strip() if fenced else stripped
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        starts = [index for index in [candidate.find("{"), candidate.find("[")] if index >= 0]
        if not starts:
            raise
        start = min(starts)
        end = max(candidate.rfind("}"), candidate.rfind("]"))
        if end <= start:
            raise
        return json.loads(candidate[start : end + 1])


def _validate_json_text(text: str, schema: type[SchemaT]) -> SchemaT:
    try:
        payload = _extract_json(text)
        return schema.model_validate(payload)
    except (json.JSONDecodeError, ValidationError):
        logger.exception("llm_json_validation_failed schema=%s", schema.__name__)
        raise


def _json_instruction(schema: type[BaseModel]) -> str:
    return (
        "Return only a JSON value matching this JSON Schema. "
        "Do not include markdown fences or explanatory text.\n"
        f"{json.dumps(schema.model_json_schema(), ensure_ascii=False)}"
    )


def openrouter_json_schema_payload(
    schema: type[BaseModel],
    *,
    name: str,
    strict: bool = True,
    require_parameters: bool = True,
    structured_outputs: bool = True,
) -> dict[str, Any]:
    """Build OpenRouter structured-output payload without affecting other providers."""
    json_schema = _strict_json_schema(schema.model_json_schema())
    return {
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": name,
                "strict": strict,
                "schema": json_schema,
            },
        },
        "structured_outputs": structured_outputs,
        "provider": {"require_parameters": require_parameters},
    }


def _strict_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    strict_schema = deepcopy(schema)
    properties = strict_schema.get("properties")
    if isinstance(properties, dict):
        strict_schema["required"] = list(properties.keys())
    strict_schema["additionalProperties"] = False
    _remove_schema_defaults(strict_schema)
    return strict_schema


def _remove_schema_defaults(value: Any) -> None:
    if isinstance(value, dict):
        value.pop("default", None)
        for item in value.values():
            _remove_schema_defaults(item)
    elif isinstance(value, list):
        for item in value:
            _remove_schema_defaults(item)


def _usage_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


class OpenAICompatibleChatClient(LLMClient):
    """OpenAI Chat Completions compatible client for OpenAI and OpenRouter."""

    def __init__(
        self,
        config: LLMProviderConfig,
        transport: JsonTransport | None = None,
    ) -> None:
        self.config = config
        self.transport = transport or UrllibJsonTransport()

    def complete_text(self, system: str, user: str) -> str:
        return self.complete_text_with_metadata(system, user).text

    def complete_text_with_metadata(self, system: str, user: str) -> LLMTextResult:
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        if self.config.extra_headers:
            headers.update(self.config.extra_headers)
        token_parameter = (
            "max_tokens"
            if self.config.provider.strip().lower() == "openrouter"
            else "max_completion_tokens"
        )
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            token_parameter: self.config.max_tokens,
        }
        if self.config.temperature is not None:
            payload["temperature"] = self.config.temperature
        if self.config.extra_payload:
            payload.update(self.config.extra_payload)
        request_metadata = {
            "structured_output_enabled": bool(
                isinstance(payload.get("response_format"), dict)
                and payload["response_format"].get("type") == "json_schema"
            ),
            "structured_outputs": bool(payload.get("structured_outputs") is True),
            "provider_require_parameters": bool(
                isinstance(payload.get("provider"), dict)
                and payload["provider"].get("require_parameters") is True
            ),
            "token_parameter": token_parameter,
        }
        response = self.transport.post_json(
            url, headers, payload, self.config.timeout_seconds
        )
        try:
            choice = response["choices"][0]
            message = choice["message"]
            text = _content_to_text(message["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError(
                f"{self.config.provider} returned an unexpected chat response shape"
            ) from exc
        response_model = response.get("model")
        metadata: dict[str, Any] = {}
        if isinstance(choice, dict) and isinstance(choice.get("finish_reason"), str):
            metadata["finish_reason"] = choice["finish_reason"]
        if isinstance(message, dict):
            metadata["message_keys"] = sorted(str(key) for key in message)
            metadata["reasoning_present"] = "reasoning" in message
            metadata["reasoning_details_present"] = "reasoning_details" in message
            metadata["reasoning_content_present"] = "reasoning_content" in message
        metadata.update(request_metadata)
        return LLMTextResult(
            provider=self.config.provider,
            model=response_model if isinstance(response_model, str) else self.config.model,
            text=text,
            usage=_usage_dict(response.get("usage")),
            response_metadata=metadata,
        )

    def complete_json(self, system: str, user: str, schema: type[SchemaT]) -> SchemaT:
        text = self.complete_text(f"{system}\n\n{_json_instruction(schema)}", user)
        return _validate_json_text(text, schema)


class ClaudeMessagesClient(LLMClient):
    def __init__(
        self,
        config: LLMProviderConfig,
        transport: JsonTransport | None = None,
        anthropic_version: str = "2023-06-01",
    ) -> None:
        self.config = config
        self.transport = transport or UrllibJsonTransport()
        self.anthropic_version = anthropic_version

    def complete_text(self, system: str, user: str) -> str:
        return self.complete_text_with_metadata(system, user).text

    def complete_text_with_metadata(self, system: str, user: str) -> LLMTextResult:
        url = f"{self.config.base_url.rstrip('/')}/messages"
        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": self.anthropic_version,
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model,
            "system": system,
            "max_tokens": self.config.max_tokens,
            "messages": [{"role": "user", "content": user}],
        }
        if self.config.temperature is not None:
            payload["temperature"] = self.config.temperature
        response = self.transport.post_json(
            url, headers, payload, self.config.timeout_seconds
        )
        try:
            text = _content_to_text(response["content"])
        except (KeyError, TypeError) as exc:
            raise LLMProviderError("claude returned an unexpected response shape") from exc
        response_model = response.get("model")
        metadata: dict[str, Any] = {}
        if isinstance(response.get("stop_reason"), str):
            metadata["stop_reason"] = response["stop_reason"]
        return LLMTextResult(
            provider=self.config.provider,
            model=response_model if isinstance(response_model, str) else self.config.model,
            text=text,
            usage=_usage_dict(response.get("usage")),
            response_metadata=metadata,
        )

    def complete_json(self, system: str, user: str, schema: type[SchemaT]) -> SchemaT:
        text = self.complete_text(f"{system}\n\n{_json_instruction(schema)}", user)
        return _validate_json_text(text, schema)


class GeminiGenerateContentClient(LLMClient):
    def __init__(
        self,
        config: LLMProviderConfig,
        transport: JsonTransport | None = None,
    ) -> None:
        self.config = config
        self.transport = transport or UrllibJsonTransport()

    def complete_text(self, system: str, user: str) -> str:
        return self.complete_text_with_metadata(system, user).text

    def complete_text_with_metadata(self, system: str, user: str) -> LLMTextResult:
        model = quote(self.config.model, safe="")
        url = f"{self.config.base_url.rstrip('/')}/models/{model}:generateContent"
        headers = {
            "x-goog-api-key": self.config.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{system}\n\n{user}"}],
                }
            ],
            "generationConfig": {"maxOutputTokens": self.config.max_tokens},
        }
        if self.config.temperature is not None:
            payload["generationConfig"]["temperature"] = self.config.temperature
        response = self.transport.post_json(
            url, headers, payload, self.config.timeout_seconds
        )
        try:
            candidate = response["candidates"][0]
            text = _content_to_text(candidate["content"]["parts"])
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError("gemini returned an unexpected response shape") from exc
        metadata: dict[str, Any] = {}
        if isinstance(candidate, dict) and isinstance(candidate.get("finishReason"), str):
            metadata["finish_reason"] = candidate["finishReason"]
        return LLMTextResult(
            provider=self.config.provider,
            model=self.config.model,
            text=text,
            usage=_usage_dict(response.get("usageMetadata")),
            response_metadata=metadata,
        )

    def complete_json(self, system: str, user: str, schema: type[SchemaT]) -> SchemaT:
        text = self.complete_text(f"{system}\n\n{_json_instruction(schema)}", user)
        return _validate_json_text(text, schema)


def _env_first(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def _provider_key(provider: str) -> str | None:
    if provider == "openai":
        return _env_first("OPENAI_API_KEY")
    if provider == "claude":
        return _env_first("ANTHROPIC_API_KEY", "CLAUDE_API_KEY")
    if provider == "gemini":
        return _env_first("GEMINI_API_KEY", "GOOGLE_API_KEY")
    if provider == "openrouter":
        return _env_first("OPENROUTER_API_KEY")
    return None


def _provider_model(settings: Settings, provider: str) -> str | None:
    aliases = {
        "claude": ("ANTHROPIC_MODEL", "CLAUDE_MODEL"),
        "gemini": ("GEMINI_MODEL", "GOOGLE_MODEL"),
    }
    provider_upper = provider.upper()
    return settings.llm_model or _env_first(
        f"{provider_upper}_MODEL",
        *aliases.get(provider, ()),
    )


def _require_provider_config(
    settings: Settings,
    provider: str,
    temperature: float | None = None,
    extra_payload: dict[str, Any] | None = None,
) -> LLMProviderConfig:
    api_key = _provider_key(provider)
    model = _provider_model(settings, provider)
    if not api_key:
        raise LLMConfigurationError(
            f"LLM provider '{provider}' requires an API key environment variable."
        )
    if not model:
        raise LLMConfigurationError(
            f"LLM provider '{provider}' requires AGENT_LLM_MODEL or a provider-specific model environment variable."
        )
    base_urls = {
        "openai": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "claude": os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1"),
        "gemini": os.environ.get(
            "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
        ),
        "openrouter": os.environ.get(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        ),
    }
    extra_headers: dict[str, str] = {}
    if provider == "openrouter":
        referer = os.environ.get("OPENROUTER_HTTP_REFERER")
        title = os.environ.get("OPENROUTER_X_TITLE")
        if referer:
            extra_headers["HTTP-Referer"] = referer
        if title:
            extra_headers["X-Title"] = title
    return LLMProviderConfig(
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=base_urls[provider],
        timeout_seconds=settings.llm_timeout_seconds,
        max_tokens=settings.llm_max_tokens,
        extra_headers=extra_headers,
        extra_payload=extra_payload,
        temperature=temperature,
    )


def create_llm_client(
    settings: Settings,
    transport: JsonTransport | None = None,
    temperature: float | None = None,
    extra_payload: dict[str, Any] | None = None,
) -> LLMClient:
    provider = settings.llm_provider.strip().lower()
    if provider in ("", "mock"):
        return MockLLMClient()
    if provider in {"state_sensitive_mock", "state-sensitive-mock", "state_aware_mock"}:
        return StateSensitiveFakeLLMClient()
    if provider == "manual":
        return ManualLLMClient()
    if provider == "openai":
        return OpenAICompatibleChatClient(
            _require_provider_config(settings, "openai", temperature, extra_payload),
            transport,
        )
    if provider == "openrouter":
        return OpenAICompatibleChatClient(
            _require_provider_config(settings, "openrouter", temperature, extra_payload),
            transport,
        )
    if provider in ("claude", "anthropic"):
        return ClaudeMessagesClient(
            _require_provider_config(settings, "claude", temperature), transport
        )
    if provider in ("gemini", "google"):
        return GeminiGenerateContentClient(
            _require_provider_config(settings, "gemini", temperature), transport
        )
    raise LLMConfigurationError(
        "AGENT_LLM_PROVIDER must be one of: mock, state_sensitive_mock, manual, openai, claude, gemini, openrouter."
    )
