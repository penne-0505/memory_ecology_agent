---
title: Docs-driven template v1.0.0 migration decisions
status: active
draft_status: n/a
intent_schema: 2
created_at: 2026-07-22
updated_at: 2026-07-22
references:
  - "_docs/survey/Workflow/docs-template-v1-migration/survey.md"
  - "_docs/plan/Workflow/docs-template-v1-migration/plan.md"
  - "_docs/qa/Workflow/docs-template-v1-migration/test-plan.md"
related_issues: []
related_prs: []
---

# Docs-driven template v1.0.0 migration decisions

## Context

project は pre-v1.0.0 template を大幅に project 固有化しており、provenance lock を持たない。移行は workflow を更新しつつ、Memory Ecology の runtime、LLM/digest evaluation、Discord adapter、saved artifacts、intent-heavy handoff を変えない必要がある。

## Decisions

### DEC-001: B / U / P を独立に固定する

- **What**: B は legacy upstream full SHA、U は release tag と full SHA、P は owner-approved local commit として別々に記録し、compatibility PASS 後に lock を U へ作る。
- **Why**: project-local validator scope と upstream provenance を混同すると、branch drift や premature lock を検出できないため。
- **Why not**: moving `main`、origin/main、`DD_SCOPE_BASE` を U の代用にしない。
- **Change freedom**: source URL と lock schema は互換性を保つ範囲で将来変更できるが、release identity は tag と full SHA の組で固定する。
- **Revisit when**: signed release metadata または別の immutable provenance mechanism を採用するとき。

### DEC-002: project semantics を raw-diff preservation で守る

- **What**: app、tests、saved evaluation artifacts、project-only docs と operator guidance は keep を既定とし、共有 root docs は semantic merge する。
- **Why**: migration の目的は workflow baseline 更新であり、Memory Ecology の機能・実験証跡・運用契約を再設計することではないため。
- **Why not**: U の root docs を wholesale replacement しない。
- **Change freedom**: workflow への参照追記や validation command 更新は許容するが、runtime/provider/Discord の保証範囲は変えない。
- **Revisit when**: project feature change と template migration を明示的に同じ release unit にする owner 判断があるとき。

### DEC-003: compatibility と strict schema を別に閉じる

- **What**: U の compatibility validator を unchanged legacy docs へ先に適用し、新規 migration docs だけ schema v2 とする。既存 Core docs の bulk migration は延期する。
- **Why**: schema migration のためだけの大量編集は historical intent と verification evidence の意味を変え、workflow update の回帰原因を不明瞭にするため。
- **Why not**: marker のない legacy docs を一括で `intent_schema: 2` / `qa_schema: 2` にしない。
- **Change freedom**: legacy doc の decision 意味または QA 契約を将来編集する単位で個別に v2 へ移行できる。
- **Revisit when**: legacy Core docs を意味単位でレビューする専用 migration が owner-approved になったとき。

### DEC-004: cleanup は exact provenance allowlist に限定する

- **What**: upstream deletionかつ P blob が B と一致する stale skill / standard / template-self record のみ remove し、不一致 path は変更せず quarantine/defer とする。U の lifecycle-self-audit history は輸入しない。
- **Why**: upstream deletion は project customization の削除権限ではなく、path 名だけの cleanup は project record を失う可能性があるため。
- **Why not**: glob、名称一致、推測による bulk deletion を行わない。
- **Change freedom**: owner が path と content を別途承認した場合は allowlist を追加できる。
- **Revisit when**: exact B comparison が不能、または deletion candidate に project edits が検出されたとき。

### DEC-005: CI は P 起点 ACMR、local closure は全走査する

- **What**: CI の scoped validator は `DD_SCOPE_BASE=P` と `DD_SCOPE_DIFF_FILTER=ACMR` を使い、local closure では scoped と unscoped の両方を実行する。
- **Why**: 既存 legacy docs の compatibility を保ちつつ、移行後に追加・編集・コピー・rename された docs を管理対象にするため。
- **Why not**: CI を追加ファイルだけの既定 `A` にせず、全 legacy docs の strict migration も要求しない。
- **Change freedom**: strict migration 完了後は scope env を外して全走査 CI に移行できる。
- **Revisit when**: legacy docs が全て schema v2 へ意味レビュー済みになったとき。

## Consequences / Impact

- U の workflow files は project baseline になるが、既存 project docs は compatibility support horizon 内で legacy marker なしを保持する。
- lock は schema 状態ではなく upstream revision だけを表す。
- exact cleanup と template-self exclusion は inventory と verification で監査可能になる。
- CI は P 以降の変更を ACMR で検査し、local unscoped run は全 repository の互換性を確認する。

## Quality Implications

- provenance、allowed-five resolution、raw-diff preservation、paired skill identity を機械的に確認する。
- branch mixing、blind replacement、premature lock、bulk schema edit を agent misbehavior checks として確認する。
- live provider / Discord write を行わず、deterministic/live-free paths で regression を確認する。

## Intent-derived Invariants

- INV-001 (from DEC-001): `docs-template.lock.json` は compatibility PASS 後にだけ作成され、`v1.0.0` と `f71e9ab20466ea2972158334261f5ae2b2265754` を保持する。
- INV-002 (from DEC-002): P から final child への app、tests、saved evaluation artifacts、runtime/source paths の raw diff は空である。
- INV-003 (from DEC-004): remove disposition は exact B blob 一致 allowlist に限定され、template-self lifecycle history は project に追加されない。
- INV-004 (from DEC-003): 既存 Core intent / QA docs に schema marker を bulk 追加しない。
- INV-005 (from DEC-005): paired `.agents/skills` と `.claude/skills` の同名配布 skill は同一内容で、CI scope は P + ACMR である。

## Rollback / Follow-ups

- rollback は child commit を統合せず P を継続利用する。main、origin、live runtime data は変更しない。
- strict schema migration は本 migration の residual follow-up である。`Workflow-Chore-23` を intake authority とし、既存 doc を意味単位で編集する必要が生じた時点で該当 pair を個別に v2 化する。bulk marker edit は authority に含めない。
- `uv build` の flat-layout package discovery failure は P と同一で migration regression ではないが、distribution build の成功を示さない。`Core-Chore-24` で packaging discovery と repair scope をこの migration から独立して扱う。
- live provider / Discord write は token、guild、外部 trace、state-mutation authorization を伴う credentialed operator task がある場合だけ再検証する。この migration の mock / live-free evidence を external readiness として扱わない。
