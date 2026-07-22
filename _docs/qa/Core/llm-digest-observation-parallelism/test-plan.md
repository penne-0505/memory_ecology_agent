---
title: "QA Test Plan: LLM Digest Observation Parallelism"
status: active
draft_status: n/a
qa_status: planned
risk: Medium
created_at: 2026-06-03
updated_at: 2026-06-03
references:
  - "_docs/intent/Core/llm-digest-observation-parallelism/decision.md"
  - "_docs/plan/Core/llm-digest-observation-parallelism/plan.md"
  - "_docs/qa/Core/llm-digest-observation-parallelism/verification.md"
related_issues: []
related_prs: []
---

# QA Test Plan: LLM Digest Observation Parallelism

## Source of Intent

- TODO: `Core-Enhance-16`
- Plan: `_docs/plan/Core/llm-digest-observation-parallelism/plan.md`
- Intent: `_docs/intent/Core/llm-digest-observation-parallelism/decision.md`

## Quality Goal

Live digest model comparison runner が DeepSeek primary run を標準化し、1モデル内の proposal calls を bounded に並列化しつつ、raw provider response や production runtime boundary を変えずに partial progress を見せられる。

## Acceptance Criteria

- AC-001: runner に DeepSeek primary run 用の model default または documented command がある。
- AC-002: 1モデル内で observation-level bounded concurrency を指定できる。
- AC-003: observation 完了ごと、または小 batch 完了ごとに partial result が JSON / Markdown に flush される。
- AC-004: observation 単位で JSON decode / schema validation / provider / timeout / orchestration / safety boundary failure を分類できる。
- AC-005: 最終 aggregate metrics は既存 model-level report と比較可能である。
- AC-006: raw provider response / secrets 非保存、isolated temp root、final deterministic decision、no Web search、Discord disabled を維持する。
- AC-007: live run で最初の partial result が model completion 前に出ることを確認する。credential が無い場合は `SKIPPED_REAL_PROVIDER` とする。

## Intent-derived Invariants

- INV-001: The runner remains evaluation-only and does not implement active `llm_assisted` adoption.
- INV-002: Production runtime, `AGENT_DIGEST_DECIDER` default, and final deterministic digest decision path remain unchanged.
- INV-003: Raw provider response text and secrets are not written to JSON, Markdown, or stdout.
- INV-004: Evaluation uses isolated temp roots and keeps Web search disabled and Discord disabled.
- INV-005: Observation-level concurrency is bounded by an explicit CLI option.
- INV-006: Observation partial output is flushed before model completion when at least one observation completes first.
- INV-007: Final aggregate metrics remain comparable with prior model-level reports.

## Risk Assessment

- Risk level: Medium
- Risk rationale: Evaluation runner orchestration and external-provider operation are affected, but production runtime is not changed.
- Regression risk: Medium for runner output shape and docs alignment.
- Data safety risk: Medium because provider responses exist transiently in memory.
- Security / privacy risk: Medium because credential-bearing live provider configuration may be present in the environment.
- Agent misbehavior risk: Medium because evaluation-only partial results must not be confused with `llm_assisted` adoption.

## Test Strategy

- Unit / integration tests cover qwen default, observation partial writer behavior, model-level metrics comparability, and failure cause classification.
- Validator covers TODO / QA / docs references.
- Diff review checks production runtime, default digest decision path, Web search, Discord, and raw response handling.
- Live provider run is optional and credential-gated.

## Test Matrix

| ID | Source | Requirement / Invariant | Test Type | Command / File | Expected Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| AC-001 | TODO | DeepSeek primary default or documented command exists. | unit / docs | `tests/test_live_digest_runner.py`; plan doc | Default model is `deepseek/deepseek-v4-pro` and command is documented; qwen remains verified fallback/baseline. | verified |
| AC-002 | TODO | Observation-level bounded concurrency is configurable. | unit | `tests/test_live_digest_runner.py` | `observation_concurrency` is accepted and passed to evaluator. | verified |
| AC-003 | TODO | Partial result flush happens before model result flush. | integration | `tests/test_live_digest_runner.py` | JSON contains observation partials before completed model results. | verified |
| AC-004 | TODO | Observation-level failure causes are classified. | unit | `tests/test_live_digest_runner.py` | JSON/schema/provider/timeout/orchestration/safety causes map to expected labels. | verified |
| AC-005 | TODO | Final aggregate metrics remain comparable. | integration / diff review | `_evals/scripts/run_live_digest_model_comparison.py` | Final result still uses `_metrics()` and model-level metrics fields. | verified |
| AC-006 | TODO | Safety boundaries are maintained. | diff review / tests | `git diff -- app _evals tests _docs TODO.md` | No production runtime changes; no raw response text in outputs. | verified |
| AC-007 | TODO | Qwen live run partial flush is verified or skipped by credential gate. | manual QA | optional OpenRouter command | Verification records first partial timing before model completion. | verified |
| INV-001 | intent | No active adoption is implemented. | diff review | `git diff -- app _evals tests _docs TODO.md` | `llm_assisted` adoption path is unchanged. | verified |
| INV-002 | intent | Runtime defaults and final deterministic decision path remain unchanged. | regression | `uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_digest_decider.py` | Existing digest decider tests pass. | verified |
| INV-003 | intent | Raw provider response and secrets are not written. | unit / diff review | `tests/test_live_digest_runner.py` | Output contains sanitized partial fields only. | verified |
| INV-004 | intent | Isolated temp root, no Web search, Discord disabled remain. | unit / diff review | runner safety checks | Safety checks remain true for evaluation output. | verified |
| INV-005 | intent | Observation concurrency is bounded. | unit | `tests/test_live_digest_runner.py` | Configured concurrency is capped by observation count and minimum 1. | verified |
| INV-006 | intent | Partial output can flush before model completion. | integration | `tests/test_live_digest_runner.py` | Writer records observation partial before model result; live run confirmed this behavior. | verified |
| INV-007 | intent | Metrics are comparable. | integration | `tests/test_live_digest_runner.py` | Model result contains existing aggregate metric keys. | verified |

## Manual QA Checklist

- [x] Run optional OpenRouter smoke only if `OPENROUTER_API_KEY` is explicitly present.
- [x] Record first partial flush elapsed and total elapsed when live smoke runs.
- [x] Confirm `AGENT_MAX_WEB_QUERIES=0` is set for live smoke.
- [x] Confirm output JSON / Markdown do not include raw provider text or credential values.

## Regression Checklist

- [x] `./scripts/check-docs.sh`
- [x] `uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_live_digest_runner.py tests/test_digest_decider.py`
- [x] `uv run --python /home/penne/.local/bin/python3.12 pytest`

## Out of Scope

- Production runtime parallelism.
- Active `llm_assisted` adoption.
- Required 3-model live comparison.
- Provider-specific retry and rate-limit policy beyond bounded concurrency.

## Open Questions

- Whether a future follow-up should move SQLite writes to a single-writer queue if live provider concurrency reveals lock contention.
