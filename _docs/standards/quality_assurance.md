# Quality Assurance Standard

## 目的

このテンプレートにおける QA は、単に「テストを増やすこと」ではない。以下を確認する活動として扱う。

- 実装が intent に記録された設計判断を裏切っていないか。
- Plan で約束した実装方針を満たしているか。
- Acceptance Criteria が自動テスト・手動 QA・validator・review のいずれかで確認されているか。
- 未確認リスクが明示されているか。

QA 文書は実装の後始末ではなく、設計判断を検証可能な条件へ変換するための作業台である。

## 基本原則

- QA は実装後ではなく、実装前または実装中に設計する。
- `Size >= M` のタスクでは QA test-plan を必須とする。
- `Risk >= Medium` のタスクでは QA test-plan を必須とする。
- `Risk High / Critical` のタスクでは rollback / recovery / data safety の確認項目を必須とする。
- Bug 修正では、原則として regression test または no-test rationale を残す。
- Refactor では、behavior-preservation checks を明記する。
- Agent workflow / validator / CI / Skill / documentation rule の変更では、agent misbehavior risk を確認する。
- テストは実装詳細ではなく、intent / acceptance criteria / invariant に紐づける。
- QA 文書はテストそのものではない。実行可能なテストが書ける場合は、必ずコードベース側の適切な場所に置く。

## Risk 分類

| Risk | 定義 |
| --- | --- |
| Low | 局所的で、失敗しても影響が小さい変更。`Size XS/S` の軽微な Doc や Chore など。 |
| Medium | 機能挙動、ワークフロー、validator、ドキュメント規約、agent skill に影響する変更。`Size M` 以上は原則 Medium 以上。 |
| High | 互換性、データ損失、認証、権限、セキュリティ、課金、外部 API、CI/CD、migration に関わる変更。 |
| Critical | 本番障害、secret 漏洩、重大なデータ破壊、ユーザー影響の大きい破壊的変更につながり得る変更。 |

Risk は「作業量」ではなく、失敗時の影響と検証難度で判断する。

## QA 必須条件

| 条件 | 必須文書・確認 |
| --- | --- |
| `Size >= M` | Plan, Intent, QA test-plan が必須。 |
| `Risk >= Medium` | Intent, QA test-plan が必須。 |
| `Risk High / Critical` | Intent, QA test-plan, verification が必須。rollback / recovery / security / data safety の観点を明記する。 |
| `Category Bug` | regression test または no-test rationale が必須。 |
| `Category Refactor` | behavior-preservation checks が必須。 |
| Agent workflow / docs workflow / validator / CI / Skill 変更 | agent misbehavior checks が必須。 |

`Size XS/S` かつ `Risk Low` のタスクでは、Plan / Intent / QA / Verification は `None` にできる。ただし、Bug や Refactor など再発防止や挙動維持の説明が必要な場合は、軽量な根拠を TODO / PR / verification に残す。

## intent-derived invariant

intent-derived invariant は、intent に残された設計判断を「壊してはいけない条件」として書き直したものである。実装詳細ではなく、設計判断の意味を守る条件にする。

例:

```text
Intent:
  intent documents are permanent decision records and must not be archived.

Invariant:
  INV-001: `_docs/intent/**` must never be moved into `_docs/archives/**`.
  INV-002: cleanup skills must not list intent as an archive candidate.
  INV-003: validators must only allow draft / plan / survey archives.
```

抽出手順:

1. intent の `Decision` と `Consequences / Impact` を読む。
2. 「この判断が破られた状態」を具体的に列挙する。
3. その状態を検出できる AC / INV に変換する。
4. 自動テスト・validator・手動 QA・diff review のどれで確認するか Test Matrix に割り当てる。

## test matrix

test matrix は最低限、以下の列を持つ。

| ID | Source | Requirement / Invariant | Test Type | Command / File | Expected Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| AC-001 | TODO | ... | unit | ... | ... | planned |
| INV-001 | intent | ... | validator | ... | ... | planned |

`Status` は以下のいずれかにする。

- `planned`
- `covered`
- `verified`
- `deferred`
- `not-applicable`

`deferred` には理由が必要である。理由のない deferred は、検証漏れとして review で扱う。

## verification verdict

`verification.md` の最終判定は以下のいずれかにする。

| Verdict | 意味 |
| --- | --- |
| `PASS` | AC / INV が確認され、完了扱いにできる。 |
| `PARTIAL` | 一部未確認だが、残リスクと follow-up TODO が明示され、限定的に完了扱いにできる。 |
| `FAIL` | 必須条件を満たしていない。完了不可。 |
| `BLOCKED` | 外部要因や未解決 blocker により検証不能。完了不可。 |

`PARTIAL` / `FAIL` / `BLOCKED` では、残リスクと次アクションを必須にする。

`verification.md` の front-matter `qa_status` は、本文 `Verification Verdict` の `Verdict` と一致しなければならない。

| Verdict | qa_status |
| --- | --- |
| `PASS` | `verified` |
| `PARTIAL` | `partial` |
| `FAIL` | `failed` |
| `BLOCKED` | `blocked` |

## QA documents

QA 文書は以下の canonical path に置く。

```text
_docs/qa/<Area>/<slug>/test-plan.md
_docs/qa/<Area>/<slug>/verification.md
```

- `test-plan.md` は intent・plan・TODO から導いた QA 計画である。
- `verification.md` は実装後の検証証跡であり、実行コマンド、手動 QA、未確認リスク、最終判定を残す。
- QA docs は persistent quality records であり、archive しない。
- feature や判断が obsolete になった場合は、`status: obsolete` または `status: superseded` にする。
- references は root-relative canonical path を推奨する。

## Root-level prompts

- Root-level Markdown files are treated as active project guidance.
- One-off implementation prompts must not be left at repository root.
- If retained, move them under `_evals/prompts/` or another clearly historical location and mark them as non-operational.
