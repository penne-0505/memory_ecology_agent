---
title: "QA Test Plan: LLM Digest Proposal Quality Evaluation"
status: active
draft_status: n/a
qa_status: planned
risk: Medium
created_at: 2026-06-02
updated_at: 2026-06-02
references:
  - "_docs/intent/Core/llm-digest-proposal-quality-evaluation/decision.md"
  - "_docs/plan/Core/llm-digest-proposal-quality-evaluation/plan.md"
  - "_docs/qa/Core/llm-digest-proposal-quality-evaluation/verification.md"
  - "_evals/reports/llm_digest_proposal_quality_2026-06-02.md"
related_issues: []
related_prs: []
---

# QA Test Plan: `LLM Digest Proposal Quality Evaluation`

## Source of Intent

- TODO: `Core-Test-13`
- Plan: `_docs/plan/Core/llm-digest-proposal-quality-evaluation/plan.md`
- Intent: `_docs/intent/Core/llm-digest-proposal-quality-evaluation/decision.md`

## Quality Goal

LLM digest proposal の quality を sample world 上で評価し、active `llm_assisted` adoption に進むかを evidence-backed に判断する。

## Acceptance Criteria

- AC-001: deterministic decision と LLM proposal の比較レポートが sample world で作成されている。
- AC-002: disagreement の代表例が分類され、採用すべき / 退けるべき proposal の判断軸が記録されている。
- AC-003: `llm_assisted` adoption rule を実装するか、shadow 継続に留めるかの intent が更新されている。

## Intent-derived Invariants

- INV-001: Evaluation は final state updater を LLM に変更しない。
- INV-002: Report は agreement だけでなく disagreement と fallback を含む。
- INV-003: Optional real provider run は credential を明示した環境でのみ実施し、CI の必須条件にしない。
- INV-004: LLM proposal から `action_candidate` を単独採用しない。
- INV-005: Digest proposal は `core_profile` / `self_model` / Discord mode / Web search / final digest decision を変更しない。

## Risk Assessment

- Risk level: Medium
- Risk rationale: Evaluation workflow と docs artifact を追加するが runtime default は変更しない。
- Regression risk: Low。実装する場合も report path に限定する。
- Data safety risk: Medium。real provider output を扱う場合は raw response を保存しない。
- Security / privacy risk: Medium。credential は env var のみ。
- UX risk: Low。CLI / report の読み違いに注意する。
- Agent misbehavior risk: Medium。evaluation と adoption implementation を混同しない。

## Test Strategy

- Integration: sample world fixture run and report generation.
- Manual QA: optional real provider run if credentials are explicitly configured.
- Validator / static check: `./scripts/check-docs.sh`.
- Diff review: final state updater が LLM に変わっていないことを確認する。

## Test Matrix

| ID | Source | Requirement / Invariant | Test Type | Command / File | Expected Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| AC-001 | TODO | Comparison report exists. | integration | `_evals/scripts/evaluate_llm_digest_proposals.py` | Report includes deterministic and proposal decisions. | verified |
| AC-002 | TODO | Disagreement examples are classified. | manual QA | `_evals/reports/llm_digest_proposal_quality_2026-06-02.md` | Examples include adoption / reject rationale. | verified |
| AC-003 | TODO | Adoption direction is recorded. | docs | `_docs/intent/Core/llm-digest-proposal-quality-evaluation/decision.md` | Decision is active after evaluation. | verified |
| INV-001 | intent | Evaluation does not change final state updater. | diff review | `git diff -- app _evals _docs TODO.md` | Runtime default remains deterministic; script/report only. | verified |
| INV-002 | intent | Report includes disagreement and fallback. | report review | `_evals/reports/llm_digest_proposal_quality_2026-06-02.md` | Report has agreement, disagreement, fallback counts. | verified |
| INV-003 | intent | Real provider remains optional. | docs / validator | `./scripts/check-docs.sh` | Docs do not make credential mandatory. | verified |
| INV-004 | intent | LLM action proposals are not adopted alone. | report review | `_evals/reports/llm_digest_proposal_quality_2026-06-02.md` | Recommendation forbids automatic action adoption. | verified |
| INV-005 | intent | Proposal does not change core/self_model/Discord/Web/final digest behavior. | diff review | `git diff -- app _evals _docs TODO.md` | No runtime adoption or Discord/Web mode changes. | verified |

## Manual QA Checklist

- [ ] Inspect representative agreement, disagreement, and fallback cases.
- [ ] Confirm no raw provider response or secret-like text is persisted.

## Regression Checklist

- [ ] Existing digest proposal tests still pass.
- [ ] Existing docs check passes.

## Out of Scope

- Implementing active `llm_assisted`.

## Open Questions

- Which confidence threshold and risk flags are sufficient for any future assisted adoption?
