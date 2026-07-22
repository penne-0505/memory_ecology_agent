---
title: "QA Verification: Docs-driven template v1.0.0 migration"
status: active
draft_status: n/a
qa_schema: 2
qa_status: partial
risk: High
created_at: 2026-07-22
updated_at: 2026-07-22
references:
  - "_docs/survey/Workflow/docs-template-v1-migration/survey.md"
  - "_docs/intent/Workflow/docs-template-v1-migration/decision.md"
  - "_docs/plan/Workflow/docs-template-v1-migration/plan.md"
  - "_docs/qa/Workflow/docs-template-v1-migration/test-plan.md"
related_issues: []
related_prs: []
---

# QA Verification: Docs-driven template v1.0.0 migration

## Summary

`Workflow-Chore-22` の legacy bootstrap migration を次の provenance で検証した。

- B: `37f7198edd9e27f1c7270fb74ce2caf83dca27de`
- U: `v1.0.0` -> `f71e9ab20466ea2972158334261f5ae2b2265754`
- P: `cc292d5e14c6ba92b3a996a8d07e125cf88751a2`
- Compatibility migration verdict: **PASS**
- Overall migration verification verdict: **PARTIAL**（strict schema の owner-directed defer、既存 packaging baseline、live external の未実施を含む）

U validator の external review と imported compatibility check は、P 由来の legacy
79 docs に対して PASS した。既存 Core docs は marker なし compatibility support を
保持し、新規 migration docs だけ schema v2 とした。

## Verification Verdict

Verdict: PARTIAL

Compatibility migration は PASS である。一方、この verification 全体は strict schema
migration が未完了であり、`uv build` の既存 baseline failure と live external の未実施を
閉じていないため PARTIAL とする。以下の deferred / residual / follow-up の境界を、
compatibility PASS や project regression PASS を full completion と誤読する根拠にしてはならない。

## Commands Run

```bash
./scripts/check-docs.sh
DD_SCOPE_PATHS="<P から追加・変更した docs>" ./scripts/check-docs.sh
npx --yes markdownlint-cli2@0.18.1 "_docs/**/*.md" "_evals/**/*.md" \
  "README.md" "AGENTS.md" "TODO.md" "QUICKSTART.md" \
  "!_docs/archives/**/*" "!_docs/standards/templates/**/*" \
  "!_evals/quarantine/**/*" --config .markdownlint.jsonc
uv run --python /home/penne/.local/bin/python3.12 pytest
AGENT_LLM_PROVIDER=mock AGENT_OBSERVATION_EXTRACTOR=deterministic \
  AGENT_DISCORD_ENABLED=false AGENT_DISCORD_MODE=observe_only \
  AGENT_DISCORD_MAX_MODE=observe_only \
  uv run --python /home/penne/.local/bin/python3.12 python -m app.main \
  --project-root "<isolated-temp-root>" llm smoke
AGENT_LLM_PROVIDER=mock AGENT_OBSERVATION_EXTRACTOR=deterministic \
  AGENT_DISCORD_ENABLED=false AGENT_DISCORD_MODE=observe_only \
  AGENT_DISCORD_MAX_MODE=observe_only \
  uv run --python /home/penne/.local/bin/python3.12 python -m app.main \
  --project-root "<isolated-temp-root>" discord doctor
AGENT_LLM_PROVIDER=mock AGENT_OBSERVATION_EXTRACTOR=deterministic \
  AGENT_DISCORD_ENABLED=false AGENT_DISCORD_MODE=observe_only \
  AGENT_DISCORD_MAX_MODE=observe_only \
  uv run --python /home/penne/.local/bin/python3.12 \
  python _evals/scripts/verify_memory_ecology_poc.py \
  --output /tmp/memory-ecology-template-migration-poc.json
uv build --out-dir /tmp/memory-ecology-template-migration-dist
uv build --out-dir /tmp/memory-ecology-template-baseline-build
```

Inventory closure は `inventory.tsv` と B / U / P の NUL-delimited `git ls-tree`
map を照合した。protected path は `git diff --quiet P -- <paths>` で確認した。

## Automated Test Results

| Command / Test | Result | Notes |
| --- | --- | --- |
| legacy docs baseline | PASS | migration 前 validator。 |
| imported U validators | PASS | P 由来 79 docs、schema edit 前。 |
| unscoped / changed-doc docs wrapper | PASS | validators、fixtures、hooks、workflow smoke。 |
| full Markdown lint | PASS | active 168 files、0 errors。 |
| schema/frontmatter fixtures | PASS | correct、wrong、unknown marker と duplicate key。 |
| pytest | PASS | 102 passed、dependency warning 1 件。 |
| mock LLM smoke | PASS | `provider-smoke-ok`、network/credential 不要。 |
| Discord doctor | PASS | errors 0、expected warnings 3 件。 |
| deterministic PoC verifier | PASS | isolated DB、core profile と lifecycle を確認。 |
| target `uv build` | BASELINE FAIL | exit 2、flat-layout package discovery。P と同一。 |
| P clean tree `uv build` | SAME FAIL | target と package list / exit 2 が完全一致。migration regression ではないが、配布 build の成功証跡ではない。 |

## Manual QA Results

| Checklist Item | Result | Notes |
| --- | --- | --- |
| inventory completeness | PASS | 350 rows = 350 union paths、duplicate / missing / extra 0。 |
| allowed-five resolution | PASS | apply 62、merge 12、keep 265、remove 11、defer 0。 |
| project raw preservation | PASS | runtime/source/tests/artifacts/packaging raw diff 0。 |
| exact cleanup | PASS | 7 exact B blobs を inactive quarantine へ移動。 |
| template-self exclusion | PASS | U history 未導入、legacy exact history は quarantine。 |
| paired skills | PASS | `.agents/skills` と `.claude/skills` の diff 0。 |
| bulk schema edit | PASS | existing Core intent / QA の marker addition 0。 |
| TODO trace | PASS | `Workflow-Chore-22` と AC は Plan / Intent / QA / verification に保持。 |

## Acceptance Criteria Coverage

| ID | Result | Evidence |
| --- | --- | --- |
| AC-001 | PASS | B / U / P と exact source/tag/SHA を survey、verification、lock に記録。 |
| AC-002 | PASS | inventory 350/350、invalid resolution / missing disposition 0。 |
| AC-003 | PASS | imported compatibility PASS と strict PARTIAL を分離して記録し、strict 完了を主張しない。 |
| AC-004 | PASS | protected diff 0、pytest / PoC / mock / doctor PASS。 |
| AC-005 | PASS | paired skills、fixtures、hooks、docs、lint、CI P + ACMR。 |
| AC-006 | PASS | misbehavior 4 種なし、exact-only quarantine。 |

## Decision Conformance

| ID | Result | Evidence |
| --- | --- | --- |
| DEC-001 | PASS | B / U / P を独立固定し、lock は最後の file write。 |
| DEC-002 | PASS | protected diff 0、custom root docs は semantic merge。 |
| DEC-003 | PASS | legacy 79 docs compatibility PASS、Core marker bulk addition 0。 |
| DEC-004 | PASS | exact B 7 blobs のみ quarantine、U self-history 未導入。 |
| DEC-005 | PASS | CI は P + ACMR、local unscoped PASS。 |

## Invariant Coverage

| ID | Result | Evidence |
| --- | --- | --- |
| INV-001 | PASS | final lock は exact U tag/full SHA。 |
| INV-002 | PASS | protected runtime/source/tests/artifacts raw diff 0。 |
| INV-003 | PASS | active remove path 0、quarantine 7/7 は B blob 一致。 |
| INV-004 | PASS | existing Core docs の schema marker addition 0。 |
| INV-005 | PASS | paired skill diff 0、CI P + ACMR。 |

## Deferred / Not Covered

| ID | Reason | Follow-up |
| --- | --- | --- |
| STRICT-SCHEMA | Existing Core docs の一括変換は DEC-003 の Non-Goal で、legacy docs は compatibility support に留まる。 | `Workflow-Chore-23` を durable intake authority とし、意味または QA 契約を編集する task で該当 pair を schema v2 化する。bulk marker edit は引き続き禁止する。 |
| BUILD-BASELINE | target と P の `uv build` は flat-layout package discovery で同一の exit 2。 | `Core-Chore-24` で migration と独立に packaging discovery / distribution build の scope と repair plan を定める。これは regression ではないが build-success evidence でもない。 |
| LIVE-EXTERNAL | token、guild、外部 trace を用意せず、state mutation を行わない scope のため、実 provider request / Discord message write は未実施。 | live readiness が必要になった時だけ、credentialed operator task で trace を残し、write authorization と mutation boundary を事前に確定して再検証する。本 migration の PASS 根拠にはしない。 |

## Residual Risks

- STRICT-SCHEMA: legacy Core docs の strict schema v2 化は未完了である。compatibility PASS は strict completion を代替しない。
- BUILD-BASELINE: target / P とも `uv build` が exit 2 のため、配布 build は未検証である。baseline equality は migration regression がないことだけを示す。
- LIVE-EXTERNAL: credentialed provider request と Discord write は実施していない。mock / live-free evidence は外部 runtime readiness を証明しない。

## Follow-up TODOs

- `Workflow-Chore-23`: strict schema v2 migration の intake authority を維持し、semantic / QA-contract edit ごとに対象 docs pair を decision-reviewed v2 migration へ送る。
- `Core-Chore-24`: packaging discovery と distribution build の baseline repair を、本 migration と分離して scope / plan 化する。
- LIVE-EXTERNAL はこの migration の follow-up task に固定しない。token / guild / trace と state-mutation authorization がある credentialed operator task だけが、external readiness を検証できる。
