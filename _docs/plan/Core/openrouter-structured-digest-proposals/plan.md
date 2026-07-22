---
title: "Plan: OpenRouter Structured Digest Proposals"
status: active
draft_status: n/a
created_at: 2026-06-03
updated_at: 2026-06-03
references:
  - "_docs/intent/Core/openrouter-structured-digest-proposals/decision.md"
  - "_docs/qa/Core/openrouter-structured-digest-proposals/test-plan.md"
  - "_docs/qa/Core/openrouter-structured-digest-proposals/verification.md"
  - "_docs/qa/Core/qwen-digest-shadow-evidence/verification.md"
  - "_docs/intent/Core/llm-assisted-readiness-gate/decision.md"
related_issues: []
related_prs: []
---

## Overview

Add provider-native structured output to the digest proposal generation path for OpenRouter shadow evaluation only. The change tests whether qwen's persistent schema validation fallback is caused by prompt-only JSON instruction rather than model capability.

## Scope

- Pass `response_format: { type: "json_schema", ... }` for `LLMDigestProposal` when digest proposals use OpenRouter.
- Pass OpenRouter provider routing preference `provider.require_parameters=true` so requests are not silently routed to providers that ignore required structured-output parameters.
- Keep prompt-only parsing available for non-OpenRouter providers and explicit test doubles.
- Add evaluation artifact metadata showing whether structured output and required parameters were enabled.
- Preserve raw response non-persistence and deterministic final digest decisions.

## Non-Goals

- Do not change the production final digest decision path.
- Do not change the default `AGENT_DIGEST_DECIDER`.
- Do not implement or enable `llm_assisted`.
- Do not change Discord, Web search, or raw response persistence behavior.
- Do not store raw LLM response text in artifacts.

## Requirements

- **Functional**: OpenRouter digest proposal calls include `response_format.type=json_schema` with the `LLMDigestProposal` schema.
- **Functional**: OpenRouter digest proposal calls include `provider.require_parameters=true`.
- **Functional**: Non-OpenRouter providers do not receive OpenRouter-specific structured-output payload.
- **Safety**: Pydantic validation remains the final schema gate after provider-native structured output.
- **Evidence**: Runner artifacts include `structured_output_enabled` and `provider_require_parameters`.

## Tasks

- Add a reusable OpenRouter structured-output payload helper in the LLM adapter.
- Wire that helper into the digest proposal request path only for OpenRouter.
- Add focused tests for payload shape, OpenRouter-only routing, prompt-only fallback, and final Pydantic gate.
- Add runner metadata and tests for evaluation artifact visibility.
- Run focused tests, docs validation, and one live qwen shadow evaluation.

## QA Plan

- QA document: `_docs/qa/Core/openrouter-structured-digest-proposals/test-plan.md`
- Risk level: Medium
- Test strategy:
  - Unit: payload shape and provider-specific routing.
  - Integration: digest decider persistence remains deterministic and schema-gated.
  - Artifact review: live runner metadata and raw response non-persistence.
  - Validator: `./scripts/check-docs.sh`.

## Deployment / Rollout

No production rollout. The change affects the optional OpenRouter digest proposal generation path used by `llm_shadow` evaluation. Final decisions remain deterministic.

## Current Verification Status

Verification is `PASS` for the structured-output prompt-hardening probe: the payload is implemented, tests pass, qwen routing works with `max_tokens`, and the targeted `related_concern_ids.0 | int_parsing` validation aggregate disappeared in the one requested full run. This is readiness prerequisite evidence only; it does not make `llm_assisted` readiness PASS.
