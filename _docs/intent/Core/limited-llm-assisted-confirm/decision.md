---
title: "Decision: Limited LLM Assisted Confirm"
status: active
draft_status: n/a
created_at: 2026-06-05
updated_at: 2026-06-05
references:
  - "_docs/plan/Core/limited-llm-assisted-confirm/plan.md"
  - "_docs/qa/Core/limited-llm-assisted-confirm/test-plan.md"
  - "_docs/intent/Core/llm-assisted-readiness-gate/decision.md"
  - "_docs/qa/Core/deepseek-digest-primary-candidate/verification.md"
related_issues: []
related_prs: []
---

# Decision: Limited LLM Assisted Confirm

## Context

The readiness gate allows future limited assisted-mode design, but it does not justify broad LLM adoption. DeepSeek is now the primary live evaluation candidate, and prompt/schema hardening has produced stable structured proposal evidence. The next safe implementation step is a confirm-only assisted path.

The user requested implementation with two conditions:

- record intent for the limited implementation;
- add an Inbox follow-up TODO saying this should be confirmed, observed, and reconsidered later.

## Decision

Implement `llm_assisted` as `assisted-confirm` only.

In this mode, the final digest decision may use the LLM proposal only when the local gate accepts it. The gate accepts only deterministic-agreeing `memory_candidate` or `discard` proposals that are schema-valid, non-fallback, normalized `should_apply=true`, and raw-response-safe.

All disagreement and all non-memory/discard routes remain deterministic.

## Alternatives

- **Broad LLM override**: rejected because current evidence proves structured stability, not general final-decision superiority.
- **Keep `llm_assisted` shadow-only**: rejected because the readiness gate now permits a limited confirm implementation.
- **Auto-adopt concern/action proposals**: rejected because their failure cost is higher and they need separate review or queue design.

## Rationale

This gate tests active assisted plumbing while keeping the behavioral blast radius small. It lets the system record an accepted assisted proposal when the model and deterministic route already agree, without allowing the model to create new concerns, actions, or overrides.

## Consequences / Impact

- `llm_assisted` becomes meaningfully different from `llm_shadow` only for gate-accepted memory/discard confirmations.
- Default runtime remains deterministic.
- Metadata gains assisted gate status and reasons.
- Future relaxation remains a separate observation and design task.

## Quality Implications

- Local validation remains the final gate.
- Raw provider text must not be persisted.
- Action and concern adoption remain blocked.
- The implementation must be easy to audit through digest metadata.

## Intent-derived Invariants

- INV-001: Default `AGENT_DIGEST_DECIDER` remains deterministic.
- INV-002: `llm_assisted` accepts only `memory_candidate` or `discard`.
- INV-003: Accepted assisted proposal must agree with deterministic disposition.
- INV-004: Accepted assisted proposal must have normalized `should_apply=true`.
- INV-005: Provider, JSON, schema, unsafe, fallback, disagreement, concern, action, and no-op cases remain deterministic.
- INV-006: Raw response text is not persisted.
- INV-007: Future relaxation is not implemented in this task.

## Rollback / Follow-ups

Rollback is to unset `AGENT_DIGEST_DECIDER` or set it to `deterministic`. The Inbox follow-up captures the need to confirm, observe, and reconsider this gate before relaxing it.
