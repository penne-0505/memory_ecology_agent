---
title: "QA Test Plan: LLM Assisted Readiness Gate"
status: active
draft_status: n/a
qa_status: planned
risk: Medium
created_at: 2026-06-03
updated_at: 2026-06-03
references:
  - "_docs/intent/Core/llm-assisted-readiness-gate/decision.md"
  - "_docs/plan/Core/llm-assisted-readiness-gate/plan.md"
  - "_docs/qa/Core/llm-assisted-readiness-gate/verification.md"
related_issues: []
related_prs: []
---

# QA Test Plan: `LLM Assisted Readiness Gate`

## Source of Intent

- TODO: `Core-Test-18`; follow-up evidence collection tracked as `Core-Test-19` and completed in this verification update.
- Plan: `_docs/plan/Core/llm-assisted-readiness-gate/plan.md`
- Intent: `_docs/intent/Core/llm-assisted-readiness-gate/decision.md`

## Quality Goal

Define a conservative evidence-backed gate for deciding whether limited `llm_assisted` design can be considered.

## Acceptance Criteria

- AC-001: Go / no-go criteria are documented without implementing `llm_assisted`.
- AC-002: Criteria include schema-valid rate, fallback frequency, action-candidate behavior, `should_apply`, safety boundaries, and run-to-run variance.
- AC-003: If the gate is not met, follow-up work is clearly routed to prompt/schema hardening or more shadow evidence.

## Intent-derived Invariants

- INV-001: No `llm_assisted` implementation or enabling occurs.
- INV-002: Criteria are based on repeated qwen evidence from `Core-Test-17` plus three clean structured-output prerequisite runs, not a single clean run.
- INV-003: Safety failures block readiness.
- INV-004: `action_candidate` is not auto-adopted from LLM proposal alone.
- INV-005: Pydantic validation remains the final acceptance gate.
- INV-006: Raw provider responses are not persisted for readiness diagnostics.
- INV-007: Structured-output success is not treated as active adoption proof.

## Risk Assessment

- Risk level: Medium
- Risk rationale: A bad gate could authorize unsafe future work.
- Regression risk: Low, because this is decision documentation.
- Data safety risk: Low.
- Security / privacy risk: Low.
- UX risk: Low.
- Agent misbehavior risk: Medium, because future agents may treat a weak gate as permission to implement adoption.

## Test Strategy

- Document review: verify criteria are concrete and conservative.
- Diff review: confirm no active adoption code changes.
- Validator / static check: `./scripts/check-docs.sh`.

## Test Matrix

| ID | Source | Requirement / Invariant | Test Type | Command / File | Expected Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| AC-001 | TODO | Go / no-go criteria are documented. | document review | decision / verification | Concrete gate language. | verified |
| AC-002 | TODO | Criteria cover required quality axes. | document review | decision / verification | Required axes present. | verified |
| AC-003 | TODO | Follow-up route is explicit. | document review | decision / verification | GO / hardening / evidence follow-up route named. | verified |
| INV-001 | intent | No assisted implementation. | diff review | app / _evals diff | No active adoption code. | verified |
| INV-002 | intent | Criteria do not rely on a single clean run. | document review | decision / verification | Three clean structured runs are required and now recorded. | verified |
| INV-003 | intent | Safety failures block readiness. | document review | decision / verification | No-go criteria include safety blockers. | verified |
| INV-004 | intent | Action candidates are not auto-adopted. | document review | decision / verification | Gate excludes action auto-adoption. | verified |
| INV-005 | intent | Pydantic remains final gate. | diff/document review | app diff / decision | No schema relaxation; gate requires local validation. | verified |
| INV-006 | intent | Raw provider responses remain non-persistent. | document review | structured verification / decision | Gate keeps raw response persistence out of scope. | verified |
| INV-007 | intent | Structured-output evidence is prerequisite only. | document review | decision / verification | Current state is GO to design consideration, not adoption. | verified |

## Manual QA Checklist

- [x] Read `Core-Test-17` verification before finalizing the gate.
- [x] Read OpenRouter structured-output verification and current prompt-hardened qwen evidence.
- [x] Run two additional qwen structured shadow evaluations under the same OpenRouter conditions.
- [x] Confirm no active adoption code was added.

## Regression Checklist

- [x] `./scripts/check-docs.sh`

## Out of Scope

- Implementing `llm_assisted`.
- Changing production final digest decision behavior, default decider behavior, Discord/Web search, Pydantic validation, or raw response persistence.

## Open Questions

- None.
