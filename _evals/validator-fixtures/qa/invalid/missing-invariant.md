---
title: Fixture QA missing invariant
status: active
draft_status: n/a
qa_status: planned
risk: Medium
created_at: 2026-05-25
updated_at: 2026-05-25
references:
  - "_docs/plan/Template/intent-qa-finalization/plan.md"
  - "_docs/intent/Template/intent-qa-finalization/decision.md"
related_issues: []
related_prs: []
fixture_path: "_docs/qa/Template/intent-qa-finalization/test-plan.md"
---

# Fixture QA missing invariant

## Source of Intent

- Intent: `_docs/intent/Template/intent-qa-finalization/decision.md`

## Quality Goal

This fixture must fail because it omits an `INV-001` style invariant.

## Acceptance Criteria

- AC-001: Missing invariants are rejected.

## Intent-derived Invariants

- Missing on purpose.

## Risk Assessment

Risk: Medium.

## Test Strategy

Use `validate-qa.mjs` in fixture mode.

## Test Matrix

| ID | Source | Requirement / Invariant | Test Type | Command / File | Expected Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| AC-001 | fixture | Invalid fixture fails. | validator | `deno run --allow-read scripts/validate-qa.mjs _evals/validator-fixtures/qa/invalid/missing-invariant.md` | Validator exits non-zero. | planned |

## Manual QA Checklist

- None

## Regression Checklist

- None

## Out of Scope

- Runtime QA.

## Open Questions

- None
