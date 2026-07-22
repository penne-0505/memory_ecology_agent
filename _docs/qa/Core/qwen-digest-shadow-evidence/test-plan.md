---
title: "QA Test Plan: Qwen Digest Shadow Evidence"
status: active
draft_status: n/a
qa_status: planned
risk: Medium
created_at: 2026-06-03
updated_at: 2026-06-03
references:
  - "_docs/intent/Core/qwen-digest-shadow-evidence/decision.md"
  - "_docs/plan/Core/qwen-digest-shadow-evidence/plan.md"
  - "_docs/qa/Core/deepseek-digest-primary-candidate/verification.md"
related_issues: []
related_prs: []
---

# QA Test Plan: `Qwen Digest Shadow Evidence`

## Source of Intent

- TODO: `Core-Test-17`
- Plan: `_docs/plan/Core/qwen-digest-shadow-evidence/plan.md`
- Intent: `_docs/intent/Core/qwen-digest-shadow-evidence/decision.md`

## Quality Goal

Repeated qwen live shadow evaluation should preserve enough verified fallback/baseline evidence to compare future primary-candidate regressions and assisted-readiness claims.

## Acceptance Criteria

- AC-001: qwen fallback/baseline runner creates multiple live artifacts, or real provider execution is explicitly skipped.
- AC-002: run-to-run variance is summarized for schema-valid, fallback, malformed JSON, validation error, agreement/disagreement, `action_candidate`, and `should_apply`.
- AC-003: a recommendation is recorded without implementing `llm_assisted`.

## Intent-derived Invariants

- INV-001: Final digest decisions remain deterministic.
- INV-002: `llm_assisted` is not implemented or enabled.
- INV-003: Live provider use is optional and explicitly configured.
- INV-004: Raw provider responses and secrets are not stored or printed.
- INV-005: Run-to-run variance is preserved in the report.

## Risk Assessment

- Risk level: Medium
- Risk rationale: Uses optional real provider evaluation and affects future adoption decisions.
- Regression risk: Low, because production runtime should not change.
- Data safety risk: Medium, because provider outputs and secrets must stay sanitized.
- Security / privacy risk: Medium, because credential presence is required but values must not be printed.
- UX risk: Low.
- Agent misbehavior risk: Medium, because shadow evidence must not be mistaken for active adoption.

## Test Strategy

- Unit: runner tests for partial flush remain passing; DeepSeek is now the default primary model.
- Integration: inspect generated qwen live artifacts.
- Manual QA: credentialed OpenRouter runs only with explicit config.
- Validator / static check: `./scripts/check-docs.sh`.
- Diff review: confirm production runtime and `AGENT_DIGEST_DECIDER` default are unchanged.

## Test Matrix

| ID | Source | Requirement / Invariant | Test Type | Command / File | Expected Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| AC-001 | TODO | Multiple qwen live artifacts or skipped provider status exists. | manual QA | runner command / verification doc | Artifact paths or `SKIPPED_REAL_PROVIDER`. | planned |
| AC-002 | TODO | Run-to-run variance is summarized. | report review | `_docs/qa/Core/qwen-digest-shadow-evidence/verification.md` | Metrics table across runs. | planned |
| AC-003 | TODO | Recommendation is recorded without adoption. | diff review | verification / intent | No `llm_assisted` implementation. | planned |
| INV-001 | intent | Deterministic final decisions remain unchanged. | diff review | app/runtime and app/cognition diff | No active decision path change. | planned |
| INV-004 | intent | Raw provider responses and secrets are omitted. | artifact review | JSON / Markdown reports | Sanitized metadata only. | planned |

## Manual QA Checklist

- [ ] Confirm credential presence without printing the credential value.
- [ ] Run qwen fallback/baseline live evaluation or record `SKIPPED_REAL_PROVIDER`.
- [ ] Inspect artifacts for sanitized output only.

## Regression Checklist

- [ ] `./scripts/check-docs.sh`
- [ ] `uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_live_digest_runner.py tests/test_digest_decider.py`

## Out of Scope

- Active `llm_assisted` adoption.
- New model selection work.
- Production runtime changes.

## Open Questions

- How many qwen runs are enough before `Core-Test-18` should start?
