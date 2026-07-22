---
title: "QA Test Plan: LLM Digest Decision Proposals"
status: active
draft_status: n/a
qa_status: planned
risk: High
created_at: 2026-06-02
updated_at: 2026-06-02
references:
  - "_docs/intent/Core/llm-digest-decision-proposals/decision.md"
  - "_docs/plan/Core/llm-digest-decision-proposals/plan.md"
related_issues: []
related_prs: []
---

# QA Test Plan: `LLM Digest Decision Proposals`

## Source of Intent

- TODO: `Core-Feat-12`
- Plan: `_docs/plan/Core/llm-digest-decision-proposals/plan.md`
- Intent: `_docs/intent/Core/llm-digest-decision-proposals/decision.md`

## Quality Goal

LLM を digest decision の proposal generator として追加しつつ、既定の deterministic behavior、offline CI、安全な永続化、downstream deterministic state update を維持する。

## Acceptance Criteria

- AC-001: `AGENT_DIGEST_DECIDER=deterministic` が既定で、provider call を行わず既存 digest behavior を維持する。
- AC-002: `AGENT_DIGEST_DECIDER=llm_shadow` で LLM proposal と deterministic final decision が別々に trace される。
- AC-003: final decision は shadow mode で deterministic のまま保持され、proposal が concern / memory / action / policy / core_profile を直接 mutate しない。
- AC-004: invalid JSON、schema-invalid output、provider error、unknown related concern、長すぎる text、secret-like output が安全に rejected / fallback trace になる。
- AC-005: proposal/final agreement と disagreement、fallback、provider/model、reason を CLI inspection で確認できる。
- AC-006: raw provider response と secrets は永続化されず、CI は mock/offline のまま通る。
- AC-007: README / QUICKSTART / reference / provider docs / QA docs が default deterministic、shadow behavior、fallback、manual v4pro smoke 境界を説明する。

## Intent-derived Invariants

- INV-001: 既定設定では digest proposal provider call と proposal persistence は発生しない。
- INV-002: `llm_shadow` では final digest decision が deterministic decision と一致する。
- INV-003: LLM proposal は downstream state を直接作成・更新しない。
- INV-004: invalid / unsafe provider output は raw response persistence なしで rejected / fallback trace になる。
- INV-005: proposal/final comparison は inspection 可能である。
- INV-006: real provider usage は manual opt-in であり、CI / default path / Discord mode / Web search を有効化しない。

## Risk Assessment

- Risk level: High
- Risk rationale: LLM provider、永続化、secret handling、digest routing 境界に触れる。
- Regression risk: deterministic digest path と downstream concern / memory creation が変わる可能性。
- Data safety risk: raw provider response や secret-like output を保存してしまう可能性。
- Security / privacy risk: API key、Authorization header、外部入力の長文保存。
- UX risk: CLI inspection が proposal と final decision を混同させる可能性。
- Agent misbehavior risk: LLM proposal を final state updater と誤解して downstream mutation を許してしまう可能性。

## Test Strategy

- Unit: schema validation、fallback、secret redaction、known concern filtering、agreement/disagreement 判定。
- Integration: wake cycle の deterministic default、llm_shadow proposal persistence、final deterministic decision、no direct mutation。
- E2E: temp-root deterministic smoke、fake-provider llm_shadow smoke。
- Manual QA: OpenRouter / `deepseek/deepseek-v4-pro` は credential が明示されている場合のみ実施し、未設定なら SKIPPED。
- Validator / static check: `pytest`、`./scripts/check-docs.sh`、`_evals/scripts/verify_memory_ecology_poc.py`。
- Diff review: raw response persistence がないこと、Discord operational mode と Web search が変わっていないことを確認する。

## Test Matrix

| ID | Source | Requirement / Invariant | Test Type | Command / File | Expected Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| AC-001 | TODO | Default digest remains deterministic and makes no provider call. | integration | `tests/test_digest_decider.py` | No proposal rows in default wake cycle. | planned |
| AC-002 | TODO | llm_shadow persists proposal and final decision separately. | integration | `tests/test_digest_decider.py` | Proposal row exists and final metadata references it. | planned |
| AC-003 | TODO / intent | LLM proposal does not directly mutate downstream state. | integration | `tests/test_digest_decider.py` | Counts show final deterministic path controls concern / memory creation. | planned |
| AC-004 | TODO | Invalid / unsafe output falls back safely. | unit | `tests/test_digest_decider.py` | Rejected proposal records and deterministic final decision. | planned |
| AC-005 | TODO | Inspection shows proposal comparison. | CLI | `python -m app.main inspect digest-proposals` | Output includes proposal, final decision, agreement, fallback. | planned |
| AC-006 | TODO / intent | Raw response and secrets are not persisted. | unit / diff review | `tests/test_digest_decider.py` | Secret-like strings absent from DB fields. | planned |
| AC-007 | TODO | Docs explain configuration and safety boundary. | validator | `./scripts/check-docs.sh` | Docs validation passes. | planned |
| INV-001 | intent | Default mode has no provider call or proposal persistence. | integration | `tests/test_digest_decider.py` | Exploding fake client is not called in deterministic mode. | planned |
| INV-002 | intent | Shadow final decision remains deterministic. | integration | `tests/test_digest_decider.py` | Proposal disagreement still finalizes deterministic decision. | planned |
| INV-003 | intent | Proposal cannot directly mutate downstream state. | integration | `tests/test_digest_decider.py` | No extra concern / memory / core profile mutation from proposal alone. | planned |
| INV-004 | intent | Raw provider response is not persisted on failures. | unit | `tests/test_digest_decider.py` | `raw_response_persisted=false` and hash only when text metadata exists. | planned |
| INV-005 | intent | Comparison is queryable. | CLI / integration | `tests/test_digest_decider.py` | Metadata includes agreement and arbitration reason. | planned |
| INV-006 | intent | CI remains offline and real provider is opt-in. | static / docs | `.env.example`, README, QUICKSTART | Real v4pro smoke is documented as optional. | planned |

## Manual QA Checklist

- [ ] Temp-root deterministic wake and `inspect digest-decisions` show deterministic final decisions.
- [ ] Fake-provider llm_shadow wake and `inspect digest-proposals` show proposals without raw response.
- [ ] Optional v4pro smoke is PASS or SKIPPED with explicit reason.

## Regression Checklist

- [ ] Existing observation extraction tests still pass.
- [ ] Existing wake/replay/Discord tests still pass.
- [ ] Existing deterministic downstream concern / memory creation still works.

## High-risk Checklist

- [ ] Rollback or recovery path is documented.
- [ ] Data safety has been checked.
- [ ] Security / privacy implications have been checked.
- [ ] Failure mode is understood.

## Out of Scope

- Active `llm_assisted` adoption of proposal as final decision.
- Real Web search.
- Discord runtime mode changes.

## Open Questions

- What proposal quality threshold should be required before enabling true `llm_assisted` adoption?
