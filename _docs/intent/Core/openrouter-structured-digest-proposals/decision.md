---
title: "OpenRouter Structured Digest Proposals Decision"
status: active
draft_status: n/a
created_at: 2026-06-03
updated_at: 2026-06-03
references:
  - "_docs/plan/Core/openrouter-structured-digest-proposals/plan.md"
  - "_docs/qa/Core/openrouter-structured-digest-proposals/test-plan.md"
  - "_docs/qa/Core/openrouter-structured-digest-proposals/verification.md"
  - "_docs/qa/Core/qwen-digest-shadow-evidence/verification.md"
  - "_docs/intent/Core/llm-assisted-readiness-gate/decision.md"
related_issues: []
related_prs: []
---

## Context

Repeated qwen shadow evaluation showed stable malformed JSON behavior but persistent schema validation fallback: previous qwen evidence averaged schema-valid `11/16`, fallback `5/16`, malformed JSON `0`, and validation error `5/16`, with a validation-error range of `4-6/16`.

The primary hypothesis is that prompt-only JSON instruction plus local Pydantic validation is under-constraining the provider response. OpenRouter supports provider-native structured outputs through `response_format.type=json_schema`, and provider routing can require support for requested parameters.

## Decision

Use OpenRouter provider-native structured output for digest proposal generation in the OpenRouter path only. Continue to treat Pydantic validation as the final gate and keep the prompt-only path for providers/configurations that do not use OpenRouter structured outputs.

## Alternatives

- **Prompt hardening only**: deferred because it would not test the provider-native structured-output hypothesis.
- **Apply structured output to all providers**: rejected because provider support and parameter names differ.
- **Move to `llm_assisted` after adding structured output**: rejected because this task produces one piece of readiness evidence, not an adoption verdict.

## Rationale

The change isolates the main uncertainty: whether schema fallback drops when OpenRouter enforces the digest proposal schema upstream. `provider.require_parameters=true` avoids a misleading pass caused by routing to a provider that ignores `response_format`.

## Consequences / Impact

- OpenRouter shadow evaluation should produce artifacts that clearly state structured-output status.
- Provider-side unsupported-parameter errors become meaningful evaluation evidence instead of silent prompt-only behavior.
- Production final digest decisions remain deterministic.
- `llm_assisted` readiness remains unproven until repeated evidence and a separate gate support it.

## Quality Implications

- Raw provider response text must not be persisted.
- Structured-output metadata must be visible in live artifacts.
- Schema validation must not be weakened because provider-native output is not a substitute for local validation.
- OpenRouter-specific payload must not affect OpenAI, Claude, Gemini, mock, or deterministic paths.

## Intent-derived Invariants

- INV-001: Deterministic final digest decisions remain unchanged.
- INV-002: `AGENT_DIGEST_DECIDER` default remains deterministic.
- INV-003: `llm_assisted` is not implemented or enabled by this change.
- INV-004: Raw LLM response text is not persisted in DB rows or evaluation artifacts.
- INV-005: Pydantic validation remains the final acceptance gate for `LLMDigestProposal`.
- INV-006: OpenRouter receives `response_format.type=json_schema` and `provider.require_parameters=true`; non-OpenRouter providers do not.
- INV-007: Structured-output evidence is treated as a readiness prerequisite, not a readiness PASS.

## Rollback / Follow-ups

If OpenRouter rejects structured output for the selected qwen route, record `PARTIAL` evidence and either refine provider/model selection or return to prompt/schema hardening. If validation errors remain near `4-6/16`, use the sanitized failure aggregates and live metrics to decide the next hardening step before any assisted-mode work.

## Verification Update

Current structured qwen evidence is `PASS` for the targeted prompt-hardening probe: `max_tokens` resolves the provider-routing confound, and the minimal `related_concern_ids` prompt contract produced schema-valid `16/16`, validation error `0/16`, provider error `0`, malformed JSON `0`, raw response persisted `0`, and validation aggregate `[]` in the one requested full run. This remains readiness prerequisite evidence, not an active `llm_assisted` adoption decision.
