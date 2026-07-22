---
title: "QA Test Plan: DeepSeek Digest Primary Candidate"
status: active
draft_status: n/a
qa_status: planned
risk: Medium
created_at: 2026-06-03
updated_at: 2026-06-03
references:
  - "_docs/plan/Core/deepseek-digest-primary-candidate/plan.md"
  - "_docs/intent/Core/deepseek-digest-primary-candidate/decision.md"
  - "_docs/qa/Core/deepseek-digest-primary-candidate/verification.md"
related_issues: []
related_prs: []
---

# QA Test Plan: `DeepSeek Digest Primary Candidate`

## Source of Intent

- Request: Evaluate `deepseek/deepseek-v4-pro` as qwen replacement primary candidate for digest proposal live evaluation.
- Plan: `_docs/plan/Core/deepseek-digest-primary-candidate/plan.md`
- Intent: `_docs/intent/Core/deepseek-digest-primary-candidate/decision.md`

## Quality Goal

Determine whether DeepSeek can replace qwen as the primary live evaluation candidate under the same OpenRouter structured shadow gate, without changing production final digest behavior or enabling `llm_assisted`.

## Acceptance Criteria

- AC-001: DeepSeek supported parameters are checked from OpenRouter model metadata without exposing secrets.
- AC-002: DeepSeek run1 uses `max_tokens`, `response_format=json_schema`, `structured_outputs=true`, and `provider.require_parameters=true`.
- AC-003: Additional run2/run3 execute only if run1 is clean.
- AC-004: Primary candidate/default changes only if run1/run2/run3 are all clean.
- AC-005: Production final digest behavior, `AGENT_DIGEST_DECIDER` default, Discord/Web search behavior, Pydantic gate, raw response persistence, and `llm_assisted` remain unchanged.

## Intent-derived Invariants

- INV-001: Final digest decisions remain deterministic by default.
- INV-002: `AGENT_DIGEST_DECIDER` default remains unchanged.
- INV-003: `llm_assisted` is not implemented or enabled.
- INV-004: Raw provider responses and secrets are not persisted or printed.
- INV-005: DeepSeek uses the qwen clean-run payload unless evidence requires a minimal adjustment.
- INV-006: Pydantic validation remains the final acceptance gate.
- INV-007: qwen remains a verified fallback/baseline when DeepSeek becomes primary.

## Risk Assessment

- Risk level: Medium
- Risk rationale: The task affects live provider evaluation defaults and readiness evidence, but not production final behavior.
- Regression risk: Medium, because changing runner defaults can alter future evaluation evidence.
- Data safety risk: Medium, because credentialed provider calls are involved.
- Agent misbehavior risk: Medium, because clean evidence could be incorrectly broadened into assisted adoption.

## Test Strategy

- Metadata check: OpenRouter model metadata for DeepSeek supported parameters.
- Live QA: staged DeepSeek structured shadow runs under isolated temp roots and Web search disabled.
- Artifact review: JSON / Markdown reports for metrics and raw-response non-persistence.
- Diff review: ensure only allowed runner/docs fields change after the gate.
- Automated tests: focused live runner and digest decider tests, then docs validator.

## Test Matrix

| ID | Source | Requirement / Invariant | Test Type | Command / File | Expected Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| AC-001 | TODO | Supported parameters are checked. | metadata | OpenRouter `/api/v1/models` | DeepSeek lists `max_tokens`, `response_format`, and `structured_outputs`; credential value not printed. | planned |
| AC-002 | TODO | Run1 uses qwen clean payload. | live QA | `_evals/scripts/run_live_digest_model_comparison.py` | Artifact metadata shows structured payload, token parameter, and raw persistence flag. | planned |
| AC-003 | TODO | Run2/run3 are gated by run1. | manual QA | verification | Run2/run3 exist only if run1 is clean. | planned |
| AC-004 | TODO | Primary candidate/default changes only after 3 clean runs. | diff review | `_evals/scripts/run_live_digest_model_comparison.py`, docs | `PRIMARY_MODEL` changes only with clean evidence; otherwise remains qwen. | planned |
| AC-005 | TODO | Production/default/assisted boundaries remain unchanged. | diff/test review | `app/config.py`, `app/cognition/digest_decider.py`, docs | No default final path, `llm_assisted`, Pydantic, Discord, Web search, or raw persistence changes. | planned |
| INV-004 | intent | Raw provider response and secrets are absent. | artifact review | JSON / Markdown reports | `raw_provider_response_persisted=false`; no raw model text. | planned |
| INV-006 | intent | Pydantic remains final gate. | unit/diff review | `tests/test_digest_decider.py` | Strict validation tests still pass; implementation unchanged. | planned |
| INV-007 | intent | qwen remains fallback/baseline after switch. | doc review | plan / intent / verification | qwen is recorded as verified fallback/baseline. | planned |

## Manual QA Checklist

- [ ] Confirm `OPENROUTER_API_KEY` presence without printing the secret.
- [ ] Check DeepSeek supported parameters from OpenRouter model metadata.
- [ ] Run DeepSeek structured shadow run1.
- [ ] If run1 is clean, run DeepSeek structured shadow run2/run3.
- [ ] Inspect artifact metrics and validation aggregate.
- [ ] Confirm no raw provider response text is persisted.

## Regression Checklist

- [ ] `uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_live_digest_runner.py tests/test_digest_decider.py tests/test_llm.py tests/test_openrouter_structured_output_probe.py`
- [ ] `./scripts/check-docs.sh`
- [ ] Diff review for production/default/assisted boundaries.

## Out of Scope

- `llm_assisted` implementation or enablement.
- Production final digest behavior changes.
- Discord or Web search behavior changes.
- Raw response persistence.

## Open Questions

- Covered in verification: DeepSeek reasoning behavior affects structured stability enough that `exclude=true` alone, `minimal`, and `low` did not produce clean first-run evidence.
- Covered in verification: the recommended OpenRouter DeepSeek setting for this runner remains `AGENT_OPENROUTER_REASONING_EFFORT=none` and `AGENT_OPENROUTER_REASONING_EXCLUDE=true`.
