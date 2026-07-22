---
title: "QA Verification: LLM Digest Observation Parallelism"
status: active
draft_status: n/a
qa_status: verified
risk: Medium
created_at: 2026-06-03
updated_at: 2026-06-03
references:
  - "_docs/intent/Core/llm-digest-observation-parallelism/decision.md"
  - "_docs/plan/Core/llm-digest-observation-parallelism/plan.md"
  - "_docs/qa/Core/llm-digest-observation-parallelism/test-plan.md"
  - "_evals/reports/live_digest_model_comparison_qwen_observation_parallel_2026-06-03.md"
  - "_docs/qa/Core/deepseek-digest-primary-candidate/verification.md"
related_issues: []
related_prs: []
---

# QA Verification: `LLM Digest Observation Parallelism`

## Summary

The live digest model comparison runner now supports DeepSeek primary evaluation, observation-level bounded concurrency, and sanitized partial JSON / Markdown flushes before model completion. The implementation remains evaluation-only and keeps deterministic final digest decisions, no Web search, Discord disabled, isolated temp roots, and no raw provider response persistence. qwen remains verified fallback/baseline after the DeepSeek primary-candidate gate.

## Verification Verdict

Verdict: PASS

All requested AC / INV checks are covered by runner tests, digest decider regression tests, docs validation, full pytest, diff review, offline mock smoke, and a credentialed qwen OpenRouter live run. The live run confirmed first partial flush before model completion.

## Commands Run

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_live_digest_runner.py -q
```

Result:

```text
6 passed
```

```bash
uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/run_live_digest_model_comparison.py --provider mock --observation-concurrency 4 --output-json /tmp/live-digest-observation-parallelism.json --output-md /tmp/live-digest-observation-parallelism.md
```

Result:

```text
/tmp/live-digest-observation-parallelism.json
/tmp/live-digest-observation-parallelism.md
```

Output inspection:

```text
models_requested: ['qwen/qwen3.6-plus']
observation_concurrency: 4
observation_partials: 16
results: 1
raw_response_persisted_count: 0
```

```bash
AGENT_MAX_WEB_QUERIES=0 AGENT_LLM_PROVIDER=openrouter uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/run_live_digest_model_comparison.py --provider openrouter --model qwen/qwen3.6-plus --observation-concurrency 4 --output-json _evals/reports/live_digest_model_comparison_qwen_observation_parallel_2026-06-03.json --output-md _evals/reports/live_digest_model_comparison_qwen_observation_parallel_2026-06-03.md
```

Result:

```text
_evals/reports/live_digest_model_comparison_qwen_observation_parallel_2026-06-03.json
_evals/reports/live_digest_model_comparison_qwen_observation_parallel_2026-06-03.md
```

Live output inspection:

```text
first_partial_elapsed_seconds: 21.3
model_completed_elapsed_seconds: 112.4
schema_valid_proposals: 11/16
rejected_or_fallback_proposals: 5/16
malformed_json_count: 0
validation_error_count: 5
provider_error_count: 0
raw_response_persisted_count: 0
failure_causes: {'schema_validation': 5}
```

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_live_digest_runner.py tests/test_digest_decider.py
```

Result:

```text
16 passed in 0.26s
```

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest
```

Result:

```text
82 passed, 1 warning in 1.39s
```

Warning: `discord/player.py` imports deprecated `audioop`; unrelated to this change.

```bash
./scripts/check-docs.sh
```

Result:

```text
Checked 5 files
PASS todo _evals/validator-fixtures/todo/valid/basic.md
PASS qa _evals/validator-fixtures/qa/valid
```

## Automated Test Results

| Command / Test | Result | Notes |
| --- | --- | --- |
| `tests/test_live_digest_runner.py -q` | PASS | Covers qwen default, observation concurrency propagation, partial writer flush, and existing safe batch behavior. |
| Mock runner smoke | PASS | Confirms qwen default, observation partial output, existing aggregate metrics, and raw response non-persistence. |
| `tests/test_live_digest_runner.py tests/test_digest_decider.py` | PASS | 16 tests passed, covering runner behavior and digest decider regression. |
| Full pytest | PASS | 82 tests passed with one unrelated Discord `audioop` deprecation warning. |
| `./scripts/check-docs.sh` | PASS | TODO, QA, frontmatter, doc links, and validator fixtures passed. |

## Manual QA Results

| Checklist Item | Result | Notes |
| --- | --- | --- |
| Credential gate | PASS | `OPENROUTER_API_KEY` was present; secret value was not printed. |
| Qwen live run first partial before model completion | PASS | 4 partials and 0 model results were observed at the first live progress check; first recorded partial elapsed was `21.3` seconds, total elapsed was `112.4` seconds. |
| Live Web search disabled | PASS | Command set `AGENT_MAX_WEB_QUERIES=0`; runner settings also set `max_web_queries_per_cycle=0`. |
| Live raw response / secret non-persistence | PASS | Live output reports `raw_response_persisted_count=0` and contains sanitized partial fields only. |

## Acceptance Criteria Coverage

| ID | Status | Evidence |
| --- | --- | --- |
| AC-001 | PASS | `PRIMARY_MODEL` is now `deepseek/deepseek-v4-pro`; CLI defaults to DeepSeek when no model is provided; plan documents the DeepSeek command and qwen fallback/baseline role. |
| AC-002 | PASS | Runner accepts `--observation-concurrency`; tests verify the value is passed to observation evaluation. |
| AC-003 | PASS | `ResultWriter.record_partial()` flushes JSON / Markdown after observation completion; live run showed partials before model result. |
| AC-004 | PASS | Observation partials include `failure_cause`; classifier maps JSON decode, schema validation, provider, timeout, orchestration, and safety boundary errors. |
| AC-005 | PASS | Final model result still uses `_collect_rows()` and `_metrics()` shape; live report remains model-level comparable. |
| AC-006 | PASS | No production runtime files were changed; safety checks show raw response not persisted, final deterministic decisions, Web disabled, Discord disabled, and isolated temp root. |
| AC-007 | PASS | Qwen live run first partial recorded at `21.3` seconds; model completed at `112.4` seconds. |

## Invariant Coverage

| ID | Status | Evidence |
| --- | --- | --- |
| INV-001 | PASS | Runner remains evaluation-only; no active `llm_assisted` adoption was implemented. |
| INV-002 | PASS | `app/config.py` default remains `digest_decider="deterministic"`; final digest decision path is unchanged. |
| INV-003 | PASS | Output contains no raw provider response text; only sanitized status / failure / timing fields are written. |
| INV-004 | PASS | `_prepare_root()` is still used; `_settings_for()` keeps `max_web_queries_per_cycle=0`; Discord remains disabled through default settings. |
| INV-005 | PASS | `--observation-concurrency` is bounded by `max(1, min(value, observation_count))`. |
| INV-006 | PASS | Live output had observation partials while model results were still empty. |
| INV-007 | PASS | Final metrics include prior keys such as `schema_valid_proposals`, `rejected_or_fallback_proposals`, `malformed_json_count`, and `validation_error_count`. |

## Deferred / Not Covered

| ID | Reason | Follow-up |
| --- | --- | --- |
| None | All requested criteria were covered. | None |

## Residual Risks

None

## Follow-up TODOs

None
