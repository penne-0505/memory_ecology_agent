---
title: LLM Digest Observation Parallelism Decision
status: active
draft_status: n/a
created_at: 2026-06-03
updated_at: 2026-06-03
references:
  - "_docs/plan/Core/llm-digest-observation-parallelism/plan.md"
  - "_docs/qa/Core/llm-digest-observation-parallelism/test-plan.md"
  - "_docs/qa/Core/deepseek-digest-primary-candidate/verification.md"
  - "_evals/reports/live_digest_model_comparison_qwen_kimi_2026-06-02.md"
related_issues: []
related_prs: []
---

# LLM Digest Observation Parallelism Decision

## Context

The current live digest model comparison runner supports bounded concurrency across models, but each model still runs 16 observation proposal calls serially. On 2026-06-02, this made the first model-level flush arrive only after several minutes.

Live evidence from 2026-06-02:

- `qwen/qwen3.6-plus`: 397.3 seconds, schema-valid `14/16`, malformed JSON `0`, validation error `2`.
- `deepseek/deepseek-v4-pro`: 327.4 seconds, schema-valid `11/16`, malformed JSON `4`, validation error `1`.
- `moonshotai/kimi-k2.6`: 652.8 seconds, schema-valid `2/16`, malformed JSON `14`.

## Decision

Use `deepseek/deepseek-v4-pro` as the primary live evaluation model after the DeepSeek primary-candidate gate. Keep qwen as verified fallback/baseline evidence, and keep older v4pro / kimi runs as historical comparison evidence rather than required peers for every future live run.

Split the evaluation runner into isolated temp root preparation, deterministic baseline / observation collection, observation-level proposal generation, metrics aggregation, and partial output flush. Add observation-level bounded concurrency and flush sanitized partial rows as each observation completes.

## Alternatives

- **Keep model-internal serial execution**: rejected because operator-visible progress remains too delayed.
- **Only add more model-level concurrency**: rejected because it does not help single primary-model runs.
- **Change production wake cycle to parallelize digest proposals**: rejected because the current task is evaluation-only and production runtime must remain unchanged.

## Rationale

The main operation problem is not only total elapsed time. It is the long silent period before the first model-level artifact appears. Observation-level partial flush makes live evaluation inspectable without storing raw provider text or changing final deterministic digest decisions.

DeepSeek is selected because the current structured-output primary-candidate gate produced three clean runs when reasoning was explicitly disabled. qwen remains the verified fallback/baseline because it also has three clean structured runs under the qwen payload and useful historical comparison evidence.

## Consequences / Impact

- A DeepSeek single-model live run can produce partial JSON / Markdown before model completion.
- Existing aggregate metrics remain comparable because the final report still uses the same proposal row collection and `_metrics()` output.
- SQLite writes may occur from separate per-thread sessions, but no SQLAlchemy session is shared across threads.
- Real provider evidence remains optional and credential-gated.

## Quality Implications

- Partial flush must never include raw provider response text.
- Failure classification must distinguish model output failures from provider and orchestration failures.
- Observation parallelism must stay bounded to avoid unbounded provider pressure.

## Intent-derived Invariants

- INV-001: The runner remains evaluation-only and does not implement active `llm_assisted` adoption.
- INV-002: Production runtime, `AGENT_DIGEST_DECIDER` default, and final deterministic digest decision path remain unchanged.
- INV-003: Raw provider response text and secrets are not written to JSON, Markdown, or stdout.
- INV-004: Evaluation uses isolated temp roots and keeps Web search disabled and Discord disabled.
- INV-005: Observation-level concurrency is bounded by an explicit CLI option.
- INV-006: Observation partial output is flushed before model completion when at least one observation completes first.
- INV-007: Final aggregate metrics remain comparable with prior model-level reports.

## Rollback / Follow-ups

If live provider runs show SQLite write contention or provider rate-limit pressure, reduce `--observation-concurrency` to `1` or add a single-writer persistence queue in a follow-up. This does not affect production runtime.
