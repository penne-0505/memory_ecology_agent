---
title: "QA Test Plan: OpenRouter Structured Digest Proposals"
status: active
draft_status: n/a
qa_status: planned
risk: Medium
created_at: 2026-06-03
updated_at: 2026-06-03
references:
  - "_docs/plan/Core/openrouter-structured-digest-proposals/plan.md"
  - "_docs/intent/Core/openrouter-structured-digest-proposals/decision.md"
  - "_docs/qa/Core/openrouter-structured-digest-proposals/verification.md"
related_issues: []
related_prs: []
---

# QA Test Plan: `OpenRouter Structured Digest Proposals`

## Source of Intent

- Request: OpenRouter structured output for digest proposal shadow evaluation.
- Plan: `_docs/plan/Core/openrouter-structured-digest-proposals/plan.md`
- Intent: `_docs/intent/Core/openrouter-structured-digest-proposals/decision.md`

## Quality Goal

Validate whether OpenRouter provider-native structured output can reduce qwen digest proposal schema fallback while preserving deterministic final decisions, prompt-only fallback for other providers, and raw response non-persistence.

## Acceptance Criteria

- AC-001: OpenRouter digest proposal requests send `response_format.type=json_schema` with `LLMDigestProposal` schema.
- AC-002: OpenRouter digest proposal requests send `provider.require_parameters=true`.
- AC-003: Non-OpenRouter providers keep the existing prompt-only parse path.
- AC-004: Pydantic validation remains the final schema gate.
- AC-005: Runner artifacts include `structured_output_enabled` and `provider_require_parameters` without raw response text.
- AC-006: Live qwen shadow evaluation records schema-valid/fallback/malformed/validation-error metrics and compares them to prior evidence.
- AC-007: Validation failures are aggregated by sanitized field path / error type / count without persisting raw model response text.
- AC-008: Prompt hardening explicitly constrains `related_concern_ids` to numeric concern IDs or `[]` without relaxing schema validation.

## Intent-derived Invariants

- INV-001: Final digest decisions remain deterministic.
- INV-002: `AGENT_DIGEST_DECIDER` default remains unchanged.
- INV-003: `llm_assisted` is not implemented or enabled.
- INV-004: Raw provider responses and secrets are not persisted or printed.
- INV-005: OpenRouter-specific parameters do not affect other providers.
- INV-006: Structured-output evidence is not treated as assisted readiness by itself.
- INV-007: Pydantic validation remains strict; diagnostics must not relax the schema gate.

## Risk Assessment

- Risk level: Medium
- Risk rationale: The change touches live provider request shape and future readiness evidence.
- Regression risk: Medium, because digest proposal validation and provider calls can fail if the payload is malformed.
- Data safety risk: Medium, because live provider responses must remain sanitized and non-persisted.
- Security / privacy risk: Medium, because real provider credentials may be used in live QA.
- Agent misbehavior risk: Medium, because structured-output success could be incorrectly promoted to `llm_assisted` readiness.

## Test Strategy

- Unit: inspect fake OpenRouter request payload and digest decider `extra_payload`.
- Unit: confirm mock/non-OpenRouter path receives no OpenRouter structured payload.
- Unit: confirm invalid enum output is still rejected by Pydantic.
- Integration: run existing digest decider and live runner tests.
- Validator: run `./scripts/check-docs.sh`.
- Manual QA: run one credentialed qwen OpenRouter shadow evaluation with `AGENT_MAX_WEB_QUERIES=0` and observation concurrency `4`.
- Diff review: confirm production final path, default decider, `llm_assisted`, Discord, Web search, and raw response persistence remain unchanged.

## Test Matrix

| ID | Source | Requirement / Invariant | Test Type | Command / File | Expected Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| AC-001 | TODO | OpenRouter sends JSON schema response format. | unit | `tests/test_llm.py`, `tests/test_digest_decider.py` | Payload includes `response_format.type=json_schema`. | planned |
| AC-002 | TODO | OpenRouter requires supported parameters. | unit | `tests/test_llm.py`, `tests/test_digest_decider.py` | Payload includes `provider.require_parameters=true`. | planned |
| AC-003 | TODO | Non-OpenRouter providers keep prompt-only path. | unit | `tests/test_digest_decider.py` | Mock provider receives `extra_payload=None`. | planned |
| AC-004 | TODO | Pydantic remains final gate. | unit | `tests/test_digest_decider.py` | Invalid enum persists rejected proposal with `ValidationError`. | planned |
| AC-005 | TODO | Runner artifacts include structured metadata and no raw text. | unit/manual QA | `tests/test_live_digest_runner.py`, live artifact | Metadata present; raw response persisted is false. | planned |
| AC-006 | TODO | Live qwen metrics are compared to prior evidence. | manual QA | verification doc | Metrics table includes previous-vs-current delta. | planned |
| AC-007 | TODO | Validation failures are aggregated without raw output. | unit/manual QA | `tests/test_live_digest_runner.py`, live artifact | `validation_failure_aggregate` includes only `loc`, `type`, and `count`. | planned |
| AC-008 | TODO | `related_concern_ids` prompt contract is numeric-array only. | unit/diff review | `tests/test_digest_decider.py`, prompt diff | Prompt forbids concern labels/titles/objects/strings and requires `[]` when absent or uncertain. | planned |
| INV-001 | intent | Final decisions remain deterministic. | diff/test review | `tests/test_digest_decider.py` | Shadow proposal does not change final decision path. | planned |
| INV-002 | intent | Default decider unchanged. | diff review | `app/config.py`, tests | No default change. | planned |
| INV-003 | intent | `llm_assisted` is not implemented or enabled. | diff review | app diff | No assisted adoption. | planned |
| INV-004 | intent | Raw responses and secrets are not persisted. | artifact review | JSON / Markdown reports | Raw response text absent; persisted flag false. | planned |
| INV-006 | intent | Structured evidence does not imply readiness PASS. | document review | verification / `Core-Test-18` docs | Readiness implication remains limited. | planned |
| INV-007 | intent | Validation gate remains strict. | diff/test review | `app/cognition/digest_decider.py`, tests | `LLMDigestProposal.model_validate` remains the acceptance gate. | planned |

## Manual QA Checklist

- [ ] Confirm OpenRouter credential presence without printing the value.
- [ ] Run one qwen OpenRouter shadow evaluation with structured output metadata.
- [ ] Inspect JSON / Markdown artifacts for metadata and absence of raw response text.
- [ ] Inspect `validation_failure_aggregate` for field/type/count only.
- [ ] Compare current schema fallback with prior qwen range `4-6/16`.

## Regression Checklist

- [ ] `./scripts/check-docs.sh`
- [ ] `uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_live_digest_runner.py tests/test_digest_decider.py`
- [ ] `uv run --python /home/penne/.local/bin/python3.12 pytest`

## Out of Scope

- Active `llm_assisted` adoption.
- Discord or Web search behavior.
- Raw response persistence.
- Broad model comparison.

## Open Questions

- Whether OpenRouter/qwen honors the full Pydantic JSON Schema without provider-side rejection.
- Whether one successful structured-output run is enough to justify two additional runs.
