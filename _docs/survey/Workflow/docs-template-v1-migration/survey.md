---
title: Docs-driven template v1.0.0 three-way inventory survey
status: active
draft_status: n/a
created_at: 2026-07-22
updated_at: 2026-07-22
references:
  - "_docs/plan/Workflow/docs-template-v1-migration/plan.md"
  - "_docs/intent/Workflow/docs-template-v1-migration/decision.md"
  - "_docs/qa/Workflow/docs-template-v1-migration/test-plan.md"
related_issues: []
related_prs: []
---

# Docs-driven template v1.0.0 three-way inventory survey

## Cutoff

- Cutoff time: `2026-07-22 14:11:18 JST`
- Destination: isolated worktree `/tmp/docs-template-v1-rollout/memory_ecology_agent`
- Branch: `rollout/docs-template-v1-memory-ecology`
- Parallel ownership: this worktree/repository only; template root and other repositories are excluded.
- P: `cc292d5e14c6ba92b3a996a8d07e125cf88751a2`
- P staged diff: none
- P unstaged diff: none
- P untracked manifest: none
- P relation: local `main` is one commit ahead of `origin/main`; origin is not the migration cutoff.

## Provenance

- Source: `https://github.com/penne-0505/docs_driven_dev_template.git`
- B: `37f7198edd9e27f1c7270fb74ce2caf83dca27de` (legacy, untagged adoption baseline)
- U: `v1.0.0` -> `f71e9ab20466ea2972158334261f5ae2b2265754`
- Included upstream lane: the exact `B..U` range only.
- Excluded upstream lanes: moving `main` after U、unmerged branches、template lifecycle-self-audit implementation history。

## Baseline

- `./scripts/check-docs.sh`: PASS with legacy validators.
- `uv run --python /home/penne/.local/bin/python3.12 pytest`: PASS, 102 tests, 1 dependency deprecation warning.
- initial PoC command with unsupported `--json-output`: command error and not counted as verification; rerun uses `--output`.

## Inventory Contract

Path-level inventory is stored in `inventory.tsv` beside this survey. It covers every path in the union of `B -> U` and `B -> P`, with both classification axes, schema/meta flags, one allowed resolution, and a final disposition. Allowed resolution values are exactly `apply`, `merge`, `keep`, `remove`, and `defer`.

Project-only source, tests, saved reports, fixtures unrelated to the docs template, and runtime/operator records use `keep`. Customized shared root documents use `merge`. U-distributed workflow files use `apply`. Exact B deletion candidates use `remove`. A deletion candidate that does not match B would use `defer` with a quarantine disposition; none may be removed by path name alone.

## Schema Classification

- New migration Intent and QA use schema v2.
- Existing Core Intent / QA records remain legacy-compatible and are not bulk edited.
- Compatibility migration and strict schema migration receive separate verdicts.

## Template-self Classification

- U lifecycle-self-audit Plan / Intent / QA / verification are excluded.
- legacy Template intent-qa-finalization records are exact upstream self-history and cleanup candidates.
- stale `frontend-design` paired skills and `jj_workflow.md` are exact B deletion candidates.
