---
title: "Plan: Limited LLM Assisted Confirm"
status: active
draft_status: n/a
created_at: 2026-06-05
updated_at: 2026-06-05
references:
  - "_docs/intent/Core/limited-llm-assisted-confirm/decision.md"
  - "_docs/qa/Core/limited-llm-assisted-confirm/test-plan.md"
  - "_docs/intent/Core/llm-assisted-readiness-gate/decision.md"
  - "_docs/qa/Core/deepseek-digest-primary-candidate/verification.md"
related_issues: []
related_prs: []
---

# Plan: Limited LLM Assisted Confirm

## Overview

Implement the first active `llm_assisted` behavior as a conservative confirm gate. The LLM proposal may be accepted only when it agrees with deterministic digest routing and satisfies local safety gates. Otherwise the final decision remains deterministic.

## Scope

- Add local assisted gate logic for `AGENT_DIGEST_DECIDER=llm_assisted`.
- Allow assisted acceptance only for `memory_candidate` and `discard`.
- Preserve deterministic fallback for all other cases.
- Record assisted gate result and reasons in digest decision metadata.
- Keep proposal persistence and raw response safety unchanged.
- Keep the Inbox follow-up note for later observation: "確認・観察して検討してみる".

## Non-Goals

- Do not implement broad LLM override.
- Do not auto-adopt `concern_candidate`, `action_candidate`, or `no_op`.
- Do not change `AGENT_DIGEST_DECIDER` default.
- Do not change Pydantic validation, raw response persistence, Discord, or Web search behavior.
- Do not decide future gate relaxation in this task.

## Requirements

- The deterministic decision is computed first.
- The LLM proposal is requested and persisted as before.
- The assisted gate can accept only when:
  - proposal is schema-valid,
  - proposal does not fallback,
  - proposal decision is `memory_candidate` or `discard`,
  - proposal agrees with deterministic disposition,
  - normalized `should_apply=true`,
  - raw response was not persisted.
- Rejection must leave final digest behavior deterministic.
- Metadata must explain the gate outcome.

## Tasks

1. Add gate result fields to digest proposal result.
2. Implement assisted gate rules.
3. Use the gate in wake-cycle final decision selection.
4. Add focused tests for accept, reject, and boundary behavior.
5. Update verification after tests.

## QA Plan

- Focused unit/regression tests for gate acceptance and rejection.
- Wake-cycle test showing assisted accepted metadata while deterministic default remains unchanged.
- Docs check.
- Full pytest if feasible.

## Deployment / Rollout

No automatic rollout. The mode remains opt-in through `AGENT_DIGEST_DECIDER=llm_assisted`. Default remains deterministic.
