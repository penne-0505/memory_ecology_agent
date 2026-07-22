"""Run live digest proposal evaluation across multiple LLM models.

The runner is evaluation-only. It starts with a small safe batch and only moves
to bounded concurrency when the safe batch does not show severe failures. It
never persists raw provider responses; it reuses the proposal persistence path,
which stores sanitized proposal metadata only.
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import sys
from threading import Lock
import time
from typing import Any, Callable, Iterable

from sqlalchemy import select

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from _evals.scripts.evaluate_llm_digest_proposals import (  # noqa: E402
    FIXTURE_WORLD,
    PROMPT_VERSION,
    _collect_rows,
    _metrics,
    _prepare_root,
    _run_cycle,
    _settings_for,
)
from app.cognition.digest_decider import create_digest_proposal  # noqa: E402
from app.db.models import DigestDecisionProposal, DigestDecisionTrace, Observation  # noqa: E402
from app.db.session import session_scope  # noqa: E402
from app.schemas import DigestDecision  # noqa: E402


PRIMARY_MODEL = "deepseek/deepseek-v4-pro"
DEFAULT_OUTPUT_JSON = (
    REPO_ROOT
    / "_evals"
    / "reports"
    / f"live_digest_model_comparison_{datetime.now(UTC).date().isoformat()}.json"
)
DEFAULT_OUTPUT_MD = DEFAULT_OUTPUT_JSON.with_suffix(".md")
SEVERE_FAILURE_CAUSES = {
    "malformed_json",
    "provider_error",
    "schema_validation",
    "timeout",
    "orchestration_error",
    "safety_boundary",
}


@dataclass(frozen=True)
class ModelEvaluationResult:
    model: str
    provider: str
    status: str
    phase: str
    elapsed_seconds: float = 0.0
    temp_root: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    failure_causes: dict[str, int] = field(default_factory=dict)
    safety_checks: dict[str, bool] = field(default_factory=dict)
    error_class: str = ""
    error_message: str = ""
    started_at: str = ""
    completed_at: str = ""
    partial_flushes: list[dict[str, Any]] = field(default_factory=list)
    validation_failure_aggregate: list[dict[str, Any]] = field(default_factory=list)
    structured_output_enabled: bool = False
    structured_outputs: bool = False
    provider_require_parameters: bool = False
    token_parameter: str = ""
    reasoning_effort: str = ""
    reasoning_exclude: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "provider": self.provider,
            "status": self.status,
            "phase": self.phase,
            "elapsed_seconds": self.elapsed_seconds,
            "temp_root": self.temp_root,
            "metrics": self.metrics,
            "failure_causes": self.failure_causes,
            "safety_checks": self.safety_checks,
            "error_class": self.error_class,
            "error_message": self.error_message,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "partial_flushes": self.partial_flushes,
            "validation_failure_aggregate": self.validation_failure_aggregate,
            "structured_output_enabled": self.structured_output_enabled,
            "structured_outputs": self.structured_outputs,
            "provider_require_parameters": self.provider_require_parameters,
            "token_parameter": self.token_parameter,
            "reasoning_effort": self.reasoning_effort,
            "reasoning_exclude": self.reasoning_exclude,
        }


@dataclass(frozen=True)
class ObservationEvaluationResult:
    model: str
    provider: str
    observation_id: int
    status: str
    elapsed_seconds: float
    schema_valid: bool = False
    fallback_used: bool = False
    error_class: str = ""
    failure_cause: str = ""
    completed_at: str = ""
    validation_failure_aggregate: list[dict[str, Any]] = field(default_factory=list)
    structured_output_enabled: bool = False
    structured_outputs: bool = False
    provider_require_parameters: bool = False
    token_parameter: str = ""
    reasoning_effort: str = ""
    reasoning_exclude: bool | None = None

    def to_partial_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "provider": self.provider,
            "observation_id": self.observation_id,
            "status": self.status,
            "elapsed_seconds": self.elapsed_seconds,
            "schema_valid": self.schema_valid,
            "fallback_used": self.fallback_used,
            "failure_cause": self.failure_cause,
            "error_class": self.error_class,
            "completed_at": self.completed_at,
            "validation_failure_aggregate": self.validation_failure_aggregate,
            "structured_output_enabled": self.structured_output_enabled,
            "structured_outputs": self.structured_outputs,
            "provider_require_parameters": self.provider_require_parameters,
            "token_parameter": self.token_parameter,
            "reasoning_effort": self.reasoning_effort,
            "reasoning_exclude": self.reasoning_exclude,
        }


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _parse_models(values: Iterable[str]) -> list[str]:
    models: list[str] = []
    for value in values:
        for item in value.split(","):
            model = item.strip()
            if model:
                models.append(model)
    deduped: list[str] = []
    seen: set[str] = set()
    for model in models:
        if model not in seen:
            seen.add(model)
            deduped.append(model)
    return deduped


def _cause_for_error_class(error_class: str) -> str:
    normalized = error_class.strip()
    if not normalized:
        return ""
    if normalized == "JSONDecodeError":
        return "malformed_json"
    if normalized == "ValidationError":
        return "schema_validation"
    if normalized in {"LLMProviderError", "LLMConfigurationError"}:
        return "provider_error"
    if normalized in {"TimeoutError", "TimeoutExpired"}:
        return "timeout"
    if normalized == "UnsafeOutput":
        return "safety_boundary"
    return "orchestration_error"


def _structured_output_metadata(provider: str) -> dict[str, Any]:
    enabled = provider.strip().lower() == "openrouter"
    reasoning_effort = os.environ.get("AGENT_OPENROUTER_REASONING_EFFORT", "").strip().lower()
    reasoning_exclude = _parse_optional_bool(
        os.environ.get("AGENT_OPENROUTER_REASONING_EXCLUDE", "")
    )
    return {
        "structured_output_enabled": enabled,
        "structured_outputs": enabled,
        "provider_require_parameters": enabled,
        "token_parameter": "max_tokens" if enabled else "max_completion_tokens",
        "reasoning_effort": reasoning_effort if enabled else "",
        "reasoning_exclude": reasoning_exclude if enabled else None,
    }


def _parse_optional_bool(value: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return None


def classify_failure_causes(
    rows: list[dict[str, Any]],
    metrics: dict[str, Any] | None = None,
    *,
    orchestration_error: str = "",
    safety_checks: dict[str, bool] | None = None,
) -> dict[str, int]:
    causes = Counter()
    for row in rows:
        cause = _cause_for_error_class(str(row.get("error_class") or ""))
        if cause:
            causes.update([cause])
    if orchestration_error:
        causes.update([_cause_for_error_class(orchestration_error)])
    if metrics and int(metrics.get("raw_response_persisted_count") or 0) > 0:
        causes.update(["safety_boundary"])
    if safety_checks:
        for passed in safety_checks.values():
            if not passed:
                causes.update(["safety_boundary"])
                break
    return dict(sorted(causes.items()))


def validation_failure_aggregate_from_rows(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    aggregate = Counter()
    for row in rows:
        if str(row.get("error_class") or "") != "ValidationError":
            continue
        sanitized = row.get("error_message_sanitized")
        if not isinstance(sanitized, str) or not sanitized.strip():
            continue
        try:
            counts = json.loads(sanitized)
        except json.JSONDecodeError:
            continue
        if not isinstance(counts, dict):
            continue
        for key, count in counts.items():
            if not isinstance(key, str) or ":" not in key:
                continue
            loc, error_type = key.rsplit(":", 1)
            try:
                safe_count = int(count)
            except (TypeError, ValueError):
                continue
            if safe_count <= 0:
                continue
            aggregate[(loc or "(root)", error_type or "unknown")] += safe_count
    return [
        {"loc": loc, "type": error_type, "count": count}
        for (loc, error_type), count in sorted(aggregate.items())
    ]


def merge_validation_failure_aggregates(
    aggregates: Iterable[list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    aggregate = Counter()
    for entries in aggregates:
        for entry in entries:
            loc = str(entry.get("loc") or "(root)")
            error_type = str(entry.get("type") or "unknown")
            try:
                count = int(entry.get("count") or 0)
            except (TypeError, ValueError):
                continue
            if count > 0:
                aggregate[(loc, error_type)] += count
    return [
        {"loc": loc, "type": error_type, "count": count}
        for (loc, error_type), count in sorted(aggregate.items())
    ]


def _safety_checks(settings_provider: str, shadow: dict[str, Any], metrics: dict[str, Any]) -> dict[str, bool]:
    wake_result = shadow.get("run", {}).get("wake_result", {})
    return {
        "raw_response_not_persisted": metrics.get("raw_response_persisted_count", 0) == 0,
        "final_digest_decisions_exist": shadow["counts"]["digest_decisions"]
        == shadow["counts"]["observations"],
        "web_search_disabled": True,
        "discord_disabled": True,
        "proposal_only_shadow": settings_provider in {"openrouter", "mock", "openai", "claude", "gemini"},
        "wake_cycle_completed": bool(wake_result),
    }


def _deterministic_baseline(root: Path) -> tuple[Any, dict[str, Any]]:
    settings = _settings_for(root, digest_decider="deterministic")
    run = _run_cycle(settings, "live-digest-observation-baseline")
    baseline = _collect_rows(settings)
    baseline["run"] = run
    return settings, baseline


def _observation_ids(settings: Any) -> list[int]:
    with session_scope(settings) as session:
        return list(session.scalars(select(Observation.id).order_by(Observation.id)).all())


def _evaluate_observation(
    *,
    settings: Any,
    model: str,
    provider: str,
    observation_id: int,
    raw_failure_diagnostic: Callable[[dict[str, Any]], None] | None = None,
) -> ObservationEvaluationResult:
    started = time.monotonic()
    try:
        with session_scope(settings) as session:
            observation = session.get(Observation, observation_id)
            trace = session.scalar(
                select(DigestDecisionTrace).where(
                    DigestDecisionTrace.source_observation_id == observation_id
                )
            )
            if observation is None or trace is None:
                raise RuntimeError("Missing deterministic observation or decision trace.")
            decision = DigestDecision(
                observation_id=observation_id,
                disposition=trace.decision,
                reason=trace.reason,
            )
            result = create_digest_proposal(
                session,
                observation,
                decision,
                settings,
                raw_failure_diagnostic=raw_failure_diagnostic,
            )
            if result.proposal is not None:
                result.proposal.deterministic_digest_decision_id = trace.id
                result.proposal.final_digest_decision_id = trace.id
                proposal = result.proposal
            else:
                proposal = session.scalar(
                    select(DigestDecisionProposal).where(
                        DigestDecisionProposal.observation_id == observation_id
                    )
                )
            error_class = proposal.error_class if proposal is not None else ""
            failure_cause = _cause_for_error_class(error_class)
            validation_aggregate = (
                validation_failure_aggregate_from_rows(
                    [
                        {
                            "error_class": proposal.error_class,
                            "error_message_sanitized": proposal.error_message_sanitized,
                        }
                    ]
                )
                if proposal is not None
                else []
            )
            return ObservationEvaluationResult(
                model=model,
                provider=provider,
                observation_id=observation_id,
                status="completed" if not failure_cause else "failed",
                elapsed_seconds=round(time.monotonic() - started, 1),
                schema_valid=bool(proposal.schema_valid) if proposal is not None else False,
                fallback_used=bool(proposal.fallback_used) if proposal is not None else False,
                error_class=error_class,
                failure_cause=failure_cause,
                completed_at=_now_iso(),
                validation_failure_aggregate=validation_aggregate,
                **_structured_output_metadata(provider),
            )
    except Exception as exc:  # noqa: BLE001 - sanitized observation-level failure.
        return ObservationEvaluationResult(
            model=model,
            provider=provider,
            observation_id=observation_id,
            status="failed",
            elapsed_seconds=round(time.monotonic() - started, 1),
            error_class=exc.__class__.__name__,
            failure_cause=_cause_for_error_class(exc.__class__.__name__),
            completed_at=_now_iso(),
            **_structured_output_metadata(provider),
        )


def _run_observation_proposals(
    *,
    settings: Any,
    model: str,
    provider: str,
    observation_ids: list[int],
    observation_concurrency: int,
    on_partial: Callable[[ObservationEvaluationResult], None],
    raw_failure_diagnostic: Callable[[dict[str, Any]], None] | None = None,
) -> list[ObservationEvaluationResult]:
    max_workers = max(1, min(observation_concurrency, len(observation_ids) or 1))
    results: list[ObservationEvaluationResult] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                _evaluate_observation,
                settings=settings,
                model=model,
                provider=provider,
                observation_id=observation_id,
                raw_failure_diagnostic=raw_failure_diagnostic,
            )
            for observation_id in observation_ids
        ]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            on_partial(result)
    return results


def _first_partial_elapsed_seconds(results: list[ObservationEvaluationResult]) -> float:
    if not results:
        return 0.0
    return results[0].elapsed_seconds


def evaluate_model(
    model: str,
    provider: str,
    phase: str,
    *,
    observation_concurrency: int = 1,
    max_observations: int = 0,
    on_partial: Callable[[ObservationEvaluationResult], None] = lambda _result: None,
    raw_failure_diagnostic: Callable[[dict[str, Any]], None] | None = None,
) -> ModelEvaluationResult:
    started_at = _now_iso()
    started = time.monotonic()
    root = _prepare_root()
    try:
        _deterministic_baseline(root)
        settings = _settings_for(
            root,
            digest_decider="llm_shadow",
            provider=provider,
            model=model,
        )
        observation_results = _run_observation_proposals(
            settings=settings,
            model=model,
            provider=provider,
            observation_ids=_observation_ids(settings)[:max_observations]
            if max_observations > 0
            else _observation_ids(settings),
            observation_concurrency=observation_concurrency,
            on_partial=on_partial,
            raw_failure_diagnostic=raw_failure_diagnostic,
        )
        shadow = _collect_rows(settings)
        shadow["run"] = {"wake_result": {"observations": shadow["counts"]["observations"]}}
        metrics = _metrics(shadow["proposal_rows"], shadow["counts"])
        safety_checks = _safety_checks(provider, shadow, metrics)
        failure_causes = classify_failure_causes(
            shadow["proposal_rows"],
            metrics,
            safety_checks=safety_checks,
        )
        validation_aggregate = validation_failure_aggregate_from_rows(
            shadow["proposal_rows"]
        )
        persisted_observation_ids = {
            int(row["observation_id"]) for row in shadow["proposal_rows"]
        }
        observation_cause_counts = Counter(
            result.failure_cause
            for result in observation_results
            if result.failure_cause
            and result.observation_id not in persisted_observation_ids
        )
        if observation_cause_counts:
            merged_causes = Counter(failure_causes)
            merged_causes.update(observation_cause_counts)
            failure_causes = dict(sorted(merged_causes.items()))
        status = "completed" if all(safety_checks.values()) else "safety_failed"
        first_partial_at = _first_partial_elapsed_seconds(observation_results)
        return ModelEvaluationResult(
            model=model,
            provider=provider,
            status=status,
            phase=phase,
            elapsed_seconds=round(time.monotonic() - started, 1),
            temp_root=str(root),
            metrics=metrics,
            failure_causes=failure_causes,
            safety_checks=safety_checks,
            started_at=started_at,
            completed_at=_now_iso(),
            partial_flushes=[
                {
                    "count": len(observation_results),
                    "first_partial_elapsed_seconds": first_partial_at,
                }
            ],
            validation_failure_aggregate=validation_aggregate,
            **_structured_output_metadata(provider),
        )
    except Exception as exc:  # noqa: BLE001 - evaluation runner records sanitized failures.
        return ModelEvaluationResult(
            model=model,
            provider=provider,
            status="failed",
            phase=phase,
            elapsed_seconds=round(time.monotonic() - started, 1),
            temp_root=str(root),
            failure_causes=classify_failure_causes(
                [],
                orchestration_error=exc.__class__.__name__,
            ),
            error_class=exc.__class__.__name__,
            error_message=_sanitize_error_message(str(exc)),
            started_at=started_at,
            completed_at=_now_iso(),
            **_structured_output_metadata(provider),
        )


def _sanitize_error_message(message: str) -> str:
    redacted = message
    for key in [
        os.environ.get("OPENROUTER_API_KEY", ""),
        os.environ.get("OPENAI_API_KEY", ""),
        os.environ.get("ANTHROPIC_API_KEY", ""),
        os.environ.get("GEMINI_API_KEY", ""),
    ]:
        if key:
            redacted = redacted.replace(key, "[REDACTED]")
    return redacted[:240]


def _has_severe_failure(result: ModelEvaluationResult) -> bool:
    if result.status in {"failed", "safety_failed"}:
        return True
    return any(result.failure_causes.get(cause, 0) > 0 for cause in SEVERE_FAILURE_CAUSES)


def _run_batch(
    *,
    models: list[str],
    provider: str,
    phase: str,
    concurrency: int,
    evaluate: Callable[[str, str, str], ModelEvaluationResult],
    on_result: Callable[[ModelEvaluationResult], None],
) -> list[ModelEvaluationResult]:
    if not models:
        return []
    max_workers = max(1, min(concurrency, len(models)))
    results: list[ModelEvaluationResult] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(evaluate, model, provider, phase): model for model in models
        }
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            on_result(result)
    return results


class DigestDiagnosticWriter:
    SECRET_PATTERN = re.compile(
        r"(sk-[A-Za-z0-9_-]{8,}|[A-Za-z0-9_]*API[_-]?KEY|Authorization:|Bearer\s+[A-Za-z0-9._-]+)",
        re.IGNORECASE,
    )

    def __init__(
        self,
        *,
        output_json: Path,
        provider: str,
        models: list[str],
    ) -> None:
        self.output_json = output_json
        self.provider = provider
        self.models = models
        self.started_at = _now_iso()
        self.failures: list[dict[str, Any]] = []
        self._lock = Lock()

    def record_failure(self, diagnostic: dict[str, Any]) -> None:
        raw_text = str(diagnostic.get("raw_response_text") or "")
        redacted_text = self._redact(raw_text)
        entry = {
            "observation_id": diagnostic.get("observation_id"),
            "provider": diagnostic.get("provider") or self.provider,
            "model": diagnostic.get("model") or "",
            "error_class": diagnostic.get("error_class") or "",
            "error_message_sanitized": diagnostic.get("error_message_sanitized") or "",
            "raw_response_sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
            if raw_text
            else "",
            "raw_response_text_redacted": redacted_text,
            "raw_response_char_count": len(raw_text),
            "usage": diagnostic.get("usage") if isinstance(diagnostic.get("usage"), dict) else {},
            "response_metadata": diagnostic.get("response_metadata")
            if isinstance(diagnostic.get("response_metadata"), dict)
            else {},
            "captured_at": _now_iso(),
        }
        with self._lock:
            self.failures.append(entry)
            self.flush()

    def _redact(self, text: str) -> str:
        redacted = text
        for key in [
            os.environ.get("OPENROUTER_API_KEY", ""),
            os.environ.get("OPENAI_API_KEY", ""),
            os.environ.get("ANTHROPIC_API_KEY", ""),
            os.environ.get("GEMINI_API_KEY", ""),
        ]:
            if key:
                redacted = redacted.replace(key, "[REDACTED]")
        return self.SECRET_PATTERN.sub("[REDACTED]", redacted)

    def flush(self) -> None:
        self.output_json.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "runner": "live_digest_model_comparison_raw_diagnostic",
            "diagnostic_mode": "explicit_opt_in_failure_raw_response_only",
            "started_at": self.started_at,
            "updated_at": _now_iso(),
            "provider": self.provider,
            "models_requested": self.models,
            "raw_response_persisted_to_db": False,
            "raw_response_in_standard_artifact": False,
            "failure_count": len(self.failures),
            "failures": self.failures,
        }
        self.output_json.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def run_models(
    *,
    models: list[str],
    provider: str,
    safe_batch_size: int,
    concurrency: int,
    fail_fast_on_safe_batch: bool,
    observation_concurrency: int = 1,
    max_observations: int = 0,
    evaluate: Callable[..., ModelEvaluationResult] = evaluate_model,
    on_result: Callable[[ModelEvaluationResult], None] = lambda _result: None,
    on_partial: Callable[[ObservationEvaluationResult], None] = lambda _result: None,
    raw_failure_diagnostic: Callable[[dict[str, Any]], None] | None = None,
) -> list[ModelEvaluationResult]:
    def evaluate_with_partials(model: str, provider: str, phase: str) -> ModelEvaluationResult:
        parameters = inspect.signature(evaluate).parameters
        if (
            "observation_concurrency" not in parameters
            and "on_partial" not in parameters
            and "max_observations" not in parameters
            and "raw_failure_diagnostic" not in parameters
        ):
            return evaluate(model, provider, phase)
        kwargs: dict[str, Any] = {}
        if "observation_concurrency" in parameters:
            kwargs["observation_concurrency"] = observation_concurrency
        if "max_observations" in parameters:
            kwargs["max_observations"] = max_observations
        if "on_partial" in parameters:
            kwargs["on_partial"] = on_partial
        if "raw_failure_diagnostic" in parameters:
            kwargs["raw_failure_diagnostic"] = raw_failure_diagnostic
        return evaluate(model, provider, phase, **kwargs)

    safe_count = min(max(safe_batch_size, 0), len(models))
    safe_models = models[:safe_count]
    remaining_models = models[safe_count:]
    safe_results = _run_batch(
        models=safe_models,
        provider=provider,
        phase="safe_batch",
        concurrency=min(max(concurrency, 1), max(safe_count, 1)),
        evaluate=evaluate_with_partials,
        on_result=on_result,
    )
    if fail_fast_on_safe_batch and any(_has_severe_failure(result) for result in safe_results):
        skipped = [
            ModelEvaluationResult(
                model=model,
                provider=provider,
                status="skipped",
                phase="bounded",
                failure_causes={"safe_batch_gate": 1},
                started_at=_now_iso(),
                completed_at=_now_iso(),
            )
            for model in remaining_models
        ]
        for result in skipped:
            on_result(result)
        return safe_results + skipped
    bounded_results = _run_batch(
        models=remaining_models,
        provider=provider,
        phase="bounded",
        concurrency=max(concurrency, 1),
        evaluate=evaluate_with_partials,
        on_result=on_result,
    )
    return safe_results + bounded_results


class ResultWriter:
    def __init__(
        self,
        *,
        output_json: Path,
        output_md: Path,
        provider: str,
        models: list[str],
        safe_batch_size: int,
        concurrency: int,
        fail_fast_on_safe_batch: bool,
        observation_concurrency: int = 1,
        max_observations: int = 0,
    ) -> None:
        self.output_json = output_json
        self.output_md = output_md
        self.provider = provider
        self.models = models
        self.safe_batch_size = safe_batch_size
        self.concurrency = concurrency
        self.observation_concurrency = observation_concurrency
        self.max_observations = max_observations
        self.fail_fast_on_safe_batch = fail_fast_on_safe_batch
        self.results: list[ModelEvaluationResult] = []
        self.observation_results: list[ObservationEvaluationResult] = []
        self.started_at = _now_iso()

    def record(self, result: ModelEvaluationResult) -> None:
        self.results.append(result)
        self.flush()

    def record_partial(self, result: ObservationEvaluationResult) -> None:
        self.observation_results.append(result)
        self.flush()

    def flush(self) -> None:
        self.output_json.parent.mkdir(parents=True, exist_ok=True)
        payload = self._payload()
        self.output_json.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self.output_md.write_text(self._markdown(payload), encoding="utf-8")

    def _payload(self) -> dict[str, Any]:
        cause_counts = Counter()
        status_counts = Counter()
        for result in self.results:
            cause_counts.update(result.failure_causes)
            status_counts.update([result.status])
        validation_aggregate = merge_validation_failure_aggregates(
            result.validation_failure_aggregate for result in self.results
        )
        return {
            "runner": "live_digest_model_comparison",
            "started_at": self.started_at,
            "updated_at": _now_iso(),
            "provider": self.provider,
            "models_requested": self.models,
            "safe_batch_size": self.safe_batch_size,
            "concurrency": self.concurrency,
            "observation_concurrency": self.observation_concurrency,
            "max_observations": self.max_observations,
            "fail_fast_on_safe_batch": self.fail_fast_on_safe_batch,
            "fixture_world": str(FIXTURE_WORLD),
            "prompt_version": PROMPT_VERSION,
            "raw_provider_response_persisted": False,
            **_structured_output_metadata(self.provider),
            "status_counts": dict(sorted(status_counts.items())),
            "failure_cause_counts": dict(sorted(cause_counts.items())),
            "validation_failure_aggregate": validation_aggregate,
            "observation_partials": [
                result.to_partial_dict() for result in self.observation_results
            ],
            "results": [result.to_dict() for result in self.results],
        }

    def _markdown(self, payload: dict[str, Any]) -> str:
        lines = [
            "---",
            "title: Live Digest Model Comparison",
            "status: active",
            "draft_status: n/a",
            f"created_at: {datetime.now(UTC).date().isoformat()}",
            f"updated_at: {datetime.now(UTC).date().isoformat()}",
            "references:",
            '  - "_docs/intent/Core/llm-digest-live-runner-hardening/decision.md"',
            '  - "_docs/qa/Core/llm-digest-live-runner-hardening/test-plan.md"',
            '  - "_docs/intent/Core/llm-digest-observation-parallelism/decision.md"',
            '  - "_docs/qa/Core/llm-digest-observation-parallelism/test-plan.md"',
            "related_issues: []",
            "related_prs: []",
            "---",
            "",
            "# Live Digest Model Comparison",
            "",
            "## Runner",
            "",
            f"- provider: `{payload['provider']}`",
            f"- safe_batch_size: `{payload['safe_batch_size']}`",
            f"- concurrency: `{payload['concurrency']}`",
            f"- observation_concurrency: `{payload['observation_concurrency']}`",
            f"- max_observations: `{payload['max_observations']}`",
            f"- fail_fast_on_safe_batch: `{payload['fail_fast_on_safe_batch']}`",
            f"- prompt_version: `{payload['prompt_version']}`",
            f"- raw_provider_response_persisted: `{payload['raw_provider_response_persisted']}`",
            f"- structured_output_enabled: `{payload['structured_output_enabled']}`",
            f"- structured_outputs: `{payload['structured_outputs']}`",
            f"- provider_require_parameters: `{payload['provider_require_parameters']}`",
            f"- token_parameter: `{payload['token_parameter']}`",
            f"- reasoning_effort: `{payload['reasoning_effort']}`",
            f"- reasoning_exclude: `{payload['reasoning_exclude']}`",
            "",
            "## Summary",
            "",
            f"- status_counts: `{payload['status_counts']}`",
            f"- failure_cause_counts: `{payload['failure_cause_counts']}`",
            f"- validation_failure_aggregate: `{payload['validation_failure_aggregate']}`",
            "",
            "## Results",
            "",
            "| Model | Phase | Status | Valid | Fallback | Causes | Elapsed |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        for result in payload["results"]:
            metrics = result.get("metrics") or {}
            lines.append(
                "| "
                f"`{result['model']}` | "
                f"`{result['phase']}` | "
                f"`{result['status']}` | "
                f"`{metrics.get('schema_valid_proposals', '')}` | "
                f"`{metrics.get('rejected_or_fallback_proposals', '')}` | "
                f"`{result.get('failure_causes', {})}` | "
                f"`{result.get('elapsed_seconds', 0.0)}` |"
            )
        lines.extend(
            [
                "",
                "## Validation Failure Aggregate",
                "",
                "| Field / Loc | Type | Count |",
                "| --- | --- | --- |",
            ]
        )
        for entry in payload["validation_failure_aggregate"]:
            lines.append(
                "| "
                f"`{entry['loc']}` | "
                f"`{entry['type']}` | "
                f"`{entry['count']}` |"
            )
        lines.extend(
            [
                "",
                "## Observation Partials",
                "",
                "| Model | Observation | Status | Schema Valid | Fallback | Cause | Elapsed |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for partial in payload["observation_partials"]:
            lines.append(
                "| "
                f"`{partial['model']}` | "
                f"`{partial['observation_id']}` | "
                f"`{partial['status']}` | "
                f"`{partial['schema_valid']}` | "
                f"`{partial['fallback_used']}` | "
                f"`{partial['failure_cause']}` | "
                f"`{partial['elapsed_seconds']}` |"
            )
        lines.extend(
            [
                "",
                "## Safety",
                "",
                "- Raw provider response text is not included.",
                "- Credential values are not printed.",
                "- Evaluation uses isolated temp roots and `llm_shadow` proposal records.",
                "- Final digest decisions remain deterministic.",
                "- Web search is disabled in evaluation settings.",
                "- Discord settings remain disabled.",
                "",
            ]
        )
        return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default=os.environ.get("AGENT_LLM_PROVIDER", "openrouter"))
    parser.add_argument("--models", action="append", default=[])
    parser.add_argument("--model", action="append", default=[])
    parser.add_argument("--safe-batch-size", type=int, default=3)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--observation-concurrency", type=int, default=1)
    parser.add_argument("--max-observations", type=int, default=0)
    parser.add_argument("--fail-fast-on-safe-batch", action="store_true")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument(
        "--capture-raw-diagnostics",
        action="store_true",
        help="Explicit opt-in: save failed LLM proposal raw response content to a separate diagnostic JSON artifact.",
    )
    parser.add_argument(
        "--raw-diagnostic-json",
        type=Path,
        default=None,
        help="Dedicated JSON artifact for --capture-raw-diagnostics. Defaults to <output-json>.raw-diagnostic.json.",
    )
    args = parser.parse_args()

    models = _parse_models(args.models + args.model)
    if not models:
        models = [PRIMARY_MODEL]

    writer = ResultWriter(
        output_json=args.output_json,
        output_md=args.output_md,
        provider=args.provider,
        models=models,
        safe_batch_size=args.safe_batch_size,
        concurrency=args.concurrency,
        observation_concurrency=args.observation_concurrency,
        max_observations=args.max_observations,
        fail_fast_on_safe_batch=args.fail_fast_on_safe_batch,
    )
    writer.flush()
    diagnostic_writer = None
    if args.capture_raw_diagnostics:
        diagnostic_output = args.raw_diagnostic_json or args.output_json.with_suffix(
            ".raw-diagnostic.json"
        )
        diagnostic_writer = DigestDiagnosticWriter(
            output_json=diagnostic_output,
            provider=args.provider,
            models=models,
        )
        diagnostic_writer.flush()
    run_models(
        models=models,
        provider=args.provider,
        safe_batch_size=args.safe_batch_size,
        concurrency=args.concurrency,
        observation_concurrency=args.observation_concurrency,
        max_observations=args.max_observations,
        fail_fast_on_safe_batch=args.fail_fast_on_safe_batch,
        on_result=writer.record,
        on_partial=writer.record_partial,
        raw_failure_diagnostic=diagnostic_writer.record_failure
        if diagnostic_writer is not None
        else None,
    )
    writer.flush()
    if diagnostic_writer is not None:
        diagnostic_writer.flush()
        print(diagnostic_writer.output_json)
    print(args.output_json)
    print(args.output_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
