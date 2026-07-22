---
title: "LLM Assisted Readiness Gate Decision"
status: active
draft_status: n/a
created_at: 2026-06-03
updated_at: 2026-06-03
references:
  - "_docs/plan/Core/llm-assisted-readiness-gate/plan.md"
  - "_docs/qa/Core/llm-assisted-readiness-gate/test-plan.md"
  - "_docs/qa/Core/llm-assisted-readiness-gate/verification.md"
  - "_docs/intent/Core/qwen-digest-shadow-evidence/decision.md"
  - "_docs/qa/Core/qwen-digest-shadow-evidence/verification.md"
  - "_docs/qa/Core/openrouter-structured-digest-proposals/verification.md"
related_issues: []
related_prs: []
---

## Context

Digest proposals affect whether observations become concerns, memories, discards, or actions. That makes assisted adoption higher risk than observation extraction. Current evidence supports shadow evaluation, but not active adoption.

The relevant evidence now has two layers:

- Repeated qwen shadow evidence: three `qwen/qwen3.6-plus` runs produced no malformed JSON, no provider errors, and no raw response persistence, but still had validation errors `4-6/16`, fallback `4-6/16`, and one `action_candidate` in every run.
- Structured-output prompt-hardening evidence: OpenRouter qwen with `max_tokens`, `response_format.type=json_schema`, `structured_outputs=true`, and `provider.require_parameters=true` removed the provider-parameter confound. After minimal `related_concern_ids` prompt hardening, three full runs produced schema-valid `16/16`, validation error `0/16`, malformed JSON `0`, provider error `0`, raw response persisted `0`, validation aggregate `[]`, and normalized `should_apply=true` `0` in every run.

The second layer is a readiness prerequisite. It now has enough repeated clean evidence to permit a future limited assisted-mode design task, but it still does not implement or authorize production final decision changes in this task.

## Decision

Do not implement `llm_assisted` in this task. Define this limited readiness gate:

### Go: proceed only to limited assisted-mode design

Proceed to a future limited `llm_assisted` design task only when all of these are true:

- At least three credentialed `qwen/qwen3.6-plus` structured-output `llm_shadow` runs, using isolated temp roots with Web search disabled and Discord disabled, reproduce stable provider behavior.
- Each run records `structured_output_enabled=true`, `provider_require_parameters=true`, token parameter `max_tokens`, provider errors `0`, malformed JSON `0`, raw response persisted `0`, and sanitized validation aggregate `[]`.
- Schema-valid proposals are `16/16` in each run, or any exception is explicitly unrelated to the proposal schema and does not create fallback adoption risk.
- Fallback caused by provider, JSON, schema validation, orchestration, timeout, or safety failure is `0`.
- `action_candidate` remains outside the assisted adoption scope. No future limited design may auto-adopt `action_candidate`; action proposals require deterministic/manual handling.
- `should_apply` remains conservative: normalized apply is allowed only for schema-valid, safe, non-action proposals that agree with deterministic disposition and pass the local Pydantic gate.
- Run-to-run variance does not regress toward the earlier qwen range: no repeat of validation errors `4-6/16`, no recurring field/type aggregate, and no sudden increase in fallback or unsafe proposal behavior.
- The future design explicitly preserves production final decision boundaries until a separate implementation task and verification exist.

### No-go: stop assisted-mode work

Stop any assisted-mode work if any of these occur:

- The task starts changing production final digest decision behavior, `AGENT_DIGEST_DECIDER` default, Discord/Web search behavior, raw response persistence, or the Pydantic validation gate.
- Provider credentials, routing, or parameter support are ambiguous enough that the evidence cannot be attributed to qwen structured-output behavior.
- Raw provider response text or secrets would need to be persisted to explain failures.
- Safety failures appear, including unsafe core/self-model claims, unsupported actions, or model output that attempts to bypass deterministic/manual boundaries.
- `action_candidate` is proposed for auto-adoption, or normalized `should_apply` becomes permissive for disagreement, unsafe, invalid, or action proposals.

### Return to evidence or hardening

Return to additional shadow evidence when the only gap is sample size.

Return to prompt/schema hardening when failures are repeated or classifiable: for example, a recurring `validation_failure_aggregate`, schema fallback above `0`, action-boundary confusion, or over-permissive `should_apply`.

Return to provider/config diagnostics when provider errors, unsupported parameter errors, or missing structured-output metadata recur.

Current state: `GO` to a future limited assisted-mode design task. Do not proceed to `llm_assisted` implementation in this task. The three clean prompt-hardened structured runs satisfy the evidence gate for design consideration only; production final digest decisions, default decider behavior, Discord/Web search, Pydantic validation, and raw response persistence remain unchanged.

## Alternatives

- **Implement limited assisted immediately**: rejected because readiness is not established.
- **Never consider assisted mode**: rejected because qwen may still prove useful under conservative gates.
- **Keep collecting evidence forever**: rejected because the gate now has three clean structured runs and should drive a scoped next-step decision.
- **Treat the 16/16 structured run as immediate readiness**: rejected because it is a single post-hardening run and does not prove run-to-run stability.

## Rationale

A readiness gate prevents accidental promotion from shadow evidence to active behavior. It also gives prompt/schema hardening a clear target if qwen fails the gate.

The main positive signal is that three structured qwen runs removed the `related_concern_ids.0 | int_parsing` aggregate without relaxing Pydantic validation. Earlier repeated qwen runs still matter as cautionary background because they showed validation fallback `4-6/16`, so the gate only authorizes a future limited design task, not active assisted adoption.

## Consequences / Impact

- Adds a decision checkpoint before future assisted-mode implementation.
- Keeps production runtime unchanged.
- Defers assisted adoption until a separate implementation task defines and verifies limited behavior.
- Routes recurring typed-schema failures to prompt/schema hardening instead of schema relaxation.

## Quality Implications

- The gate must preserve safety boundaries around actions, core/self model, Discord, Web search, and final deterministic decisions.
- The gate must distinguish model quality from provider/config failure.
- The gate must preserve strict local validation even when provider-native structured output is enabled.

## Intent-derived Invariants

- INV-001: This task does not implement or enable `llm_assisted`.
- INV-002: Gate criteria are based on repeated qwen evidence plus three clean structured-output prerequisite runs, not a single clean run.
- INV-003: Safety failures block readiness.
- INV-004: `action_candidate` is never auto-adopted from LLM proposal alone.
- INV-005: Pydantic validation remains the final acceptance gate.
- INV-006: Raw provider responses are not persisted for readiness diagnostics.
- INV-007: Structured-output success is not treated as active adoption proof.

## Rollback / Follow-ups

The gate is defined and current evidence routes future work to limited assisted-mode design consideration. If recurring schema failures reappear in later evidence, return to prompt/schema hardening rather than assisted adoption.
