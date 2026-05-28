---
title: Intent QA finalization plan
status: active
draft_status: n/a
created_at: 2026-05-25
updated_at: 2026-05-25
references:
  - "_docs/intent/Template/intent-qa-finalization/decision.md"
  - "_docs/qa/Template/intent-qa-finalization/test-plan.md"
related_issues: []
related_prs: []
---

# Intent QA finalization plan

## Overview

一回限りの作業仕様を、テンプレートの現行運用へ安全に反映する。主対象は root prompt の扱い、TODO validator、QA validator、validator fixture/self-test、QA Skills の具体例である。

## Scope

- Root 直下の一回限り prompt を active guidance から外す。
- `validate-todo.mjs` を `### <ID>: [<Category>] <Title>` heading 起点の parser にする。
- `validate-qa.mjs` で verification の `qa_status` と本文 `Verdict` の対応を検証する。
- validator fixtures と `scripts/test-validators.mjs` を追加し、valid / invalid の両方を検証する。
- `scripts/check-docs.sh` と Docs CI に validator self-test を追加する。
- `qa-prep` / `test-maintenance` / `qa-review` の同名 Skills を `.agents` と `.claude` で同期し、具体例を追加する。
- `_docs/standards/` と `_evals/agent-workflows/` に新しい invariant を反映する。

## Non-Goals

- npm 依存の追加。
- 古い TODO / QA schema との後方互換。
- `_docs/archives/` への QA / intent の移動。
- root prompt の物理削除。

## Requirements

- Root-level Markdown は active project guidance として読まれても問題ない状態にする。
- TODO task は heading から検出し、`Title` field が欠落していても task として検証する。
- heading ID / category / title と task fields の不一致を error にする。
- verification の `qa_status` は本文 verdict と一致させる。
- validator fixtures は valid examples と intentionally invalid examples を含める。
- self-test は invalid fixtures が失敗することも確認する。
- 実行していない検証を verification や最終報告に書かない。

## Tasks

1. Root `PROMPT.md` を active guidance から除外し、必要事項を現行 docs へ反映する。
2. TODO schema docs と validator parser を heading 起点に更新する。
3. QA validator の verdict mapping と fixture mode を実装する。
4. Fixture tree と self-test script を追加する。
5. check-docs / Docs CI / Skills / eval docs を同期する。
6. QA verification を作成し、`qa-review` で PASS 可否を確認する。

## QA Plan

- QA test-plan: `_docs/qa/Template/intent-qa-finalization/test-plan.md`
- Main checks:
  - Deno validators.
  - Validator fixture self-test.
  - markdownlint.
  - `.agents` / `.claude` Skill sync comparison.
  - grep checks for stale runtime references and old npm validation commands.

## Deployment / Rollout

テンプレート repo 内の docs / scripts / skills / evals を同時に更新する。外部 runtime や secret は扱わない。完了後は `scripts/check-docs.sh` と個別 validator の両方で確認する。
