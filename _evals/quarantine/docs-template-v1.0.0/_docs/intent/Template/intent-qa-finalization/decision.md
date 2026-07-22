---
title: Intent QA finalization decision
status: active
draft_status: n/a
created_at: 2026-05-25
updated_at: 2026-05-25
references:
  - "_docs/plan/Template/intent-qa-finalization/plan.md"
  - "_docs/qa/Template/intent-qa-finalization/test-plan.md"
related_issues: []
related_prs: []
---

# Intent QA finalization decision

## Context

このテンプレートは coding agent が root docs、`TODO.md`、`_docs/`、Skills を読んで作業する前提である。root に一回限りの作業 prompt が残ると active guidance と誤読される。また、TODO / QA validator 自体の回帰確認が弱いと、docs-driven workflow の契約が形だけになりやすい。

## Decision

- 一回限りの implementation prompt は root に置かず、必要事項を現行 docs へ反映した後は active project guidance から除外する。保持は前提にしない。
- TODO task の source of truth は `Title` field ではなく `### <ID>: [<Category>] <Title>` heading とする。
- QA verification は front-matter の `qa_status` と本文の `Verdict` を必ず一致させる。
- Validator には fixture と self-test を持たせ、valid が通るだけでなく invalid が失敗することを確認する。
- QA Skills には copyable な短い例を含め、抽象的な空欄 matrix / verdict を出しにくくする。

## Alternatives

- `PROMPT.md` を物理削除する: `rm` / `git rm` 禁止のため、この変更では active guidance から除外する扱いにした。
- TODO parser を `Title` field 起点のまま強化する: `Title` 欠落タスクを見逃すため採用しない。
- Validator fixtures を docs だけに残す: validator 自体を実行して確認できないため採用しない。

## Rationale

Agent workflow の事故は、入口ファイルの誤読と validator の抜け穴から起きやすい。Root guidance、TODO schema、QA verification、self-test を同じ変更単位で揃えることで、テンプレート利用開始直後から品質ゲートが機能する。

## Consequences / Impact

- 旧 TODO schema との後方互換はなくなる。
- TODO heading と fields の二重記述には同期コストがあるが、validator が不一致を検出する。
- Fixture の保守コストが増えるが、validator 変更時の回帰検出力が上がる。

## Quality Implications

- `Size >= M` / `Risk >= Medium` の task は QA test-plan と verification を持つ。
- Agent workflow / validator / CI / Skill 変更として、agent misbehavior checks を含める。
- Verification は PASS / PARTIAL / FAIL / BLOCKED と `qa_status` mapping の両方を確認する。

## Intent-derived Invariants

- INV-001: Root-level one-off implementation prompts must not remain active project guidance.
- INV-002: TODO validators must detect malformed or incomplete task headings even when `Title` is missing.
- INV-003: Verification `qa_status` must match the body `Verdict`.
- INV-004: Validator self-tests must prove both valid fixtures pass and invalid fixtures fail.
- INV-005: `.agents/skills` and `.claude/skills` copies of the same Skill must remain synchronized.
