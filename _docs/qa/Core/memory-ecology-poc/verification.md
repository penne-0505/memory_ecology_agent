---
title: "QA Verification: Memory Ecology Agent PoC"
status: active
draft_status: n/a
qa_status: verified
risk: High
created_at: 2026-05-29
updated_at: 2026-06-02
references:
  - "_docs/qa/Core/memory-ecology-poc/test-plan.md"
  - "_docs/intent/Core/memory-ecology-poc/decision.md"
  - "_docs/plan/Core/memory-ecology-poc/plan.md"
  - "_docs/reference/Core/memory-ecology-poc/reference.md"
  - "_evals/reports/memory_ecology_verification_2026-05-30.json"
related_issues: []
related_prs: []
---

## Summary

Memory Ecology Agent PoC の deterministic closed loop を強化し、外部 LLM provider / 実 Web search / live Discord credentials なしで、digest decision、natural concern lifecycle、policy-driven probe planning、outcome-driven policy update、state-sensitive replay drift、core profile stability を検証した。追加で GitHub Actions の pytest CI を整備し、mock/offline 設定で pytest と deterministic verification script を再現する経路を確認した。

## Verification Verdict

Verdict: PASS

## Commands Run

| Command / Test | Result |
| --- | --- |
| `uv run --python /home/penne/.local/bin/python3.12 pytest` | PASS: 52 passed, 1 warning (`discord.py` の Python 3.13 deprecation warning) |
| `./scripts/check-docs.sh` | PASS: TODO / frontmatter / links / QA / validator fixtures |
| `uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/verify_memory_ecology_poc.py --output /tmp/memory_ecology_ci_check.json > /tmp/memory_ecology_ci_check.log && test -s /tmp/memory_ecology_ci_check.json` | PASS: CI step equivalent generated isolated verification JSON under `/tmp` |
| `uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/verify_memory_ecology_poc.py --output _evals/reports/memory_ecology_verification_2026-05-30.json` | PASS: isolated report generated with digest decisions, lifecycle probe, replay drift, core stability |
| `uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root /tmp/tmp.uxaOHYrZuE init` | PASS: initialized isolated DB |
| `uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root /tmp/tmp.uxaOHYrZuE seed` | PASS: core profile, attention policy, self model, eval prompts, 5 world files |
| `uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root /tmp/tmp.uxaOHYrZuE wake --reason deterministic-loop-test` | PASS: 1 probe, 3 raw events, 3 observations, 1 concern, 2 memories, 2 actions, 2 outcomes, policy v3, 1 wake request |
| `uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root /tmp/tmp.uxaOHYrZuE review` | PASS: review activated 1 concern and kept core stable |
| `uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root /tmp/tmp.uxaOHYrZuE reflect` | PASS: no core proposal needed for small isolated state |
| `AGENT_LLM_PROVIDER=state_sensitive_mock uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root /tmp/tmp.uxaOHYrZuE eval run --prompt-id 1` | PASS: replay run saved with state-sensitive mock |
| `AGENT_LLM_PROVIDER=state_sensitive_mock uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root /tmp/tmp.uxaOHYrZuE chat "Should we implement now?"` | PASS: state-sensitive response and response_trace_id saved |
| `uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root /tmp/tmp.uxaOHYrZuE inspect digest-decisions` | PASS: concern / discard / memory decisions inspectable |
| `uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root /tmp/tmp.uxaOHYrZuE inspect probes` | PASS: policy_selection ranking and skipped sources inspectable |
| `uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root /tmp/tmp.uxaOHYrZuE inspect attention-policy` | PASS: outcome evidence shown on policy event |
| `uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root /tmp/tmp.uxaOHYrZuE inspect outcomes` | PASS: outcome attention effect inspectable |
| `uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root /tmp/tmp.uxaOHYrZuE inspect wake-requests` | PASS: wake request inspectable |
| `uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root /tmp/tmp.uxaOHYrZuE inspect traces` | PASS: selected memories / concerns / modes / prompt summary inspectable |

## Automated Test Results

`uv run --python /home/penne/.local/bin/python3.12 pytest`

```text
52 passed, 1 warning in 0.88s
```

`./scripts/check-docs.sh`

```text
Checked 5 files
PASS todo _evals/validator-fixtures/todo/valid/basic.md
PASS todo _evals/validator-fixtures/todo/invalid/missing-title.md failed as expected
PASS todo _evals/validator-fixtures/todo/invalid/malformed-heading.md failed as expected
PASS todo _evals/validator-fixtures/todo/invalid/missing-qa-for-medium.md failed as expected
PASS todo _evals/validator-fixtures/todo/invalid/mismatched-heading-id.md failed as expected
PASS qa _evals/validator-fixtures/qa/valid
PASS qa _evals/validator-fixtures/qa/invalid/missing-invariant.md failed as expected
PASS qa _evals/validator-fixtures/qa/invalid/status-verdict-mismatch.md failed as expected
PASS qa _evals/validator-fixtures/qa/invalid/verification-in-progress-status.md failed as expected
PASS qa _evals/validator-fixtures/qa/invalid/verification-missing-test-plan-reference.md failed as expected
PASS qa _evals/validator-fixtures/qa/invalid/qa-archive-path.md failed as expected
```

Coverage added in this pass:

- `tests/test_closed_loop_hardening.py`: digest decision persistence, lifecycle transitions, successor creation, identity reinforcement/separation, policy-driven probe source selection, outcome-driven policy event, state-sensitive replay drift.
- `tests/test_discord_integration.py`: Discord feedback creates policy event with outcome evidence.
- `tests/test_llm.py`: `state_sensitive_mock` factory remains offline.
- `.github/workflows/pytest-ci.yml`: Python 3.12 / `uv sync --locked` / `uv run pytest` / runner-temp verification output with `AGENT_LLM_PROVIDER=mock` and Discord disabled.

## Manual QA Results

- `inspect digest-decisions` で concern / discard / memory の判断理由と score snapshot を確認した。
- `inspect probes` で `policy_selection` の candidate ranking、selected source、skipped source reason を確認した。
- `inspect attention-policy` で outcome evidence 付きの policy event を確認した。
- `inspect outcomes` と `inspect wake-requests` で action outcome と follow-up wake request を確認した。
- `inspect traces` で state-sensitive chat response の selected memories / concerns / modes を確認した。

## Evidence

- Discard decision with reason: `inspect digest-decisions` showed `digest_decision#2 discard obs#2 raw#2`, scores `salience=0.25`, `self_relevance=0.35`, reason `low signal across salience, uncertainty, and self relevance`.
- Concern transition: verification report `natural_lifecycle_probe` recorded `dormant=1`, then `resolved=1`, then `archived=1`, then `successors=1`.
- Outcome-driven policy event: `inspect attention-policy` showed `event#2 outcome_preference_adjusted source_preferences.local_file` with `outcome_evidence: [1]`.
- Policy-driven probe: `inspect probes` showed `policy_selection.selected_source_key=local_file`, selected score `0.8`, ranked alternatives, and skipped reasons such as `lower_policy_rank` and `no_memories_available`.
- Replay text drift: report `replay_comparison[0]` has `response_changed=true` and `state_changed=true`; before response had `selected_concerns=0 selected_memories=0`, after response had `selected_concerns=4 selected_memories=5`.
- Core stability: report `core_profile_stability.content_unchanged_after_reflect=true`, `content_unchanged_after_all=true`, `locked=true`.

## Acceptance Criteria Coverage

- AC-001: PASS. `digest_decisions` table exists and wake / Discord ingest / verification fixtures persist decisions with source observation/raw event, reason, confidence, score snapshots, and related concern ids.
- AC-002: PASS. Concern lifecycle helpers and review flow cover seed, active, dormant, resolved, archived, and successor events with auditable deltas.
- AC-003: PASS. Deterministic identity layer reinforces same unresolved tension and separates unrelated observations.
- AC-004: PASS. `attention_policy` source preferences affect probe ranking and selected source; probe metadata records ranking and skipped sources.
- AC-005: PASS. Outcome evidence creates bounded `attention_policy_events` with `evidence_outcome_ids_json`; Discord feedback path is covered.
- AC-006: PASS. `state_sensitive_mock` produces deterministic response text differences from selected state without provider calls.
- AC-007: PASS. Replay verification distinguishes selected-state drift, response-text drift, and core stability.
- AC-008: PASS. Core profile remains unchanged; existing Discord tests pass without live credentials.
- AC-015: PASS. `Pytest CI` runs on `main` pull requests and `main` / `dev` pushes, installs dependencies through `uv sync --locked`, runs `uv run pytest`, and writes deterministic verification output to runner temp with mock/offline provider and Discord disabled.

## Invariant Coverage

- INV-001 / INV-002: PASS. Existing local file safety tests still pass.
- INV-003: PASS. Existing Pydantic LLM validation tests still pass.
- INV-004: PASS. Concern events include reason and transition deltas, including previous/new state and evidence ids.
- INV-005: PASS. Policy events include reason, target field, observation/action/outcome evidence as applicable.
- INV-006: PASS. Core profile is not mutated by wake / review / reflection / replay.
- INV-007 / INV-008: PASS. Chat and replay selected state remains traced.
- INV-009: PASS. Digest decisions store source ids and score snapshots.
- INV-010: PASS. Lifecycle events store previous/new state and evidence ids in `delta_json`.
- INV-011: PASS. Probe metadata stores candidate ranking and skipped source reasons.
- INV-012: PASS. Outcome-driven policy event stores outcome id evidence.
- INV-013: PASS. State-sensitive replay changes response text without changing core profile.

## Deferred / Not Covered

None for this deterministic closed-loop scope.

## Residual Risks

None

## Notes

- Concern lifecycle and identity remain intentionally heuristic and deterministic, not semantic embeddings.
- SQLite schema migration framework is still not introduced; this PoC expects fresh `--project-root` verification or `create_all` for new tables.
- Web remains a deterministic stub and does not prove real network search behavior.

## Follow-up TODOs

None required for this PASS. Future work can be tracked separately for real provider/web/dashboard work.
