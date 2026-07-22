"""Probe OpenRouter structured-output payload dialects with sanitized artifacts.

This script does not use the app DB or digest persistence. It sends tiny
one-prompt requests and records only sanitized status metadata. Raw model
response text is never written to artifacts.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from app.cognition.digest_decider import LLMDigestProposal  # noqa: E402


DEFAULT_MODEL = "qwen/qwen3.6-plus"
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "_evals"
    / "reports"
    / f"openrouter_structured_output_probe_{datetime.now(UTC).date().isoformat()}.json"
)
DEFAULT_OUTPUT_MD = DEFAULT_OUTPUT_JSON.with_suffix(".md")
OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"
DOC_URLS = [
    "https://openrouter.ai/docs/features/structured-outputs",
    "https://openrouter.ai/docs/api/reference/parameters",
    "https://openrouter.ai/docs/features/provider-routing",
    "https://openrouter.ai/docs/models",
    "https://openrouter.ai/api/v1/models",
]
MINIMAL_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
    },
    "required": ["answer"],
    "additionalProperties": False,
}
TINY_MESSAGES = [
    {
        "role": "system",
        "content": "Return exactly one JSON object. No markdown.",
    },
    {
        "role": "user",
        "content": 'Set answer to "ok".',
    },
]
DIGEST_MESSAGES = [
    {
        "role": "system",
        "content": "Return exactly one JSON object matching the requested schema. No markdown.",
    },
    {
        "role": "user",
        "content": (
            "Produce a safe digest proposal for a low-signal note. Use decision discard, "
            "confidence 0.95, empty related_concern_ids, empty risk_flags, and should_apply false."
        ),
    },
]
SECRET_KEYS = [
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
]


@dataclass(frozen=True)
class ProbeMode:
    id: str
    description: str
    response_format_type: str
    include_schema: bool
    structured_outputs: bool | None
    provider_require_parameters: bool | None
    strict: bool | None = True


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _redact(value: str) -> str:
    redacted = value
    for key in SECRET_KEYS:
        secret = os.environ.get(key)
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    return redacted.replace("Bearer ", "Bearer [REDACTED] ")[:500]


def _schema_response_format(
    schema: dict[str, Any],
    *,
    name: str,
    strict: bool | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": "json_schema",
        "json_schema": {
            "name": name,
            "schema": schema,
        },
    }
    if strict is not None:
        payload["json_schema"]["strict"] = strict
    return payload


def _build_extra_payload(
    mode: ProbeMode,
    schema: dict[str, Any],
    *,
    schema_name: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if mode.response_format_type == "json_schema":
        payload["response_format"] = _schema_response_format(
            schema,
            name=schema_name,
            strict=mode.strict,
        )
    elif mode.response_format_type == "json_object":
        payload["response_format"] = {"type": "json_object"}
    else:
        raise ValueError(f"Unsupported response_format_type={mode.response_format_type}")
    if mode.structured_outputs is not None:
        payload["structured_outputs"] = mode.structured_outputs
    if mode.provider_require_parameters is not None:
        payload["provider"] = {
            "require_parameters": mode.provider_require_parameters,
        }
    return payload


def probe_modes(*, include_strict_false: bool) -> list[ProbeMode]:
    base = [
        ProbeMode(
            "A",
            "json_schema + provider.require_parameters=true",
            "json_schema",
            True,
            None,
            True,
        ),
        ProbeMode(
            "B",
            "json_schema + structured_outputs=true + provider.require_parameters=true",
            "json_schema",
            True,
            True,
            True,
        ),
        ProbeMode(
            "C",
            "json_schema + structured_outputs=true + provider.require_parameters=false",
            "json_schema",
            True,
            True,
            False,
        ),
        ProbeMode(
            "D",
            "json_object + provider.require_parameters=true",
            "json_object",
            False,
            None,
            True,
            strict=None,
        ),
        ProbeMode(
            "E",
            "json_object + structured_outputs=true + provider.require_parameters=true",
            "json_object",
            False,
            True,
            True,
            strict=None,
        ),
        ProbeMode(
            "F",
            "json_schema response_format only; no provider object",
            "json_schema",
            True,
            None,
            None,
        ),
    ]
    if not include_strict_false:
        return base
    expanded: list[ProbeMode] = []
    for mode in base:
        expanded.append(mode)
        if mode.response_format_type == "json_schema":
            expanded.append(
                ProbeMode(
                    f"{mode.id}-strict-false",
                    f"{mode.description}; strict=false",
                    mode.response_format_type,
                    mode.include_schema,
                    mode.structured_outputs,
                    mode.provider_require_parameters,
                    strict=False,
                )
            )
    return expanded


def _post_chat_completion(
    *,
    api_key: str,
    model: str,
    payload_extra: dict[str, Any],
    messages: list[dict[str, str]],
    max_completion_tokens: int,
    token_parameter: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0,
    }
    payload[token_parameter] = max_completion_tokens
    payload.update(payload_extra)
    request = Request(
        OPENROUTER_CHAT_COMPLETIONS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8")
    loaded = json.loads(body)
    if not isinstance(loaded, dict):
        raise RuntimeError("non_object_provider_response")
    return loaded


def _provider_model(response: dict[str, Any]) -> str:
    value = response.get("model")
    return value if isinstance(value, str) else ""


def _finish_reason(response: dict[str, Any]) -> str:
    try:
        value = response["choices"][0]["finish_reason"]
    except (KeyError, IndexError, TypeError):
        return ""
    return value if isinstance(value, str) else ""


def _content_parse_status(response: dict[str, Any], expected_keys: set[str]) -> str:
    return _content_parse_summary(response, expected_keys)["status"]


def _content_parse_summary(
    response: dict[str, Any],
    expected_keys: set[str],
) -> dict[str, Any]:
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return {"status": "missing_content", "parsed_keys": [], "missing_keys": sorted(expected_keys)}
    if not isinstance(content, str):
        return {"status": "non_string_content", "parsed_keys": [], "missing_keys": sorted(expected_keys)}
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {"status": "content_not_json", "parsed_keys": [], "missing_keys": sorted(expected_keys)}
    if not isinstance(parsed, dict):
        return {"status": "content_not_object", "parsed_keys": [], "missing_keys": sorted(expected_keys)}
    parsed_keys = sorted(str(key) for key in parsed)
    missing_keys = sorted(expected_keys - set(parsed))
    if missing_keys:
        return {
            "status": "missing_expected_keys",
            "parsed_keys": parsed_keys,
            "missing_keys": missing_keys,
        }
    return {
        "status": "valid_json_object",
        "parsed_keys": parsed_keys,
        "missing_keys": [],
    }


def _usage_summary(response: dict[str, Any]) -> dict[str, Any]:
    usage = response.get("usage")
    if not isinstance(usage, dict):
        return {}
    safe_keys = {
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "reasoning_tokens",
    }
    return {key: usage[key] for key in safe_keys if key in usage}


def run_probe_call(
    *,
    mode: ProbeMode,
    schema: dict[str, Any],
    schema_name: str,
    api_key: str,
    model: str,
    timeout_seconds: float,
    max_completion_tokens: int,
    token_parameter: str = "max_tokens",
    messages: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    extra_payload = _build_extra_payload(mode, schema, schema_name=schema_name)
    result: dict[str, Any] = {
        "mode": mode.id,
        "description": mode.description,
        "schema_name": schema_name,
        "response_format_type": mode.response_format_type,
        "structured_outputs": mode.structured_outputs,
        "provider_require_parameters": mode.provider_require_parameters,
        "strict": mode.strict,
        "status": "unknown",
        "http_status": None,
        "error_class": "",
        "error_message_sanitized": "",
        "provider_model": "",
        "finish_reason": "",
        "content_parse_status": "",
        "parsed_keys": [],
        "missing_keys": [],
        "usage": {},
        "elapsed_seconds": 0.0,
        "raw_response_persisted": False,
    }
    try:
        response = _post_chat_completion(
            api_key=api_key,
            model=model,
            payload_extra=extra_payload,
            messages=messages or TINY_MESSAGES,
            max_completion_tokens=max_completion_tokens,
            token_parameter=token_parameter,
            timeout_seconds=timeout_seconds,
        )
        parse_summary = _content_parse_summary(
            response,
            set(schema.get("properties", {}).keys()),
        )
        result.update(
            {
                "status": "success",
                "http_status": 200,
                "provider_model": _provider_model(response),
                "finish_reason": _finish_reason(response),
                "content_parse_status": parse_summary["status"],
                "parsed_keys": parse_summary["parsed_keys"],
                "missing_keys": parse_summary["missing_keys"],
                "usage": _usage_summary(response),
            }
        )
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        result.update(
            {
                "status": "provider_error",
                "http_status": exc.code,
                "error_class": "HTTPError",
                "error_message_sanitized": _redact(_summarize_error_body(body)),
            }
        )
    except (URLError, TimeoutError) as exc:
        result.update(
            {
                "status": "network_error",
                "error_class": exc.__class__.__name__,
                "error_message_sanitized": _redact(str(exc)),
            }
        )
    except Exception as exc:  # noqa: BLE001 - sanitized diagnostic artifact.
        result.update(
            {
                "status": "client_error",
                "error_class": exc.__class__.__name__,
                "error_message_sanitized": _redact(str(exc)),
            }
        )
    result["elapsed_seconds"] = round(time.monotonic() - started, 2)
    return result


def _summarize_error_body(body: str) -> str:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return "provider_returned_non_json_error"
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        message = str(error.get("message") or error.get("code") or "provider_error")
        code = error.get("code")
        return f"code={code} message={message}" if code is not None else message
    return "provider_error"


def _digest_schema() -> dict[str, Any]:
    schema = LLMDigestProposal.model_json_schema()
    properties = schema.get("properties", {})
    if isinstance(properties, dict):
        schema["required"] = list(properties.keys())
    schema["additionalProperties"] = False
    _remove_defaults(schema)
    return schema


def _remove_defaults(value: Any) -> None:
    if isinstance(value, dict):
        value.pop("default", None)
        for item in value.values():
            _remove_defaults(item)
    elif isinstance(value, list):
        for item in value:
            _remove_defaults(item)


def _select_digest_mode(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    successful = [
        result
        for result in results
        if result["status"] == "success"
        and result["content_parse_status"] == "valid_json_object"
    ]
    if not successful:
        return None
    enforced = [result for result in successful if result["provider_require_parameters"] is True]
    json_schema = [result for result in enforced if result["response_format_type"] == "json_schema"]
    if json_schema:
        return json_schema[0]
    if enforced:
        return enforced[0]
    return successful[0]


def _successful_minimal_modes(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        result
        for result in results
        if result["schema_name"] == "minimal"
        and result["status"] == "success"
        and result["content_parse_status"] == "valid_json_object"
    ]


def _payload() -> dict[str, Any]:
    return {}


def write_artifacts(output_json: Path, output_md: Path, payload: dict[str, Any]) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    output_md.write_text(_markdown(payload), encoding="utf-8")


def _markdown(payload: dict[str, Any]) -> str:
    lines = [
        "---",
        "title: OpenRouter Structured Output Probe",
        "status: active",
        "draft_status: n/a",
        f"created_at: {datetime.now(UTC).date().isoformat()}",
        f"updated_at: {datetime.now(UTC).date().isoformat()}",
        "references:",
        '  - "_docs/qa/Core/openrouter-structured-digest-proposals/verification.md"',
        "related_issues: []",
        "related_prs: []",
        "---",
        "",
        "# OpenRouter Structured Output Probe",
        "",
        "## Summary",
        "",
        f"- model: `{payload['model']}`",
        f"- raw_response_persisted: `{payload['raw_response_persisted']}`",
        f"- recommendation: `{payload['recommendation']}`",
        "",
        "## Matrix",
        "",
        "| Mode | Schema | Status | HTTP | Parse | Require Parameters | Structured Outputs | Strict | Error |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for result in payload["results"]:
        lines.append(
            "| "
            f"`{result['mode']}` | "
            f"`{result['schema_name']}` | "
            f"`{result['status']}` | "
            f"`{result['http_status']}` | "
            f"`{result['content_parse_status']}` | "
            f"`{result['provider_require_parameters']}` | "
            f"`{result['structured_outputs']}` | "
            f"`{result['strict']}` | "
            f"`{result['error_message_sanitized']}` |"
        )
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- Raw provider/model response text is not included.",
            "- Credential values are not printed.",
            "- DB and digest persistence are not used.",
            "",
        ]
    )
    return "\n".join(lines)


def run_probe(
    *,
    api_key: str,
    model: str,
    include_strict_false: bool,
    timeout_seconds: float,
    max_completion_tokens: int,
    token_parameter: str,
) -> dict[str, Any]:
    started_at = _now_iso()
    results = [
        run_probe_call(
            mode=mode,
            schema=MINIMAL_SCHEMA,
            schema_name="minimal",
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
            max_completion_tokens=max_completion_tokens,
            token_parameter=token_parameter,
        )
        for mode in probe_modes(include_strict_false=include_strict_false)
    ]
    selected = _select_digest_mode(results)
    mode_by_id = {
        mode.id: mode for mode in probe_modes(include_strict_false=include_strict_false)
    }
    for selected_result in _successful_minimal_modes(results):
        digest_mode = mode_by_id[selected_result["mode"]]
        results.append(
            run_probe_call(
                mode=digest_mode,
                schema=_digest_schema(),
                schema_name="llm_digest_proposal",
                api_key=api_key,
                model=model,
                timeout_seconds=timeout_seconds,
                max_completion_tokens=max(max_completion_tokens, 192),
                token_parameter=token_parameter,
                messages=DIGEST_MESSAGES,
            )
        )
    recommendation = _recommendation(results, selected)
    return {
        "runner": "openrouter_structured_output_probe",
        "started_at": started_at,
        "completed_at": _now_iso(),
        "model": model,
        "docs_checked": DOC_URLS,
        "raw_response_persisted": False,
        "prompt_shape": "tiny_single_prompt",
        "full_digest_runner_executed": False,
        "token_parameter": token_parameter,
        "recommendation": recommendation,
        "results": results,
    }


def _recommendation(
    results: list[dict[str, Any]],
    selected_minimal: dict[str, Any] | None,
) -> str:
    if selected_minimal is None:
        return "NO_FULL_RUN_PROVIDER_ERRORS_ONLY"
    digest = next(
        (result for result in results if result["schema_name"] == "llm_digest_proposal"),
        None,
    )
    if digest is None:
        return "NO_FULL_RUN_NO_DIGEST_PROBE"
    successful_digest = [
        result
        for result in results
        if result["schema_name"] == "llm_digest_proposal"
        and result["status"] == "success"
        and result["content_parse_status"] == "valid_json_object"
    ]
    if successful_digest:
        enforced = [
            result
            for result in successful_digest
            if result["provider_require_parameters"] is True
        ]
        if enforced:
            return f"FULL_RUN_CANDIDATE_MODE_{enforced[0]['mode']}"
        return f"NON_ENFORCING_DIAGNOSTIC_ONLY_MODE_{successful_digest[0]['mode']}"
    return f"NO_FULL_RUN_MINIMAL_ONLY_MODE_{selected_minimal['mode']}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--max-completion-tokens", type=int, default=64)
    parser.add_argument("--token-parameter", choices=["max_tokens", "max_completion_tokens"], default="max_tokens")
    parser.add_argument("--strict-variants", action="store_true")
    args = parser.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        payload = {
            "runner": "openrouter_structured_output_probe",
            "started_at": _now_iso(),
            "completed_at": _now_iso(),
            "model": args.model,
            "docs_checked": DOC_URLS,
            "raw_response_persisted": False,
            "prompt_shape": "tiny_single_prompt",
            "full_digest_runner_executed": False,
            "token_parameter": args.token_parameter,
            "recommendation": "SKIPPED_REAL_PROVIDER",
            "results": [
                {
                    "mode": "credential_gate",
                    "schema_name": "minimal",
                    "status": "skipped",
                    "error_class": "MissingCredential",
                    "error_message_sanitized": "OPENROUTER_API_KEY is not set",
                    "raw_response_persisted": False,
                }
            ],
        }
        write_artifacts(args.output_json, args.output_md, payload)
        print(args.output_json)
        print(args.output_md)
        return 0

    payload = run_probe(
        api_key=api_key,
        model=args.model,
        include_strict_false=args.strict_variants,
        timeout_seconds=args.timeout_seconds,
        max_completion_tokens=args.max_completion_tokens,
        token_parameter=args.token_parameter,
    )
    write_artifacts(args.output_json, args.output_md, payload)
    print(args.output_json)
    print(args.output_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
