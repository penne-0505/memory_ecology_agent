---
title: "QA Test Plan: Docs-driven template v1.0.0 migration"
status: active
draft_status: n/a
qa_schema: 2
qa_status: planned
risk: High
created_at: 2026-07-22
updated_at: 2026-07-22
references:
  - "_docs/survey/Workflow/docs-template-v1-migration/survey.md"
  - "_docs/intent/Workflow/docs-template-v1-migration/decision.md"
  - "_docs/plan/Workflow/docs-template-v1-migration/plan.md"
related_issues: []
related_prs: []
---

# QA Test Plan: Docs-driven template v1.0.0 migration

## Source of Intent

- TODO: `Workflow-Chore-22`
- Plan: `_docs/plan/Workflow/docs-template-v1-migration/plan.md`
- Intent: `_docs/intent/Workflow/docs-template-v1-migration/decision.md`

## Decision Review Scope

- DEC-001: B / U / P と lock timing。
- DEC-002: project semantics と raw-diff preservation。
- DEC-003: compatibility / strict schema separation。
- DEC-004: exact-only cleanup と template-self exclusion。
- DEC-005: P + ACMR CI scope と unscoped closure。

## Quality Goal

U の docs-driven workflow を採用しながら、project 固有の機能・証跡・運用契約を変えず、provenance と deferred strict schema 状態を再検証可能にする。

## Acceptance Criteria

- AC-001: B / U / P と final lock が一致する。
- AC-002: union inventory が allowed-five resolution と disposition を全 path に持つ。
- AC-003: unchanged docs compatibility PASS と strict schema 別 verdict があり、strict が未完了なら overall verification を PARTIAL として残リスクと durable follow-up authority を記録する。
- AC-004: project regression と raw-diff preservation が PASS する。
- AC-005: paired skills、fixtures、hooks、docs、lint、CI scope が PASS する。
- AC-006: agent misbehavior と exact-only cleanup checks が PASS する。

## Intent-derived Invariants

- INV-001: lock は compatibility PASS 後の final write で exact U を指す。
- INV-002: app / tests / artifacts / runtime-source の raw diff は空である。
- INV-003: removal は exact B allowlist のみで template-self history を追加しない。
- INV-004: existing Core intent / QA に schema marker を bulk 追加しない。
- INV-005: paired skills は同一で CI scope は P + ACMR である。

## Risk Assessment

- Risk level: High
- Risk rationale: workflow、validator、CI、hooks、schema compatibility、provenance を同時に変更する migration である。
- Regression risk: project docs の誤った strict 化、custom root guidance の上書き、stale workflow の残留。既存 `uv build` failure を migration regression でないことだけを理由に build-success と誤記するリスクも含む。
- Data safety risk: runtime DB と saved artifacts を変更しない。raw diff と git status で確認する。
- Security / privacy risk: `.env` と secrets を読まず、live provider / Discord write を行わない。この live-free boundary は外部 runtime readiness の PASS evidence ではない。
- UX risk: agent hook が過剰に block する、または paired guidance が不一致になる可能性。
- Agent misbehavior risk: branch mixing、blind replacement、premature lock、bulk schema edit、unreviewed removal。

## Test Strategy

- Unit: `scripts/test-validators.mjs`、`scripts/test-agent-workflow-hook.mjs`、pytest。
- Integration: `scripts/check-docs.sh` の scoped / unscoped、PoC verification。
- E2E: mock provider smoke、Discord doctor read-only/live-free path。
- Manual QA: inventory completeness、custom root diff、template-self exclusion、lock timing。
- Validator / static check: Deno fmt、frontmatter、TODO、links、intent、QA、Markdown lint。
- Diff review: P との path-limited raw diff、B exact blob removal、paired skill compare。

## Test Matrix

| ID | Source | Requirement / Invariant | Test Type | Command / File | Expected Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| AC-001 | TODO | B / U / P と lock provenance | static | `git rev-parse` と lock JSON review | tag/full SHA/P が一致 | verified |
| AC-002 | TODO | union inventory completeness | static | inventory row/count script | unresolved 0、allowed resolution 以外 0 | verified |
| AC-003 | TODO | compatibility / strict 分離 | validator / QA review | unscoped/scoped validators、verification residual review | compatibility PASS、strict PARTIAL、durable follow-up authority | verified |
| AC-004 | TODO | project behavior preservation | regression | pytest、PoC、mock smoke、Discord doctor、raw diff、target/P `uv build` comparison | tests PASS、protected path diff 0、build failure is P-identical and separately tracked | verified |
| AC-005 | TODO | workflow closure | static/unit | paired diff、fixtures、hooks、Markdown lint | required command PASS | verified |
| AC-006 | TODO | misbehavior と cleanup | diff review | path inventory と git diff | blind replacement / bulk marker / extra removal なし | verified |
| INV-001 | intent | final lock exact U | static | lock JSON + git diff ordering review | exact tag/SHA | verified |
| INV-002 | intent | protected raw diff 0 | diff review | `git diff P -- <protected paths>` | empty | verified |
| INV-003 | intent | exact-only removal | static | B blob hash comparison | allowlist 全件 exact | verified |
| INV-004 | intent | no bulk schema migration | static | Core schema marker diff | marker addition 0 | verified |
| INV-005 | intent | paired skills + CI ACMR | static | recursive diff + workflow review | identical、P + ACMR | verified |

## Manual QA Checklist

- [x] customized README / QUICKSTART / TODO の project-specific content が保持される。
- [x] U の lifecycle-self-audit Plan / Intent / QA / verification が追加されない。
- [x] removed path は B blob と一致し、project customization を含まない。
- [x] lock が compatibility checks より先に作成されていない。

## Regression Checklist

- [x] pytest と deterministic PoC verification が baseline と同等以上。
- [x] mock LLM smoke は credential や network を要求しない。
- [x] Discord doctor は read-only/live-free 設定で secret を表示しない。
- [x] saved reports と source/tests の raw diff が 0。

## High-risk Checklist

- [x] Rollback or recovery path is documented.
- [x] Data safety has been checked.
- [x] Security / privacy implications have been checked.
- [x] Failure mode is understood.

## Out of Scope

- live LLM provider request、Discord message write、runtime DB mutation。
- existing Core docs の strict schema v2 migration。
- main / origin 更新。

## Open Questions

- None. B / U / P、destination mode、ownership、strict deferral は owner 指示で固定済み。
