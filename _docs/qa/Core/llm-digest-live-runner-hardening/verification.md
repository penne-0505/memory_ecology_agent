---
title: "QA Verification: LLM Digest Live Runner Hardening"
status: active
draft_status: n/a
qa_status: verified
risk: Medium
created_at: 2026-06-02
updated_at: 2026-06-03
references:
  - "_docs/intent/Core/llm-digest-live-runner-hardening/decision.md"
  - "_docs/plan/Core/llm-digest-live-runner-hardening/plan.md"
  - "_docs/qa/Core/llm-digest-live-runner-hardening/test-plan.md"
  - "_evals/scripts/run_live_digest_model_comparison.py"
related_issues: []
related_prs: []
---

# QA Verification: `LLM Digest Live Runner Hardening`

## Summary

Live digest model comparison runner was added as an evaluation-only script. It accepts multiple models, runs a small safe batch first, moves to bounded concurrency only when the safe batch does not show severe failures, flushes per-model results, and records classified failure causes without raw provider responses.

2026-06-03 addendum: the runner now supports explicit diagnostic raw capture through `--capture-raw-diagnostics`. Standard JSON / Markdown artifacts and DB proposal rows still do not persist raw provider responses. Diagnostic raw content is written only to a dedicated `.raw.json` artifact and only for failed proposal outputs.

## Verification Verdict

Verdict: PASS

All AC / INV checks for runner implementation hardening are covered by automated tests, mock provider smoke, focused regression tests, DeepSeek diagnostic live probes, docs validation, and diff review. The implementation does not change active adoption or production runtime behavior. This PASS is scoped to runner behavior, safety boundaries, and explicit diagnostic raw-capture separation; live speed improvement remains outside this verification.

## Commands Run

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_live_digest_runner.py tests/test_digest_decider.py tests/test_llm.py -q
```

Result:

```text
42 passed
```

DeepSeek reasoning diagnostic commands:

```bash
env -u AGENT_OPENROUTER_REASONING_EFFORT -u AGENT_OPENROUTER_REASONING_EXCLUDE uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/run_live_digest_model_comparison.py --provider openrouter --model deepseek/deepseek-v4-pro --safe-batch-size 1 --concurrency 1 --observation-concurrency 1 --max-observations 16 --fail-fast-on-safe-batch --capture-raw-diagnostics --output-json _evals/reports/deepseek_reasoning_raw_diagnostic_unspecified_full_2026-06-03.json --output-md _evals/reports/deepseek_reasoning_raw_diagnostic_unspecified_full_2026-06-03.md --raw-diagnostic-json _evals/reports/deepseek_reasoning_raw_diagnostic_unspecified_full_2026-06-03.raw.json
```

```bash
AGENT_OPENROUTER_REASONING_EXCLUDE=true env -u AGENT_OPENROUTER_REASONING_EFFORT uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/run_live_digest_model_comparison.py --provider openrouter --model deepseek/deepseek-v4-pro --safe-batch-size 1 --concurrency 1 --observation-concurrency 4 --max-observations 16 --fail-fast-on-safe-batch --capture-raw-diagnostics --output-json _evals/reports/deepseek_reasoning_raw_diagnostic_exclude_only_full_2026-06-03.json --output-md _evals/reports/deepseek_reasoning_raw_diagnostic_exclude_only_full_2026-06-03.md --raw-diagnostic-json _evals/reports/deepseek_reasoning_raw_diagnostic_exclude_only_full_2026-06-03.raw.json
```

```bash
AGENT_OPENROUTER_REASONING_EFFORT=minimal AGENT_OPENROUTER_REASONING_EXCLUDE=true uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/run_live_digest_model_comparison.py --provider openrouter --model deepseek/deepseek-v4-pro --safe-batch-size 1 --concurrency 1 --observation-concurrency 4 --max-observations 16 --fail-fast-on-safe-batch --capture-raw-diagnostics --output-json _evals/reports/deepseek_reasoning_raw_diagnostic_minimal_exclude_full_2026-06-03.json --output-md _evals/reports/deepseek_reasoning_raw_diagnostic_minimal_exclude_full_2026-06-03.md --raw-diagnostic-json _evals/reports/deepseek_reasoning_raw_diagnostic_minimal_exclude_full_2026-06-03.raw.json
```

```bash
AGENT_OPENROUTER_REASONING_EFFORT=low AGENT_OPENROUTER_REASONING_EXCLUDE=true uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/run_live_digest_model_comparison.py --provider openrouter --model deepseek/deepseek-v4-pro --safe-batch-size 1 --concurrency 1 --observation-concurrency 4 --max-observations 16 --fail-fast-on-safe-batch --capture-raw-diagnostics --output-json _evals/reports/deepseek_reasoning_raw_diagnostic_low_exclude_full_2026-06-03.json --output-md _evals/reports/deepseek_reasoning_raw_diagnostic_low_exclude_full_2026-06-03.md --raw-diagnostic-json _evals/reports/deepseek_reasoning_raw_diagnostic_low_exclude_full_2026-06-03.raw.json
```

Result:

```text
unspecified: schema_valid=14/16, malformed_json=2, diagnostic raw failures=2
exclude-only: schema_valid=16/16, diagnostic raw failures=0
minimal+exclude: schema_valid=16/16, diagnostic raw failures=0
low+exclude: schema_valid=14/16, malformed_json=1, schema_validation=1, diagnostic raw failures=2
All standard artifacts: raw_provider_response_persisted=false
```

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_live_digest_runner.py tests/test_digest_decider.py
```

Result:

```text
14 passed in 0.25s
```

```bash
uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/run_live_digest_model_comparison.py --provider mock --models mock-a,mock-b --safe-batch-size 1 --concurrency 2 --fail-fast-on-safe-batch --output-json /tmp/live_digest_runner_mock.json --output-md /tmp/live_digest_runner_mock.md
```

Result:

```text
/tmp/live_digest_runner_mock.json
/tmp/live_digest_runner_mock.md
```

```bash
python - <<'PY'
```

Result from inspecting `/tmp/live_digest_runner_mock.json`:

```text
{'completed': 1, 'skipped': 1}
{'malformed_json': 16, 'safe_batch_gate': 1}
mock-a safe_batch completed {'malformed_json': 16}
mock-b bounded skipped {'safe_batch_gate': 1}
```

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest
```

Result:

```text
100 passed, 1 warning in 1.53s
```

Warning: `discord/player.py` imports deprecated `audioop`; unrelated to this change.

```bash
./scripts/check-docs.sh
```

Final result:

```text
Checked 5 files
PASS todo _evals/validator-fixtures/todo/valid/basic.md
PASS qa _evals/validator-fixtures/qa/valid
```

## Automated Test Results

| Command / Test | Result | Notes |
| --- | --- | --- |
| `uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_live_digest_runner.py tests/test_digest_decider.py tests/test_llm.py -q` | PASS | Diagnostic writer separation, raw redaction, adapter metadata, and digest decider regressions passed. |
| DeepSeek reasoning raw diagnostic runs | PASS | Dedicated `.raw.json` artifacts captured failed raw content only; standard artifacts kept `raw_provider_response_persisted=false`. |
| `uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_live_digest_runner.py tests/test_digest_decider.py` | PASS | Runner orchestration, failure cause classification, per-model flush, and digest decider regression tests passed. |
| Mock provider runner smoke | PASS | Safe batch classified malformed JSON as severe and skipped remaining model through `safe_batch_gate`. |
| `uv run --python /home/penne/.local/bin/python3.12 pytest` | PASS | Full suite passed with one unrelated Discord `audioop` deprecation warning. |
| `./scripts/check-docs.sh` | PASS | TODO, frontmatter, doc links, QA, and validator fixtures passed. |

## Manual QA Results

| Checklist Item | Result | Notes |
| --- | --- | --- |
| Confirm mock runner writes JSON and Markdown outputs | PASS | `/tmp/live_digest_runner_mock.json` and `/tmp/live_digest_runner_mock.md` were created. |
| Confirm safe batch gate behavior | PASS | `mock-a` completed in `safe_batch`; `mock-b` was skipped in `bounded` with `safe_batch_gate`. |
| Confirm raw provider response and secret values are not printed | PASS | Script printed output paths only; report/JSON contain aggregate metadata and no raw response text. |
| Confirm diagnostic raw capture separation | PASS | `deepseek_reasoning_raw_diagnostic_*_full_2026-06-03.raw.json` is separate from standard artifacts and records failed raw content only. |
| Confirm live provider is optional | PASS | Tests and mock smoke ran without requiring `OPENROUTER_API_KEY`. |

## Acceptance Criteria Coverage

| ID | Status | Evidence |
| --- | --- | --- |
| AC-001 | PASS | `_evals/scripts/run_live_digest_model_comparison.py` accepts `--model` / `--models`; `tests/test_live_digest_runner.py` covers multi-model execution. |
| AC-002 | PASS | `run_models()` runs `safe_batch` first and skips remaining models on severe failure when `--fail-fast-on-safe-batch` is enabled. Severe causes include malformed JSON, schema validation, provider, timeout, orchestration, and safety failures. |
| AC-003 | PASS | `ResultWriter.record()` calls `flush()` per result; test confirms output JSON contains a partial result after the first model. |
| AC-004 | PASS | `classify_failure_causes()` maps JSON decode, schema validation, provider, timeout, orchestration, and safety failures. |
| AC-005 | PASS | Mock runner output reports isolated temp roots, `raw_provider_response_persisted=false`, no credential values, Web disabled, Discord disabled, and deterministic final decisions. |
| AC-006 | PASS | `_evals/reports/deepseek_reasoning_raw_diagnostic_*_full_2026-06-03.raw.json` files are dedicated diagnostic artifacts. Standard JSON/Markdown artifacts do not include raw response text. |

## Invariant Coverage

| ID | Status | Evidence |
| --- | --- | --- |
| INV-001 | PASS | Diff is limited to evaluation scripts, tests, TODO, and docs; runtime default adoption is unchanged. |
| INV-002 | PASS | Output/report omit raw provider response text and credential values; proposal persistence still stores sanitized metadata only. |
| INV-003 | PASS | Test event order confirms safe batch results finish before bounded phase starts. |
| INV-004 | PASS | Writer flush is called on each model result. |
| INV-005 | PASS | Unit test covers expected failure cause categories. |
| INV-006 | PASS | Tests and mock smoke run without `OPENROUTER_API_KEY`; real provider remains optional. |
| INV-007 | PASS | Diagnostic callback defaults to disabled and is only wired by the eval runner when `--capture-raw-diagnostics` is present. DB proposal rows retain `raw_response_persisted=false`; production/default/adoption paths are unchanged. |

## DeepSeek Reasoning Diagnostic Result

| Mode | Schema Valid | Failure Cause | Raw Diagnostic Failures | Cause Seen In Raw |
| --- | --- | --- | --- | --- |
| reasoning unspecified | 14/16 | `malformed_json=2` | 2 | Both failures ended with `finish_reason=length`; one content was partial JSON, one content was empty. Reasoning fields were present in provider message metadata. |
| exclude-only | 16/16 | none | 0 | No failed raw response captured. |
| minimal + exclude | 16/16 | none | 0 | No failed raw response captured. |
| low + exclude | 14/16 | `malformed_json=1`, `schema_validation=1` | 2 | One failure was `evidence_quote:string_too_long`; one was empty content with `finish_reason=length`. No `<think>` text appeared in captured content. |

Interpretation: captured failures do not show chain-of-thought text mixed into JSON content. The stronger signal is token-budget pressure from reasoning tokens causing `finish_reason=length` and empty/partial content, plus one ordinary Pydantic schema violation.

## Deferred / Not Covered

| Item | Reason | Follow-up |
| --- | --- | --- |
| Live speed improvement evidence | Diagnostic reruns were scoped to DeepSeek reasoning failure causes, not throughput benchmarking. | Compare elapsed time and per-model completion behavior in a separate credentialed performance run. |

## Residual Risks

None

## Follow-up TODOs

None required for this scope.

## Verification Verdict Detail

Verdict: PASS

The runner improvement is complete for the requested implementation scope: safe initial parallelism, bounded expansion, per-model flush, clear failure cause classification, explicit diagnostic raw-capture separation, and safety boundaries are implemented and verified. Real-provider speed improvement remains outside the evidence gathered here.
