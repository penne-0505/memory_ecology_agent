from __future__ import annotations

import json
from urllib.error import HTTPError
from io import BytesIO

from _evals.scripts import openrouter_structured_output_probe as probe


def test_probe_modes_cover_requested_matrix_and_strict_variants():
    modes = probe.probe_modes(include_strict_false=True)
    ids = [mode.id for mode in modes]

    assert ids == [
        "A",
        "A-strict-false",
        "B",
        "B-strict-false",
        "C",
        "C-strict-false",
        "D",
        "E",
        "F",
        "F-strict-false",
    ]
    assert modes[0].provider_require_parameters is True
    assert modes[4].provider_require_parameters is False
    assert modes[8].provider_require_parameters is None


def test_build_payload_shapes_are_openrouter_dialects():
    modes = {mode.id: mode for mode in probe.probe_modes(include_strict_false=False)}

    a_payload = probe._build_extra_payload(
        modes["A"],
        probe.MINIMAL_SCHEMA,
        schema_name="minimal",
    )
    assert a_payload["response_format"]["type"] == "json_schema"
    assert a_payload["response_format"]["json_schema"]["name"] == "minimal"
    assert a_payload["response_format"]["json_schema"]["strict"] is True
    assert a_payload["provider"] == {"require_parameters": True}
    assert "structured_outputs" not in a_payload

    c_payload = probe._build_extra_payload(
        modes["C"],
        probe.MINIMAL_SCHEMA,
        schema_name="minimal",
    )
    assert c_payload["structured_outputs"] is True
    assert c_payload["provider"] == {"require_parameters": False}

    d_payload = probe._build_extra_payload(
        modes["D"],
        probe.MINIMAL_SCHEMA,
        schema_name="minimal",
    )
    assert d_payload == {
        "response_format": {"type": "json_object"},
        "provider": {"require_parameters": True},
    }

    f_payload = probe._build_extra_payload(
        modes["F"],
        probe.MINIMAL_SCHEMA,
        schema_name="minimal",
    )
    assert "provider" not in f_payload


def test_probe_artifact_does_not_include_raw_model_content(tmp_path, monkeypatch):
    mode = probe.ProbeMode(
        "A",
        "json_schema",
        "json_schema",
        True,
        None,
        True,
    )

    def fake_post_chat_completion(**kwargs):
        return {
            "model": "qwen/qwen3.6-plus",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": '{"answer":"secret-provider-output"}'},
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
        }

    monkeypatch.setattr(probe, "_post_chat_completion", fake_post_chat_completion)

    result = probe.run_probe_call(
        mode=mode,
        schema=probe.MINIMAL_SCHEMA,
        schema_name="minimal",
        api_key="sk-test-secret",
        model="qwen/qwen3.6-plus",
        timeout_seconds=1,
        max_completion_tokens=8,
    )
    payload = {
        "model": "qwen/qwen3.6-plus",
        "raw_response_persisted": False,
        "recommendation": "FULL_RUN_CANDIDATE_MODE_A",
        "results": [result],
    }
    output_json = tmp_path / "probe.json"
    output_md = tmp_path / "probe.md"
    probe.write_artifacts(output_json, output_md, payload)

    serialized = output_json.read_text(encoding="utf-8") + output_md.read_text(
        encoding="utf-8"
    )
    assert result["content_parse_status"] == "valid_json_object"
    assert result["parsed_keys"] == ["answer"]
    assert result["missing_keys"] == []
    assert "secret-provider-output" not in serialized
    assert "sk-test-secret" not in serialized
    assert "raw_response_persisted" in serialized


def test_http_error_is_sanitized_without_raw_body(monkeypatch):
    mode = probe.probe_modes(include_strict_false=False)[0]

    def fake_post_chat_completion(**kwargs):
        raise HTTPError(
            url="https://openrouter.ai/api/v1/chat/completions",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=BytesIO(
                json.dumps(
                    {
                        "error": {
                            "code": 404,
                            "message": "No endpoints found for sk-test-secret",
                        }
                    }
                ).encode("utf-8")
            ),
        )

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-secret")
    monkeypatch.setattr(probe, "_post_chat_completion", fake_post_chat_completion)

    result = probe.run_probe_call(
        mode=mode,
        schema=probe.MINIMAL_SCHEMA,
        schema_name="minimal",
        api_key="sk-test-secret",
        model="qwen/qwen3.6-plus",
        timeout_seconds=1,
        max_completion_tokens=8,
    )

    assert result["status"] == "provider_error"
    assert result["http_status"] == 404
    assert "sk-test-secret" not in result["error_message_sanitized"]
    assert "[REDACTED]" in result["error_message_sanitized"]


def test_content_parse_summary_records_keys_without_values():
    response = {
        "choices": [
            {"message": {"content": '{"decision":"discard","reason":"private"}'}}
        ]
    }

    summary = probe._content_parse_summary(
        response,
        {"decision", "reason", "confidence"},
    )

    assert summary == {
        "status": "missing_expected_keys",
        "parsed_keys": ["decision", "reason"],
        "missing_keys": ["confidence"],
    }
    assert "private" not in json.dumps(summary)
