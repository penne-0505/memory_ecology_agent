from __future__ import annotations

import json

from _evals.scripts.run_live_digest_model_comparison import (
    DigestDiagnosticWriter,
    ModelEvaluationResult,
    ObservationEvaluationResult,
    PRIMARY_MODEL,
    ResultWriter,
    _first_partial_elapsed_seconds,
    classify_failure_causes,
    merge_validation_failure_aggregates,
    run_models,
    validation_failure_aggregate_from_rows,
)


def _result(model: str, provider: str, phase: str, **overrides) -> ModelEvaluationResult:
    payload = {
        "model": model,
        "provider": provider,
        "phase": phase,
        "status": "completed",
        "metrics": {
            "schema_valid_proposals": 16,
            "rejected_or_fallback_proposals": 0,
            "raw_response_persisted_count": 0,
        },
        "failure_causes": {},
        "safety_checks": {
            "raw_response_not_persisted": True,
            "final_digest_decisions_exist": True,
            "web_search_disabled": True,
            "discord_disabled": True,
            "proposal_only_shadow": True,
            "wake_cycle_completed": True,
        },
        "structured_output_enabled": provider == "openrouter",
        "structured_outputs": provider == "openrouter",
        "provider_require_parameters": provider == "openrouter",
        "token_parameter": "max_tokens" if provider == "openrouter" else "max_completion_tokens",
        "reasoning_effort": "",
        "reasoning_exclude": None,
    }
    payload.update(overrides)
    return ModelEvaluationResult(**payload)


def test_classify_failure_causes_groups_schema_provider_and_safety():
    rows = [
        {"error_class": "JSONDecodeError"},
        {"error_class": "ValidationError"},
        {"error_class": "LLMProviderError"},
        {"error_class": "UnsafeOutput"},
        {"error_class": ""},
    ]

    causes = classify_failure_causes(
        rows,
        {"raw_response_persisted_count": 1},
        orchestration_error="TimeoutError",
        safety_checks={"raw_response_not_persisted": False},
    )

    assert causes["malformed_json"] == 1
    assert causes["schema_validation"] == 1
    assert causes["provider_error"] == 1
    assert causes["timeout"] == 1
    assert causes["safety_boundary"] == 3


def test_safe_batch_failure_skips_remaining_models():
    calls: list[tuple[str, str]] = []

    def evaluate(model: str, provider: str, phase: str) -> ModelEvaluationResult:
        calls.append((model, phase))
        if model == "bad-model":
            return _result(
                model,
                provider,
                phase,
                status="failed",
                failure_causes={"provider_error": 1},
            )
        return _result(model, provider, phase)

    results = run_models(
        models=["bad-model", "later-a", "later-b"],
        provider="openrouter",
        safe_batch_size=1,
        concurrency=3,
        fail_fast_on_safe_batch=True,
        evaluate=evaluate,
    )

    assert calls == [("bad-model", "safe_batch")]
    assert [result.status for result in results] == ["failed", "skipped", "skipped"]
    assert all(result.failure_causes == {"safe_batch_gate": 1} for result in results[1:])


def test_successful_safe_batch_runs_bounded_phase_after_safe_phase():
    completed_phases: list[str] = []

    def evaluate(model: str, provider: str, phase: str) -> ModelEvaluationResult:
        return _result(model, provider, phase)

    results = run_models(
        models=["safe-a", "safe-b", "bounded-a", "bounded-b"],
        provider="openrouter",
        safe_batch_size=2,
        concurrency=2,
        fail_fast_on_safe_batch=True,
        evaluate=evaluate,
        on_result=lambda result: completed_phases.append(result.phase),
    )

    assert len(results) == 4
    assert completed_phases[:2] == ["safe_batch", "safe_batch"]
    assert completed_phases[2:] == ["bounded", "bounded"]
    assert all(result.status == "completed" for result in results)


def test_run_models_passes_observation_concurrency_and_partial_callback():
    seen_observation_concurrency: list[int] = []
    seen_max_observations: list[int] = []
    partials: list[int] = []

    def evaluate(
        model: str,
        provider: str,
        phase: str,
        *,
        observation_concurrency: int,
        max_observations: int,
        on_partial,
    ) -> ModelEvaluationResult:
        seen_observation_concurrency.append(observation_concurrency)
        seen_max_observations.append(max_observations)
        on_partial(
            ObservationEvaluationResult(
                model=model,
                provider=provider,
                observation_id=42,
                status="completed",
                elapsed_seconds=0.2,
                schema_valid=True,
                completed_at="2026-06-03T00:00:00+00:00",
            )
        )
        partials.append(42)
        return _result(model, provider, phase)

    results = run_models(
        models=[PRIMARY_MODEL],
        provider="openrouter",
        safe_batch_size=1,
        concurrency=1,
        observation_concurrency=4,
        max_observations=3,
        fail_fast_on_safe_batch=True,
        evaluate=evaluate,
    )

    assert [result.model for result in results] == [PRIMARY_MODEL]
    assert seen_observation_concurrency == [4]
    assert seen_max_observations == [3]
    assert partials == [42]


def test_result_writer_flushes_after_each_model_without_raw_response(tmp_path):
    output_json = tmp_path / "comparison.json"
    output_md = tmp_path / "comparison.md"
    writer = ResultWriter(
        output_json=output_json,
        output_md=output_md,
        provider="openrouter",
        models=["model-a", "model-b"],
        safe_batch_size=1,
        concurrency=2,
        fail_fast_on_safe_batch=True,
    )

    writer.record(_result("model-a", "openrouter", "safe_batch"))
    first_payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert [result["model"] for result in first_payload["results"]] == ["model-a"]

    writer.record(_result("model-b", "openrouter", "bounded"))
    second_payload = json.loads(output_json.read_text(encoding="utf-8"))
    report = output_md.read_text(encoding="utf-8")

    assert [result["model"] for result in second_payload["results"]] == [
        "model-a",
        "model-b",
    ]
    assert second_payload["raw_provider_response_persisted"] is False
    assert second_payload["max_observations"] == 0
    assert second_payload["structured_output_enabled"] is True
    assert second_payload["structured_outputs"] is True
    assert second_payload["provider_require_parameters"] is True
    assert second_payload["token_parameter"] == "max_tokens"
    assert second_payload["reasoning_effort"] == ""
    assert second_payload["reasoning_exclude"] is None
    assert second_payload["results"][0]["structured_output_enabled"] is True
    assert second_payload["results"][0]["structured_outputs"] is True
    assert second_payload["results"][0]["token_parameter"] == "max_tokens"
    assert "secret-provider-output" not in json.dumps(second_payload, ensure_ascii=False)
    assert "Raw provider response text is not included." in report
    assert "structured_output_enabled" in report
    assert "token_parameter" in report
    assert "reasoning_effort" in report


def test_validation_failure_aggregate_uses_sanitized_field_type_counts():
    rows = [
        {
            "error_class": "ValidationError",
            "error_message_sanitized": json.dumps(
                {
                    "reason:missing": 1,
                    "alternative_decision:missing": 2,
                    "confidence:less_than_equal": 1,
                }
            ),
        },
        {
            "error_class": "ValidationError",
            "error_message_sanitized": json.dumps({"reason:missing": 3}),
        },
        {
            "error_class": "LLMProviderError",
            "error_message_sanitized": "LLMProviderError",
        },
    ]

    aggregate = validation_failure_aggregate_from_rows(rows)

    assert aggregate == [
        {"loc": "alternative_decision", "type": "missing", "count": 2},
        {"loc": "confidence", "type": "less_than_equal", "count": 1},
        {"loc": "reason", "type": "missing", "count": 4},
    ]
    assert "raw-model-value" not in json.dumps(aggregate)


def test_result_writer_records_validation_failure_aggregate_without_raw_text(tmp_path):
    output_json = tmp_path / "comparison.json"
    output_md = tmp_path / "comparison.md"
    writer = ResultWriter(
        output_json=output_json,
        output_md=output_md,
        provider="openrouter",
        models=[PRIMARY_MODEL],
        safe_batch_size=1,
        concurrency=1,
        fail_fast_on_safe_batch=True,
    )

    partial_aggregate = [{"loc": "reason", "type": "missing", "count": 1}]
    writer.record_partial(
        ObservationEvaluationResult(
            model=PRIMARY_MODEL,
            provider="openrouter",
            observation_id=3,
            status="failed",
            elapsed_seconds=0.3,
            fallback_used=True,
            error_class="ValidationError",
            failure_cause="schema_validation",
            validation_failure_aggregate=partial_aggregate,
        )
    )
    writer.record(
        _result(
            PRIMARY_MODEL,
            "openrouter",
            "safe_batch",
            validation_failure_aggregate=[
                {"loc": "reason", "type": "missing", "count": 4},
                {"loc": "alternative_decision", "type": "missing", "count": 2},
            ],
        )
    )

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    report = output_md.read_text(encoding="utf-8")

    assert payload["validation_failure_aggregate"] == [
        {"loc": "alternative_decision", "type": "missing", "count": 2},
        {"loc": "reason", "type": "missing", "count": 4},
    ]
    assert payload["observation_partials"][0]["validation_failure_aggregate"] == partial_aggregate
    assert payload["results"][0]["validation_failure_aggregate"][0]["loc"] == "reason"
    assert "raw-model-value" not in json.dumps(payload, ensure_ascii=False)
    assert "Validation Failure Aggregate" in report


def test_merge_validation_failure_aggregates_sums_matching_entries():
    merged = merge_validation_failure_aggregates(
        [
            [{"loc": "reason", "type": "missing", "count": 1}],
            [
                {"loc": "reason", "type": "missing", "count": 2},
                {"loc": "confidence", "type": "float_parsing", "count": 1},
            ],
        ]
    )

    assert merged == [
        {"loc": "confidence", "type": "float_parsing", "count": 1},
        {"loc": "reason", "type": "missing", "count": 3},
    ]


def test_result_writer_flushes_observation_partials_before_model_completion(tmp_path):
    output_json = tmp_path / "comparison.json"
    output_md = tmp_path / "comparison.md"
    writer = ResultWriter(
        output_json=output_json,
        output_md=output_md,
        provider="openrouter",
        models=[PRIMARY_MODEL],
        safe_batch_size=1,
        concurrency=1,
        observation_concurrency=4,
        fail_fast_on_safe_batch=True,
    )

    writer.record_partial(
        ObservationEvaluationResult(
            model=PRIMARY_MODEL,
            provider="openrouter",
            observation_id=7,
            status="failed",
            elapsed_seconds=1.3,
            schema_valid=False,
            fallback_used=True,
            error_class="JSONDecodeError",
            failure_cause="malformed_json",
            completed_at="2026-06-03T00:00:00+00:00",
        )
    )
    partial_payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert partial_payload["observation_concurrency"] == 4
    assert partial_payload["observation_partials"][0]["observation_id"] == 7
    assert partial_payload["results"] == []

    writer.record(_result(PRIMARY_MODEL, "openrouter", "safe_batch"))
    final_payload = json.loads(output_json.read_text(encoding="utf-8"))
    report = output_md.read_text(encoding="utf-8")

    assert final_payload["observation_partials"][0]["failure_cause"] == "malformed_json"
    assert (
        final_payload["observation_partials"][0]["structured_output_enabled"] is False
    )
    assert (
        final_payload["observation_partials"][0]["token_parameter"] == ""
    )
    assert final_payload["results"][0]["model"] == PRIMARY_MODEL
    assert "Observation Partials" in report


def test_openrouter_result_metadata_marks_structured_output_enabled():
    result = _result(PRIMARY_MODEL, "openrouter", "safe_batch")
    partial = ObservationEvaluationResult(
        model=PRIMARY_MODEL,
        provider="openrouter",
        observation_id=7,
        status="completed",
        elapsed_seconds=1.3,
        schema_valid=True,
        structured_output_enabled=True,
        structured_outputs=True,
        provider_require_parameters=True,
        token_parameter="max_tokens",
    )

    result_dict = result.to_dict()
    partial_dict = partial.to_partial_dict()

    assert result_dict["structured_output_enabled"] is True
    assert result_dict["structured_outputs"] is True
    assert result_dict["provider_require_parameters"] is True
    assert result_dict["token_parameter"] == "max_tokens"
    assert partial_dict["structured_output_enabled"] is True
    assert partial_dict["structured_outputs"] is True
    assert partial_dict["provider_require_parameters"] is True
    assert partial_dict["token_parameter"] == "max_tokens"


def test_result_writer_records_openrouter_reasoning_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENT_OPENROUTER_REASONING_EFFORT", "none")
    monkeypatch.setenv("AGENT_OPENROUTER_REASONING_EXCLUDE", "true")
    output_json = tmp_path / "comparison.json"
    output_md = tmp_path / "comparison.md"
    writer = ResultWriter(
        output_json=output_json,
        output_md=output_md,
        provider="openrouter",
        models=[PRIMARY_MODEL],
        safe_batch_size=1,
        concurrency=1,
        fail_fast_on_safe_batch=True,
    )

    writer.record(
        _result(
            PRIMARY_MODEL,
            "openrouter",
            "safe_batch",
            reasoning_effort="none",
            reasoning_exclude=True,
        )
    )

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    report = output_md.read_text(encoding="utf-8")

    assert payload["reasoning_effort"] == "none"
    assert payload["reasoning_exclude"] is True
    assert payload["results"][0]["reasoning_effort"] == "none"
    assert payload["results"][0]["reasoning_exclude"] is True
    assert "reasoning_exclude" in report


def test_raw_diagnostic_writer_is_separate_and_redacts_secret_like_text(tmp_path):
    diagnostic_json = tmp_path / "deepseek.raw-diagnostic.json"
    writer = DigestDiagnosticWriter(
        output_json=diagnostic_json,
        provider="openrouter",
        models=[PRIMARY_MODEL],
    )

    writer.record_failure(
        {
            "observation_id": 9,
            "provider": "openrouter",
            "model": PRIMARY_MODEL,
            "error_class": "JSONDecodeError",
            "error_message_sanitized": "JSONDecodeError",
            "raw_response_text": "<think>reasoning</think> {bad json} Bearer sk-secretvalue",
            "usage": {"completion_tokens": 12, "reasoning_tokens": 4},
            "response_metadata": {
                "reasoning_present": True,
                "message_keys": ["content", "reasoning"],
            },
        }
    )

    payload = json.loads(diagnostic_json.read_text(encoding="utf-8"))

    assert payload["diagnostic_mode"] == "explicit_opt_in_failure_raw_response_only"
    assert payload["raw_response_persisted_to_db"] is False
    assert payload["raw_response_in_standard_artifact"] is False
    assert payload["failure_count"] == 1
    failure = payload["failures"][0]
    assert failure["raw_response_sha256"]
    assert "<think>reasoning</think>" in failure["raw_response_text_redacted"]
    assert "sk-secretvalue" not in json.dumps(payload, ensure_ascii=False)
    assert failure["response_metadata"]["reasoning_present"] is True


def test_first_partial_elapsed_uses_completion_order_not_fastest_call():
    results = [
        ObservationEvaluationResult(
            model=PRIMARY_MODEL,
            provider="openrouter",
            observation_id=2,
            status="completed",
            elapsed_seconds=21.3,
        ),
        ObservationEvaluationResult(
            model=PRIMARY_MODEL,
            provider="openrouter",
            observation_id=13,
            status="failed",
            elapsed_seconds=14.5,
            failure_cause="schema_validation",
        ),
    ]

    assert _first_partial_elapsed_seconds(results) == 21.3
