---
title: "QA Verification: LLM Digest Prompt Hardening"
status: active
draft_status: n/a
qa_status: partial
risk: Medium
created_at: 2026-06-02
updated_at: 2026-06-02
references:
  - "_docs/intent/Core/llm-digest-prompt-hardening/decision.md"
  - "_docs/plan/Core/llm-digest-prompt-hardening/plan.md"
  - "_docs/qa/Core/llm-digest-prompt-hardening/test-plan.md"
  - "_evals/reports/llm_digest_proposal_quality_2026-06-02.md"
related_issues: []
related_prs: []
---

# QA Verification: `LLM Digest Prompt Hardening`

## Summary

The digest proposal prompt was hardened to `digest_decision_llm.v3`. The new rubric is shorter, stricter, JSON-only, and explicitly distinguishes unresolved concerns from stable memories. Runtime now stores the model's `should_apply` separately and overwrites persisted `should_apply` with deterministic normalization. Runtime final digest decisions remain deterministic.

## Verification Verdict

Verdict: PARTIAL

Prompt/rubric hardening, deterministic `should_apply` normalization, evaluation metrics, prompt boundary tests, regression tests, offline PoC verification, offline quality evaluation rerun, and live OpenRouter / `deepseek/deepseek-v4-pro` shadow evaluation are verified. The result is PARTIAL because live schema adherence improved but is not perfect, so this must remain shadow-only.

## Commands Run

```bash
date +%F
```

Result:

```text
2026-06-02
```

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_digest_decider.py
```

Result:

```text
10 passed in 0.24s
```

```bash
uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/evaluate_llm_digest_proposals.py
```

Result:

```text
/home/penne/dev/active/memory_ecology_agent/_evals/reports/llm_digest_proposal_quality_2026-06-02.md
```

```bash
AGENT_LLM_PROVIDER=openrouter AGENT_LLM_MODEL=deepseek/deepseek-v4-pro AGENT_DIGEST_DECIDER=llm_shadow AGENT_MAX_WEB_QUERIES=0 uv run --python /home/penne/.local/bin/python3.12 python - <<'PY'
```

Result:

```text
schema_valid_proposals 15
rejected_or_fallback_proposals 1
malformed_json_count 0
validation_error_count 1
action_candidate_count 0
model_should_apply_true_count 3
normalized_should_apply_true_count 3
raw_response_persisted_count 0
core_profile_unchanged True
discord_enabled False
```

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest
```

Result:

```text
76 passed, 1 warning in 1.28s
```

Warning: `discord/player.py` imports deprecated `audioop`; unrelated to this change.

```bash
./scripts/check-docs.sh
```

Initial result before this verification file existed:

```text
ERROR: TODO.md
  - Core-Enhance-14: Verification file does not exist: _docs/qa/Core/llm-digest-prompt-hardening/verification.md
```

Final result after creating this verification file:

```text
Checked 5 files
PASS todo _evals/validator-fixtures/todo/valid/basic.md
PASS qa _evals/validator-fixtures/qa/valid
```

```bash
uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/verify_memory_ecology_poc.py --output /tmp/memory_ecology_digest_prompt_hardening_check.json
```

Result:

```text
PASS: wrote /tmp/memory_ecology_digest_prompt_hardening_check.json
```

Evidence summary from the output JSON:

```text
table_counts.digest_decisions 50
table_counts.response_traces 2
core_profile_locked True
core_profile_unchanged_after_all True
wake_results 3
replay_runs 8
```

## Automated Test Results

| Command / Test | Result | Notes |
| --- | --- | --- |
| `uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_digest_decider.py` | PASS | Prompt boundary tests, digest proposal regression tests, and deterministic `should_apply` normalization tests passed. |
| `uv run --python /home/penne/.local/bin/python3.12 pytest` | PASS | Full suite passed with one unrelated `audioop` deprecation warning from `discord/player.py`. |
| `./scripts/check-docs.sh` | PASS | TODO, doc links, frontmatter, QA, and validator fixtures passed after verification file creation. |
| `uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/evaluate_llm_digest_proposals.py` | PASS | Generated post-hardening offline mock quality report. |
| Live OpenRouter / `deepseek/deepseek-v4-pro` isolated shadow run | PASS | 15/16 schema-valid, 0 malformed JSON, 1 validation error, action_candidate 0, raw response persisted 0. |
| `uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/verify_memory_ecology_poc.py --output /tmp/memory_ecology_digest_prompt_hardening_check.json` | PASS | Isolated PoC verification output was generated. |

## Quality Evaluation Rerun

Report: `_evals/reports/llm_digest_proposal_quality_2026-06-02.md`

Post-hardening offline mock metrics:

| Metric | Value |
| --- | --- |
| total observations | 16 |
| total proposals | 16 |
| schema-valid proposals | 16 |
| rejected/fallback proposals | 0 |
| malformed JSON count | 0 |
| agreement rate | 0.625 |
| proposed distribution | `concern_candidate=4`, `memory_candidate=7`, `discard=4`, `action_candidate=1`, `no_op=0` |
| final distribution | `concern_candidate=8`, `memory_candidate=5`, `discard=3`, `action_candidate=0`, `no_op=0` |
| action candidate count | 1 |
| model_should_apply=true count | 4 |
| normalized should_apply=true count | 0 |
| memory-vs-concern disagreement count | 3 |
| discard-vs-memory disagreement count | 1 |
| raw response persisted count | 0 |
| live v4pro | COMPLETED: OpenRouter / `deepseek/deepseek-v4-pro`, isolated temp root |

The remaining `action_candidate` example is the explicit bounded recommendation fixture. It remains `should_apply=false` and is called out as deterministic-safer in the qualitative section.

Live OpenRouter / `deepseek/deepseek-v4-pro` metrics after v3 hardening:

| Metric | Value |
| --- | --- |
| total observations | 16 |
| total proposals | 16 |
| schema-valid proposals | 15 |
| rejected/fallback proposals | 1 |
| malformed JSON count | 0 |
| validation error count | 1 |
| agreement rate | 0.667 |
| proposed distribution | `concern_candidate=5`, `memory_candidate=6`, `discard=4`, `action_candidate=0`, `no_op=0` |
| action candidate count | 0 |
| model_should_apply=true count | 3 |
| normalized should_apply=true count | 3 |
| raw response persisted count | 0 |
| core_profile unchanged | true |
| Discord enabled | false |

## Acceptance Criteria Coverage

| ID | Status | Evidence |
| --- | --- | --- |
| AC-001 | PASS | Prompt now defines concern, memory, discard, action, and no-op decision boundaries. |
| AC-002 | PASS | Prompt forbids automatic LLM action adoption, downstream mutation, and raw provider response persistence. |
| AC-003 | PASS | Prompt limits `should_apply=true`; runtime overwrites persisted `should_apply` with deterministic normalization and records model value / reason. |
| AC-004 | PASS | Prompt includes confidence calibration bands and risk flag rules. |
| AC-005 | PASS | Evaluation script/report includes required counts, boundary disagreement metrics, confidence by decision, risk flag distribution, and qualitative examples. |
| AC-006 | PASS | Prompt/rubric tests passed; full regression suite passed. |

## Invariant Coverage

| ID | Status | Evidence |
| --- | --- | --- |
| INV-001 | PASS | Prompt includes the automatic adoption ban for LLM `action_candidate`. |
| INV-002 | PASS | Prompt and existing tests preserve no downstream mutation from proposals. |
| INV-003 | PASS | Prompt examples and tests cover stable fact -> memory and true concern -> concern. |
| INV-004 | PASS | Prompt, tests, and live run cover conservative `should_apply`; action example is false and live action_candidate count is zero. |
| INV-005 | PASS | Evaluation report includes memory-vs-concern, discard-vs-memory, action, confidence, risk flag, and qualitative sample sections. |
| INV-006 | PASS | `pytest` and PoC verification passed; final decisions remain deterministic; no real credentials were required. |

## Manual QA Results

| Checklist Item | Result | Notes |
| --- | --- | --- |
| Review prompt diff for scope creep into active adoption | PASS | No active adoption path added. |
| Review quality report for raw response persistence | PASS | `raw_response_persisted_count=0`. |
| Confirm live v4pro handling | PASS | Live run completed in isolated temp root with explicit OpenRouter provider/model and existing credential environment. |

## Deferred / Not Covered

| Item | Reason | Follow-up |
| --- | --- | --- |
| Additional live repetitions | One live run is not enough to justify assisted adoption design. | Keep `llm_shadow` and collect more live runs before any assisted-mode design. |

## Residual Risks

- One live v4pro proposal still failed schema validation, though fallback was safe.
- Normalized true occurred in three low-risk memory/discard cases; this remains proposal metadata only and does not affect final decisions.

## Follow-up TODOs

- Continue collecting live `llm_shadow` metrics before any `llm_assisted` design.

## Verification Verdict Detail

Verdict: PARTIAL

The task can be accepted as prompt/rubric and deterministic normalization hardening with a shadow-only boundary. Recommendation: `KEEP_SHADOW_AND_COLLECT_MORE`. It must not be treated as evidence for active `llm_assisted` adoption.
