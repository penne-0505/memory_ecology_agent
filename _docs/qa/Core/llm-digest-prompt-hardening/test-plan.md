---
title: "QA Test Plan: LLM Digest Prompt Hardening"
status: active
draft_status: n/a
qa_status: planned
risk: Medium
created_at: 2026-06-02
updated_at: 2026-06-02
references:
  - "_docs/intent/Core/llm-digest-prompt-hardening/decision.md"
  - "_docs/plan/Core/llm-digest-prompt-hardening/plan.md"
related_issues: []
related_prs: []
---

# QA Test Plan: `LLM Digest Prompt Hardening`

## Source of Intent

- TODO: `Core-Enhance-14`
- Plan: `_docs/plan/Core/llm-digest-prompt-hardening/plan.md`
- Intent: `_docs/intent/Core/llm-digest-prompt-hardening/decision.md`

## Quality Goal

LLM digest proposal prompt / rubric と `should_apply` normalization を harden し、`llm_shadow` proposal が safer and more informative になるようにする。final digest decision と downstream state mutation は deterministic boundary のまま維持する。

## Acceptance Criteria

- AC-001: Prompt が `concern_candidate` と `memory_candidate` の境界、`discard`、`action_candidate`、`no_op` を明確に定義している。
- AC-002: Prompt が `action_candidate` の自動採用禁止、downstream state mutation 禁止、raw provider response 非永続化境界を明示している。
- AC-003: `should_apply` は conservative advisory field として定義され、risk boundary flags では deterministic normalization により true を禁止している。
- AC-004: confidence calibration と risk flag rubric が prompt 内に明示されている。
- AC-005: 評価スクリプトが required metrics と qualitative examples を出力する。
- AC-006: Prompt/rubric tests と既存 regression tests が通る。

## Intent-derived Invariants

- INV-001: Prompt は LLM `action_candidate` の自動採用禁止を含む。
- INV-002: Prompt は LLM proposal が downstream state を mutate しないことを明示する。
- INV-003: Prompt は stable fact / user feedback / project requirement と unresolved tension を区別する。
- INV-004: `should_apply=true` は action / boundary / unknown / low-confidence cases で禁止される。
- INV-005: Evaluation report は boundary disagreement と qualitative examples を確認できる。
- INV-006: Runtime final digest decision は deterministic のままで、CI は mock/offline のまま通る。

## Risk Assessment

- Risk level: Medium
- Risk rationale: Runtime behavior は変えないが、LLM provider prompt / evaluation workflow / QA docs に影響する。
- Regression risk: Prompt version change が evaluation comparability を変える。
- Data safety risk: Prompt が raw response や downstream mutation を許すように読めると、将来の adoption 判断が危険になる。
- Agent misbehavior risk: `should_apply` や `action_candidate` を実 adoption と誤解する可能性。

## Test Strategy

- Unit: prompt text が key safety and rubric requirements を含むことを検証する。
- Unit: prompt examples が stable fact -> memory、true concern -> concern、repeated noise -> discard、action -> should_apply false を含むことを検証する。
- Unit: model `should_apply=true` が低 confidence / blocked risk で false に正規化され、allowed high-confidence memory/discard だけ true になることを検証する。
- Script: `_metrics` が required metrics を算出することを fixture rows で検証する。
- Regression: full `pytest` で digest / wake / observation / replay / Discord tests を確認する。
- Validator: `./scripts/check-docs.sh` で docs / TODO / QA consistency を確認する。
- E2E-ish: `_evals/scripts/verify_memory_ecology_poc.py` と `_evals/scripts/evaluate_llm_digest_proposals.py` を実行する。

## Test Matrix

| ID | Source | Requirement / Invariant | Test Type | Command / File | Expected Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| AC-001 | TODO | Prompt defines decision boundaries. | unit | `tests/test_digest_decider.py` | Prompt text contains definitions and examples. | planned |
| AC-002 | TODO / intent | Prompt forbids automatic action adoption and downstream mutation. | unit | `tests/test_digest_decider.py` | Required boundary strings are present. | planned |
| AC-003 | TODO / intent | `should_apply` is conservative and boundary flags forbid true. | unit | `tests/test_digest_decider.py` | Prompt text and normalization tests include allowed and forbidden cases. | planned |
| AC-004 | TODO | Confidence and risk flag rubric are explicit. | unit | `tests/test_digest_decider.py` | Calibration bands and required risk flags are present. | planned |
| AC-005 | TODO / intent | Evaluation report has required metrics and qualitative examples. | unit / script | `tests/test_digest_decider.py`, `_evals/scripts/evaluate_llm_digest_proposals.py` | Metrics include boundary counts and selected examples. | planned |
| AC-006 | TODO | Regression tests pass. | regression | `uv run --python /home/penne/.local/bin/python3.12 pytest` | Full suite passes. | planned |
| INV-001 | intent | Action proposal cannot be auto-adopted. | unit / diff review | `tests/test_digest_decider.py`, prompt diff | `action_candidate` example has `should_apply=false`. | planned |
| INV-002 | intent | Proposal cannot mutate downstream state. | regression / diff review | `tests/test_digest_decider.py` | Existing no-direct-mutation test still passes. | planned |
| INV-003 | intent | Stable fact and unresolved tension are distinguished. | unit | `tests/test_digest_decider.py` | Examples map to memory and concern respectively. | planned |
| INV-004 | intent | Boundary risk flags prevent `should_apply=true`. | unit | `tests/test_digest_decider.py` | Prompt lists prohibited flags and persisted proposal uses normalized value. | planned |
| INV-005 | intent | Report includes boundary disagreement and examples. | script | `_evals/scripts/evaluate_llm_digest_proposals.py` | Report includes required metrics and qualitative sections. | planned |
| INV-006 | intent | Runtime remains deterministic by default and CI offline. | regression | `pytest`, `./scripts/check-docs.sh` | Existing tests and docs check pass without real credentials. | planned |

## Manual QA Checklist

- [ ] Review prompt diff for scope creep into active adoption.
- [ ] Review evaluation report for `raw_response_persisted_count=0`.
- [ ] Confirm live v4pro is PASS only if explicit provider/model/credential are configured; otherwise SKIPPED.

## Regression Checklist

- [ ] Existing digest proposal validation tests still pass.
- [ ] Existing wake / observation / replay / Discord tests still pass.
- [ ] Default deterministic digest mode remains unchanged.

## Out of Scope

- Active `llm_assisted` adoption.
- Real Web search.
- Discord mode changes.
- CI credentials for real providers.

## Open Questions

- What live v4pro boundary metrics are sufficient before considering any future assisted adoption?
