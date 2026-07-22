---
title: Intent QA finalization QA test plan
status: active
draft_status: n/a
qa_status: planned
risk: Medium
created_at: 2026-05-25
updated_at: 2026-05-25
references:
  - "_docs/plan/Template/intent-qa-finalization/plan.md"
  - "_docs/intent/Template/intent-qa-finalization/decision.md"
related_issues: []
related_prs: []
---

# Intent QA finalization QA test plan

## Source of Intent

- TODO task: `Template-Enhance-4`
- Plan: `_docs/plan/Template/intent-qa-finalization/plan.md`
- Intent: `_docs/intent/Template/intent-qa-finalization/decision.md`

## Quality Goal

Agent が root prompt、TODO heading、QA verification、validator fixtures を誤って扱っても、docs / validators / CI が実用上の抜け穴を検出できる状態にする。

## Acceptance Criteria

- AC-001: Root 直下に一回限りの `PROMPT.md` が残っていない。
- AC-002: `validate-todo.mjs` が heading 起点で task を検出し、missing title / malformed heading / mismatched ID を error にする。
- AC-003: `validate-qa.mjs` が verification の `qa_status` と `Verdict` の不一致、および `qa_status: in-progress` を error にする。
- AC-004: `_evals/validator-fixtures/` と `scripts/test-validators.mjs` があり、valid fixtures は通り invalid fixtures は失敗する。
- AC-005: `scripts/check-docs.sh` と Docs CI が validator self-test を実行する。
- AC-006: QA Skills の具体例が `.agents` と `.claude` の同名 files で同期している。

## Intent-derived Invariants

- INV-001: Root-level one-off implementation prompts must not remain active project guidance.
- INV-002: TODO validators must detect malformed or incomplete task headings even when `Title` is missing.
- INV-003: Verification `qa_status` must match the body `Verdict`.
- INV-004: Validator self-tests must prove both valid fixtures pass and invalid fixtures fail.
- INV-005: `.agents/skills` and `.claude/skills` copies of the same Skill must remain synchronized.

## Risk Assessment

Risk: Medium. Validator、CI、Skill、documentation rule、agent workflow に影響する変更であり、過度に緩い validator も過度に厳しい validator も実運用を妨げる可能性がある。

## Test Strategy

- Deno validators で schema / links / QA docs / TODO を確認する。
- Fixture self-test で validator の false negative を防ぐ。
- grep で stale runtime references と古い npm validation commands を検出する。
- Skill sync comparison で `.agents` と `.claude` の drift を防ぐ。
- markdownlint と `git diff --check` で docs hygiene を確認する。

## Test Matrix

| ID | Source | Requirement / Invariant | Test Type | Command / File | Expected Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| AC-001 | TODO | Root `PROMPT.md` is not active guidance. | static check | `find . -maxdepth 1 -type f -name "*.md" -print \| sort` | Root Markdown list excludes `PROMPT.md`. | planned |
| AC-002 | TODO | Heading parser rejects malformed / incomplete TODO tasks. | fixture test | `deno run --allow-read --allow-run scripts/test-validators.mjs` | TODO invalid fixtures fail as expected. | planned |
| AC-003 | TODO | `qa_status` must match verification verdict. | fixture test | `deno run --allow-read --allow-run scripts/test-validators.mjs` | QA mismatch fixture fails as expected. | planned |
| AC-004 | TODO | Validator fixtures cover valid and invalid examples. | validator | `deno run --allow-read --allow-run scripts/test-validators.mjs` | Self-test reports PASS for valid and expected-failure fixtures. | planned |
| AC-005 | TODO | check-docs and CI include validator self-test. | diff review | `scripts/check-docs.sh`, `.github/workflows/docs-ci.yml` | Self-test command appears in both entrypoints. | planned |
| AC-006 | TODO | QA Skills contain concrete examples and stay synced. | static check | `cmp -s .agents/skills/<skill>/SKILL.md .claude/skills/<skill>/SKILL.md` | `qa-prep`, `test-maintenance`, and `qa-review` compare equal. | planned |
| INV-001 | intent | One-off prompts are not assumed to remain after their requirements are incorporated. | doc review | active guidance inventory | Agents must not treat one-off prompts as current guidance. | planned |
| INV-002 | intent | Missing `Title` field is still detected from heading. | fixture test | `_evals/validator-fixtures/todo/invalid/missing-title.md` | Fixture fails validation. | planned |
| INV-003 | intent | Verdict mapping is enforced. | fixture test | `_evals/validator-fixtures/qa/invalid/status-verdict-mismatch.md` | Fixture fails validation. | planned |
| INV-004 | intent | Self-test checks both pass and fail cases. | self-test | `scripts/test-validators.mjs` | Script expects exit 0 for valid and non-zero for invalid. | planned |
| INV-005 | intent | Paired Skill trees stay synchronized. | static check | `cmp -s` loop | No differences are reported. | planned |

## Manual QA Checklist

- Root Markdown files are active guidance only.
- Historical prompt warning is visible before the original prompt text.
- QA Skill examples are short, concrete, and copyable.
- Eval cases describe expected validator behavior and failure modes.

## Regression Checklist

- Existing `deno run --allow-read scripts/validate-frontmatter.mjs` still passes.
- Existing `deno run --allow-read scripts/validate-doc-links.mjs` still passes.
- Existing `deno run --allow-read scripts/validate-qa.mjs` still passes for real `_docs/qa`.
- Existing `TODO.md` validates under the new heading parser.

## Out of Scope

- Browser or app runtime QA.
- GitHub Actions live run.
- npm dependency changes.

## Open Questions

- None
