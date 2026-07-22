---
title: "QA Test Plan: Limited LLM Assisted Confirm"
status: active
draft_status: n/a
qa_status: planned
risk: Medium
created_at: 2026-06-05
updated_at: 2026-06-05
references:
  - "_docs/intent/Core/limited-llm-assisted-confirm/decision.md"
  - "_docs/plan/Core/limited-llm-assisted-confirm/plan.md"
related_issues: []
related_prs: []
---

# QA Test Plan: `Limited LLM Assisted Confirm`

## Source of Intent

- TODO: `Core-Enhance-21`
- Plan: `_docs/plan/Core/limited-llm-assisted-confirm/plan.md`
- Intent: `_docs/intent/Core/limited-llm-assisted-confirm/decision.md`

## Quality Goal

Verify that `llm_assisted` can accept only safe deterministic-agreeing memory/discard proposals, while every risky or non-confirming case falls back to deterministic behavior.

## Acceptance Criteria

- AC-001: `llm_assisted` accepts only schema-valid, normalized-apply, deterministic-agreeing `memory_candidate` / `discard` proposals.
- AC-002: gate failures keep deterministic final decision.
- AC-003: metadata records assisted gate result and reasons.
- AC-004: default, Pydantic gate, raw response safety, Discord, and Web search behavior remain unchanged.

## Intent-derived Invariants

- INV-001: Default `AGENT_DIGEST_DECIDER` remains deterministic.
- INV-002: `llm_assisted` accepts only `memory_candidate` or `discard`.
- INV-003: Accepted assisted proposal must agree with deterministic disposition.
- INV-004: Accepted assisted proposal must have normalized `should_apply=true`.
- INV-005: Provider, JSON, schema, unsafe, fallback, disagreement, concern, action, and no-op cases remain deterministic.
- INV-006: Raw response text is not persisted.
- INV-007: Future relaxation is not implemented.

## Risk Assessment

- Risk: Medium.
- Rationale: This changes active behavior for an opt-in mode, but the default remains deterministic and the gate is narrow.
- Agent misbehavior risk: Medium, because `llm_assisted` could be mistaken for broad adoption if metadata is unclear.

## Test Strategy

- Add focused tests around `create_digest_proposal` gate behavior.
- Add wake-cycle tests to verify downstream final decision and metadata.
- Re-run digest tests and docs validator.

## Test Matrix

| ID | Source | Requirement / Invariant | Test Type | Command / File | Expected Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| AC-001 | TODO | Safe agreeing memory/discard can be accepted. | automated | `tests/test_digest_decider.py` | metadata shows `assisted_gate_result=accepted`. | verified |
| AC-002 | TODO | Disagreement and unsafe routes fallback. | automated | `tests/test_digest_decider.py` | final decision remains deterministic. | verified |
| AC-003 | TODO | Gate result and reasons are persisted in metadata. | automated | `tests/test_digest_decider.py` | metadata includes gate fields. | verified |
| AC-004 | TODO | Defaults and safety boundaries remain unchanged. | automated/static | `tests/test_digest_decider.py`, diff review | deterministic default and raw persistence unchanged. | verified |
| INV-002 | intent | Concern/action/no-op are not accepted. | automated | `tests/test_digest_decider.py` | gate rejects those decisions. | verified |
| INV-007 | intent | Future relaxation is not implemented. | diff review | app diff / docs | only confirm gate exists. | verified |

## Manual QA Checklist

- Confirm Inbox contains the follow-up note.
- Confirm no production default change.
- Confirm docs distinguish confirm gate from broad assisted adoption.

## Regression Checklist

- Deterministic mode creates no LLM proposal.
- `llm_shadow` still records proposals without changing final decisions.
- Invalid JSON and schema failures still persist rejected proposals safely.

## Out of Scope

- DeepSeek live reruns.
- Broad override.
- Concern/action queue design.
- Gate relaxation.

## Open Questions

- None for initial confirm implementation.
