---
title: Intent QA finalization QA verification
status: active
draft_status: n/a
qa_status: verified
risk: Medium
created_at: 2026-05-25
updated_at: 2026-05-25
references:
  - "_docs/plan/Template/intent-qa-finalization/plan.md"
  - "_docs/intent/Template/intent-qa-finalization/decision.md"
  - "_docs/qa/Template/intent-qa-finalization/test-plan.md"
related_issues: []
related_prs: []
---

# Intent QA finalization QA verification

## Summary

Root active-guidance cleanup, heading-based TODO validation, QA verdict mapping, validator fixtures, self-test wiring, QA Skill examples, and eval guidance were updated and verified against the local validator suite.

## Verification Verdict

Verdict: PASS

## Commands Run

| Command / Test | Result | Notes |
| --- | --- | --- |
| `date +%F` | PASS | Returned `2026-05-25`. |
| `deno fmt --check scripts/*.mjs` | PASS | Checked 5 files after formatting `scripts/test-validators.mjs`. |
| `deno run --allow-read scripts/validate-frontmatter.mjs` | PASS | Exit 0. |
| `deno run --allow-read scripts/validate-todo.mjs` | PASS | Exit 0 with heading-based parser. |
| `deno run --allow-read scripts/validate-doc-links.mjs` | PASS | Exit 0. |
| `deno run --allow-read scripts/validate-qa.mjs` | PASS | Exit 0 with verdict mapping enforcement. |
| `deno run --allow-read --allow-run scripts/test-validators.mjs` | PASS | Valid fixtures passed; invalid TODO / QA fixtures failed as expected. |
| `./scripts/check-docs.sh` | PASS | Exit 0; includes validator self-test. |
| `npx markdownlint-cli2 "_docs/**/*.md" "_evals/**/*.md" "README.md" "AGENTS.md" "TODO.md" "QUICKSTART.md"` | PASS | `Summary: 0 error(s)`. |
| Deprecated runtime reference grep | PASS | No stale active-guidance references remain. |
| Legacy npm validation command grep | PASS | No matches. |
| `find . -maxdepth 1 -type f -name "*.md" -print \| sort` | PASS | Root Markdown is `AGENTS.md`, `QUICKSTART.md`, `README.md`, `TODO.md`. |
| `for f in docs-cleanup docs-prep implementation-prep post-implementation qa-prep qa-review test-maintenance; do cmp -s ".agents/skills/$f/SKILL.md" ".claude/skills/$f/SKILL.md" \|\| echo "DIFF $f"; done` | PASS | No output; paired Skills are synchronized. |
| `git diff --check` | PASS | Exit 0. |

## Automated Test Results

- `validate-todo.mjs` now accepts an optional TODO file path and parses task blocks from `### <ID>: [<Category>] <Title>` headings.
- `test-validators.mjs` confirmed invalid TODO fixtures for missing title, malformed heading, missing QA for Medium risk, and mismatched heading ID fail as expected.
- `validate-qa.mjs` now accepts fixture roots/files and enforces `PASS -> verified`, `PARTIAL -> partial`, `FAIL -> failed`, and `BLOCKED -> blocked`.
- `test-validators.mjs` confirmed invalid QA fixtures for missing invariant, status/verdict mismatch, in-progress verification status, missing test-plan reference, and archive path fail as expected.
- `check-docs.sh` and Docs CI include the validator self-test command.

## Manual QA Results

- Root one-off prompt requirements were incorporated into current docs, and root guidance was verified not to depend on retaining the prompt.
- Root Markdown files were reviewed and are active project guidance.
- QA Skill examples were added to `.agents` and `.claude` copies for `qa-prep`, `test-maintenance`, and `qa-review`.
- `_evals/agent-workflows/expected-invariants.md` and new eval cases cover malformed TODO headings, qa_status / verdict mismatch, and one-off prompt exclusion from active guidance.

## Acceptance Criteria Coverage

- AC-001: PASS. Root Markdown list excludes `PROMPT.md`, so active guidance does not depend on a one-off prompt file.
- AC-002: PASS. `validate-todo.mjs` is heading-based, and invalid TODO fixtures fail as expected.
- AC-003: PASS. `validate-qa.mjs` rejects mismatched `qa_status` / `Verdict` and `qa_status: in-progress` verification fixtures.
- AC-004: PASS. `_evals/validator-fixtures/` and `scripts/test-validators.mjs` exist and self-test valid / invalid fixtures.
- AC-005: PASS. `scripts/check-docs.sh` and `.github/workflows/docs-ci.yml` run `scripts/test-validators.mjs`.
- AC-006: PASS. QA Skill examples exist and `.agents` / `.claude` files compare equal.

## Invariant Coverage

- INV-001: PASS. One-off prompt requirements were incorporated into current docs; retaining the prompt is not part of the operating model.
- INV-002: PASS. Missing-title and malformed-heading fixtures prove heading-based TODO errors.
- INV-003: PASS. Status/verdict mismatch and in-progress status fixtures fail.
- INV-004: PASS. Self-test checks valid success and invalid expected failure cases.
- INV-005: PASS. Skill sync comparison produced no differences.

## Deferred / Not Covered

- GitHub Actions was not run live in this local session; the same Deno, markdownlint, and self-test commands were run locally and CI config was reviewed in diff.

## Residual Risks

None

## Follow-up TODOs

- None.
