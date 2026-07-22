---
title: "QA Verification: LLM Assisted Readiness Gate"
status: active
draft_status: n/a
qa_status: verified
risk: Medium
created_at: 2026-06-03
updated_at: 2026-06-03
references:
  - "_docs/intent/Core/llm-assisted-readiness-gate/decision.md"
  - "_docs/plan/Core/llm-assisted-readiness-gate/plan.md"
  - "_docs/qa/Core/llm-assisted-readiness-gate/test-plan.md"
  - "_evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run1.md"
  - "_evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run2.md"
  - "_evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run3.md"
related_issues: []
related_prs: []
---

# QA Verification: `LLM Assisted Readiness Gate`

## Summary

The limited `llm_assisted` readiness gate is defined without implementing or enabling `llm_assisted`.

The gate incorporates two evidence layers:

- Repeated qwen shadow evidence from `Core-Test-17`: no malformed JSON, no provider errors, raw response persisted `0`, but validation errors `4-6/16`, fallback `4-6/16`, and one `action_candidate` in each run.
- OpenRouter structured-output / prompt-hardening evidence: `max_tokens` resolved the provider-parameter confound, and three prompt-hardened qwen structured runs produced schema-valid `16/16`, validation error `0/16`, malformed JSON `0`, provider error `0`, raw response persisted `0`, validation aggregate `[]`, and normalized `should_apply=true` `0` in every run.

Current gate decision: `GO` to a future limited assisted-mode design task. This is not assisted adoption proof and does not implement or enable `llm_assisted`; it only means the evidence gate no longer routes back to additional qwen structured shadow collection. If typed schema failures recur in later evidence, return to prompt/schema hardening.

## Verification Verdict

Verdict: PASS

The gate is documented, conservative, and now backed by three clean qwen structured runs. No active adoption code or runtime boundary changes were made.

## Commands Run

```bash
date '+%Y-%m-%d %H:%M:%S %Z (%z)'
```

Result:

```text
2026-06-03 16:14:14 JST (+0900)
```

```bash
AGENT_MAX_WEB_QUERIES=0 AGENT_LLM_PROVIDER=openrouter \
  uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/run_live_digest_model_comparison.py \
    --provider openrouter \
    --model qwen/qwen3.6-plus \
    --observation-concurrency 4 \
    --output-json _evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run2.json \
    --output-md _evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run2.md
```

Result:

```text
_evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run2.json
_evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run2.md
```

```bash
AGENT_MAX_WEB_QUERIES=0 AGENT_LLM_PROVIDER=openrouter \
  uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/run_live_digest_model_comparison.py \
    --provider openrouter \
    --model qwen/qwen3.6-plus \
    --observation-concurrency 4 \
    --output-json _evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run3.json \
    --output-md _evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run3.md
```

Result:

```text
_evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run3.json
_evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run3.md
```

```bash
./scripts/check-docs.sh
```

Result:

```text
PASS
```

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_live_digest_runner.py tests/test_digest_decider.py tests/test_openrouter_structured_output_probe.py -q
```

Result:

```text
30 passed
```

## Automated Test Results

| Command / Test | Result | Notes |
| --- | --- | --- |
| `./scripts/check-docs.sh` | PASS | TODO, QA, frontmatter, links, and validator fixtures passed. |
| `pytest tests/test_live_digest_runner.py tests/test_digest_decider.py tests/test_openrouter_structured_output_probe.py -q` | PASS | `30 passed`; runner artifact handling, decision payload boundaries, and structured-output probe helpers remain green. |

## Manual QA Results

| Checklist Item | Result | Notes |
| --- | --- | --- |
| Read repeated qwen evidence | PASS | `_docs/qa/Core/qwen-digest-shadow-evidence/verification.md` records three runs with validation errors `4-6/16` and recommendation `PROMPT_SCHEMA_HARDENING_BEFORE_ASSISTED`. |
| Read structured qwen evidence | PASS | Three prompt-hardened qwen structured artifacts now record schema-valid `16/16`, validation error `0/16`, provider error `0`, malformed JSON `0`, raw response persisted `0`, aggregate `[]`. |
| Run two additional structured qwen shadows | PASS | run2 and run3 were created with `AGENT_MAX_WEB_QUERIES=0`, `AGENT_LLM_PROVIDER=openrouter`, `qwen/qwen3.6-plus`, and `--observation-concurrency 4`. |
| No active adoption | PASS | Only documentation, TODO metadata, and evaluation artifacts were changed for this task. |
| Boundary review | PASS | Gate explicitly preserves production final digest decision path, `AGENT_DIGEST_DECIDER` default, Discord/Web search behavior, Pydantic validation, and raw response non-persistence. |

## Structured Qwen Evidence

| Run | Artifact | Schema-valid | Fallback | Malformed JSON | Validation errors | Provider errors | Raw persisted | Validation aggregate | model / normalized `should_apply=true` | Action candidates | Elapsed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| run1 | `_evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run1.json` | `16/16` | `0/16` | `0` | `0` | `0` | `0` | `[]` | `0 / 0` | `1` | `121.5s` |
| run2 | `_evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run2.json` | `16/16` | `0/16` | `0` | `0` | `0` | `0` | `[]` | `0 / 0` | `1` | `115.8s` |
| run3 | `_evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run3.json` | `16/16` | `0/16` | `0` | `0` | `0` | `0` | `[]` | `0 / 0` | `1` | `124.1s` |

All three runs recorded `structured_output_enabled=true`, `structured_outputs=true`, `provider_require_parameters=true`, token parameter `max_tokens`, Web search disabled, Discord disabled, proposal-only shadow mode, and no raw provider response persistence.

The repeated `action_candidate_count=1` signal is not a readiness blocker here because `model_should_apply_true_count=0`, `normalized_should_apply_true_count=0`, final deterministic decisions do not auto-adopt action candidates, and the gate continues to exclude action auto-adoption from any future limited design.

## Readiness Gate Summary

| Route | Condition |
| --- | --- |
| Go to limited assisted design | At least three credentialed qwen structured `llm_shadow` runs reproduce clean structured metadata, schema-valid `16/16`, fallback `0`, provider error `0`, malformed JSON `0`, raw response persisted `0`, validation aggregate `[]`, conservative `should_apply`, no safety failures, and no action auto-adoption. |
| No-go / stop | Any attempt to change production final digest behavior, default decider, Discord/Web search, Pydantic gate, raw response persistence, or action/safety boundary; ambiguous provider/config evidence; unsafe output; or permissive `should_apply`. |
| Return to additional shadow evidence | The only gap is sample size. |
| Return to prompt/schema hardening | Recurring sanitized validation aggregate, schema fallback above `0`, `action_candidate` boundary confusion, or over-permissive `should_apply`. |
| Return to provider/config diagnostics | Provider errors, unsupported parameter errors, or missing structured-output metadata recur. |

## Acceptance Criteria Coverage

| ID | Status | Evidence |
| --- | --- | --- |
| AC-001 | PASS | Go / no-go / return-to-evidence conditions are documented in intent and summarized here without implementing `llm_assisted`. |
| AC-002 | PASS | Gate covers schema-valid rate, fallback frequency, action candidate handling, `should_apply`, safety boundaries, provider/config diagnostics, and run-to-run variance. |
| AC-003 | PASS | Current state routes to future limited assisted-mode design consideration; recurring typed schema failures still route to prompt/schema hardening. |

## Invariant Coverage

| ID | Status | Evidence |
| --- | --- | --- |
| INV-001 | PASS | No `llm_assisted` implementation or enabling was added. |
| INV-002 | PASS | Gate requires repeated structured qwen evidence and now has three clean runs. |
| INV-003 | PASS | Safety failures are explicit no-go conditions. |
| INV-004 | PASS | `action_candidate` is excluded from auto-adoption. |
| INV-005 | PASS | Gate keeps Pydantic as the final acceptance gate. |
| INV-006 | PASS | Gate does not require or allow raw provider response persistence. |
| INV-007 | PASS | Structured-output success is recorded as design-readiness evidence only, not active adoption proof. |

## Deferred / Not Covered

| ID | Reason | Follow-up |
| --- | --- | --- |
| `llm_assisted` implementation | Out of scope for this evidence task. | Create a separate limited assisted-mode design / implementation task if the user chooses to proceed. |

## Residual Risks

None

## Follow-up TODOs

- None. `Core-Test-19` evidence collection is complete and removed from active TODO state after this PASS verification update.
