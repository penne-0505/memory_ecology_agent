---
title: "DeepSeek Digest Primary Candidate Decision"
status: active
draft_status: n/a
created_at: 2026-06-03
updated_at: 2026-06-03
references:
  - "_docs/plan/Core/deepseek-digest-primary-candidate/plan.md"
  - "_docs/qa/Core/deepseek-digest-primary-candidate/test-plan.md"
  - "_docs/qa/Core/deepseek-digest-primary-candidate/verification.md"
  - "_docs/intent/Core/openrouter-structured-digest-proposals/decision.md"
  - "_docs/qa/Core/openrouter-structured-digest-proposals/verification.md"
related_issues: []
related_prs: []
---

## Context

Three qwen structured shadow runs are clean after OpenRouter structured-output payload hardening and `related_concern_ids` prompt hardening. qwen is therefore a verified live evaluation baseline, but the next question is whether `deepseek/deepseek-v4-pro` should replace it as the primary candidate for future live digest proposal evaluation.

Older DeepSeek evidence was mixed: an earlier prompt-only live shadow improved to `15/16` schema-valid after prompt v3, but one schema validation failure remained. That evidence predates the current OpenRouter structured-output gate and should not be treated as current structured-output evidence.

## Decision

Evaluate DeepSeek with the same OpenRouter structured-output gate as qwen. Use a staged threshold: run one evaluation first; if it is clean, run two more. Only three clean runs authorize switching the evaluation runner primary candidate/default from qwen to DeepSeek.

## Alternatives

- **Switch immediately based on older DeepSeek evidence**: rejected because the older evidence was not from the current structured-output gate.
- **Keep qwen as primary without testing DeepSeek**: deferred because qwen is clean but the user requested a DeepSeek replacement evaluation.
- **Change production digest behavior after clean evidence**: rejected because this task only chooses the primary candidate for live evaluation, not assisted production adoption.

## Rationale

The staged gate prevents one favorable run from being overinterpreted. Matching the qwen payload isolates model behavior from payload drift. Keeping qwen as fallback/baseline preserves a verified comparison point even if DeepSeek becomes the default live evaluation candidate.

## Consequences / Impact

- Clean DeepSeek evidence can change the evaluation runner default model.
- qwen remains documented as verified fallback/baseline.
- Failures route to evidence collection or hardening rather than adoption.
- `llm_assisted` and production final digest decisions remain unchanged.

## Quality Implications

- Raw model responses remain non-persisted.
- Provider supported-parameter evidence must be explicit.
- Local Pydantic validation remains authoritative.
- Reasoning-related adjustments are allowed only when supported-parameter or artifact evidence shows they are necessary.

## Intent-derived Invariants

- INV-001: The production final digest decision path remains deterministic unless explicitly configured otherwise outside this task.
- INV-002: `AGENT_DIGEST_DECIDER` default remains `deterministic`.
- INV-003: `llm_assisted` is not implemented, enabled, or treated as complete.
- INV-004: Raw provider responses and credential values are not persisted or printed.
- INV-005: DeepSeek uses the qwen clean-run structured payload unless evidence requires a minimal supported-parameter adjustment.
- INV-006: Pydantic validation remains the final gate for `LLMDigestProposal`.
- INV-007: The primary candidate/default changes only after three clean DeepSeek runs.
- INV-008: qwen remains recorded as a verified fallback/baseline if DeepSeek becomes primary.

## Gate Outcomes

- `GO`: Three clean DeepSeek runs; switch live evaluation primary candidate/default to DeepSeek.
- `RETURN_TO_EVIDENCE`: Live execution is blocked, credentials are absent, or sample count is insufficient.
- `RETURN_TO_HARDENING`: DeepSeek has provider/schema/validation issues that appear diagnosable.
- `NO_GO`: DeepSeek fails the gate in a way that makes it worse than the verified qwen baseline for this role.
