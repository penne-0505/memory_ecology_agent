---
title: Docs-driven template v1.0.0 migration plan
status: active
draft_status: n/a
created_at: 2026-07-22
updated_at: 2026-07-22
references:
  - "_docs/survey/Workflow/docs-template-v1-migration/survey.md"
  - "_docs/intent/Workflow/docs-template-v1-migration/decision.md"
  - "_docs/qa/Workflow/docs-template-v1-migration/test-plan.md"
related_issues: []
related_prs: []
---

# Docs-driven template v1.0.0 migration plan

## Overview

legacy template baseline `37f7198edd9e27f1c7270fb74ce2caf83dca27de` から tagged release `v1.0.0` (`f71e9ab20466ea2972158334261f5ae2b2265754`) へ、owner-approved project cutoff `cc292d5e14c6ba92b3a996a8d07e125cf88751a2` を保全して移行する。

## Scope

- upstream 配布 validators、fixtures、paired skills、hooks、CI、standards、templates の reconciliation。
- customized `README.md`、`QUICKSTART.md`、`TODO.md` の semantic merge。
- legacy-compatible validator 導入、project docs の unchanged compatibility check、schema v2 の新規 migration docs への適用。
- exact B blob に一致する stale template path の限定 cleanup と template-self history の除外。
- 初回 `docs-template.lock.json` の compatibility PASS 後の作成。

## Non-Goals

- 既存 Core intent / QA docs の一括 schema v2 変換。
- app、tests、saved evaluation artifacts、live LLM / Discord state、runtime data の変更。
- template の lifecycle-self-audit 実装履歴を project history として輸入すること。
- main 更新、remote push、live provider 呼び出し、Discord への書き込み。

## Requirements

- **Functional**: inventory の各 path に allowed-five resolution と final disposition を一つずつ付ける。
- **Functional**: project customization を wholesale replacement せず、U の workflow contract と project-specific operator contract を両立する。
- **Non-Functional**: migration 前後の project-only source / tests / artifacts の raw diff を 0 にする。
- **Non-Functional**: compatibility migration と strict schema migration の verdict を分離する。
- **Safety**: removal candidate は inventory に列挙した exact B blob 一致 path のみに限定し、不一致時は変更せず quarantine/defer とする。

## Tasks

1. B / U / P、cutoff、branch ownership、baseline results を inventory に固定する。
2. U の migration skill、hooks、scripts を external input としてレビューする。
3. U validators / fixtures を導入し、unchanged project docs で compatibility check を実行する。
4. standards、templates、paired skills、hooks、CI、root guidance を resolution ごとに統合する。
5. strict schema は新規 migration docs のみ v2 とし、legacy Core docs は保持する。
6. project regression、raw diff、paired tree、provenance、inventory completeness を検証する。
7. compatibility PASS 後に lock を最後の write として作成する。

## QA Plan

- QA document: `_docs/qa/Workflow/docs-template-v1-migration/test-plan.md`
- Risk level: High
- Test strategy:
  - Unit: validator fixtures、hook tests、Python tests。
  - Integration: scoped / unscoped docs wrapper、PoC verifier。
  - E2E: live-free Discord doctor と deterministic CLI smoke。
  - Manual QA: three-way inventory、custom root merge、template-self exclusion、lock provenance review。
  - Validator / static check: Markdown lint、Deno fmt、frontmatter / TODO / links / intent / QA validators。
- rollback は migration child commit を採用しないこととし、P worktree / main / remote を変更しない。

## Deployment / Rollout

- isolated branch `rollout/docs-template-v1-memory-ecology` に P の child commit を一つ作る。
- main と origin には反映しない。owner が diff と verification を確認してから後続統合を判断する。
