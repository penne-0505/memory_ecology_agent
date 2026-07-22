---
title: Memory Ecology Agent PoC Verification Report
status: active
draft_status: n/a
created_at: 2026-05-30
updated_at: 2026-05-30
references:
  - "_docs/intent/Core/memory-ecology-poc/decision.md"
  - "_docs/plan/Core/memory-ecology-poc/plan.md"
  - "_docs/qa/Core/memory-ecology-poc/test-plan.md"
  - "_docs/qa/Core/memory-ecology-poc/verification.md"
  - "_docs/reference/Core/memory-ecology-poc/reference.md"
  - "_evals/fixtures/memory_ecology_sample_world/world/notes/unfinished_agent_idea.md"
  - "_evals/scripts/verify_memory_ecology_poc.py"
  - "_evals/reports/memory_ecology_verification_2026-05-30.json"
related_issues: []
related_prs: []
---

# Memory Ecology Agent PoC Verification Report

## 1. Summary

- Verdict: PARTIAL
- 総評: schema と wake/chat/replay の trace はかなり揃っているが、discard 判断の永続化、自然な concern lifecycle、attention policy による probe 選別、replay 応答変容の実証が足りず、仮説検証は部分成立に留まる。

## 2. What was verified

- Date command: `date` -> `Sat May 30 03:01:57 JST 2026`
- Static review: `README.md`, `QUICKSTART.md`, `TODO.md`, `_docs/standards/*`, `_docs/plan/Core/memory-ecology-poc/plan.md`, `_docs/intent/Core/memory-ecology-poc/decision.md`, `_docs/qa/Core/memory-ecology-poc/test-plan.md`, `_docs/reference/Core/memory-ecology-poc/reference.md`, `app/**`, `tests/**`, `app/prompts/**`
- Automated checks: `uv run --python /home/penne/.local/bin/python3.12 pytest` -> `23 passed`; `./scripts/check-docs.sh` -> PASS
- Verification command: `uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/verify_memory_ecology_poc.py --output _evals/reports/memory_ecology_verification_2026-05-30.json`
- CLI trace checks: `inspect probes`, `inspect concerns`, `inspect attention-policy`, `inspect traces`, `eval compare --prompt-id 1` against `/tmp/memory-ecology-verify-xkzfgbuv`
- Sample world: `_evals/fixtures/memory_ecology_sample_world/world/**`
- Evidence DB: `/tmp/memory-ecology-verify-xkzfgbuv/data/agent.db`
- Mocked: LLM used `MockLLMClient`; web search used `WebSearchAdapter` stub. No external API key or network search was used.

## 3. Static architecture check

| concept | implemented? | location | notes |
| --- | --- | --- | --- |
| raw_events | yes | `app/db/models.py:22`, `app/runtime/events.py:15` | source_type, event_type, payload, content hash, content text are persisted. |
| input_probes | yes | `app/db/models.py:35`, `app/cognition/probe_planner.py:23` | rationale, expected_gain, source_type, exploration_mode, budget, status are persisted. |
| observations | partial | `app/db/models.py:53`, `app/cognition/observation_extractor.py:46` | observation rationale persists, but digest/adopt/discard decision reason is not persisted. |
| concerns | partial | `app/db/models.py:72`, `app/cognition/concern_manager.py:45` | seed/active works; dormant/resolved/archived/successor fields exist but no natural runtime transitions. |
| concern_events | yes | `app/db/models.py:105`, `app/cognition/concern_manager.py:111` | seeded/reinforced reason and delta persist. Manual fixture proved other event types can be stored. |
| memories | yes | `app/db/models.py:118`, `app/cognition/memory_manager.py:11` | observation digest memories persist with source ids and related concern ids. |
| actions | yes | `app/db/models.py:206`, `app/cognition/action_planner.py:23`, `app/runtime/chat_cycle.py:34` | wake actions and chat respond actions persist. |
| outcomes | partial | `app/db/models.py:220`, `app/cognition/action_planner.py:57` | wake outcomes persist; chat feedback outcome required manual verification fixture. |
| attention_policies | yes | `app/db/models.py:134`, `app/db/models.py:288` | first-class state with source/salience/concern/action/response preferences. |
| attention_policy_events | partial | `app/db/models.py:152`, `app/cognition/attention_policy.py:70` | event reason and evidence fields persist; natural updates use observation evidence, not outcome evidence. |
| core_profiles | yes | `app/db/models.py:168`, `app/db/init_db.py:89` | locked seed profile exists and runtime cycles do not mutate it. |
| core_change_proposals | partial | `app/db/models.py:178`, `app/runtime/reflection_cycle.py:41` | proposals exist, but creation is count-based rather than tied to dangerous core-change input content. |
| self_model_snapshots | partial | `app/db/models.py:190`, `app/runtime/reflection_cycle.py:26` | seed plus reflection threshold update; low-frequency policy is heuristic. |
| wake_requests | yes | `app/db/models.py:232`, `app/cognition/action_planner.py:78`, `app/runtime/scheduler.py:9` | scheduler is modeled through requests; no direct cron mutation. |
| response_traces | yes | `app/db/models.py:250`, `app/runtime/chat_cycle.py:47` | selected memories, concerns, attention policy, concern modes, prompt summary persist. |
| eval_prompts | yes | `app/db/models.py:264`, `app/db/init_db.py:30` | four seeded prompts exist. |
| replay_runs | partial | `app/db/models.py:274`, `app/eval/replay.py:15` | selected state persists, but mock responses did not vary with internal state. |

## 4. Runtime trace check

| wake | probe | observation | concern update | action/outcome | attention policy update |
| --- | --- | --- | --- | --- | --- |
| 1 | `local_file world/`, `random_environment_sample`, rationale includes `policy=1` | 10 raw events -> 10 observations | 7 concerns seeded | 2 actions, 2 outcomes, 1 wake_request | policy v2, `local_file` 0.45 -> 0.50 |
| 2 | `local_file world/`, `concern_driven`, related concern `[6]` | 10 raw events -> 10 observations | same 7 concerns reinforced | 2 actions, 2 outcomes, 1 wake_request | policy v3, `local_file` 0.50 -> 0.55 |
| 3 | `local_file world/`, `concern_driven`, related concern `[6]` | 10 raw events -> 10 observations | same 7 concerns reinforced | 2 actions, 2 outcomes, 1 wake_request | policy v4, `local_file` 0.55 -> 0.60 |

Counts after verification: `raw_events=34`, `input_probes=3`, `observations=32`, `concerns=8`, `concern_events=25`, `memories=30`, `actions=10`, `outcomes=8`, `attention_policies=5`, `attention_policy_events=4`, `wake_requests=3`, `response_traces=2`, `replay_runs=8`.

Observation dispositions in persisted rows were `concern_candidate=21`, `memory_candidate=11`; no persisted observation had `discard`.

## 5. Concern lifecycle check

- Natural seed example: concern `6`, title `PoC risk log Path traversal and secret leakage would invalidate`, opened with reason `Observation was classified as unresolved and salient enough to hold as a seed concern.`
- Natural active example: concern `6` was reinforced by observations `[9, 19, 29]`; recurrence reached `0.4`, activation reached `3.47`, and concern count stayed `[7, 7, 7]` over three wakes, so identical repeated observations did not create unbounded duplicates.
- Manual fixture only: `_evals/scripts/verify_memory_ecology_poc.py` inserted `resolved`, `dormant`, `archived`, and `successor_linked` events through action `10`. This proves the schema can trace these states, not that runtime lifecycle can naturally perform them.
- Identity behavior: current merge key is exact generated title (`app/cognition/concern_manager.py:47`). This prevents duplicates for identical repeated file content, but semantically similar reworded topics may split; unrelated notes containing key terms can become concerns, as `Random daily log...` became concern `3`.

## 6. Attention policy check

- Before wake: `source_preferences.local_file=0.45`, `web=0.15`.
- After three wake cycles: `local_file=0.60`, `web=0.15`.
- Component web-noise check: `WebSearchAdapter` stub plus `update_policy_from_observations(..., "web_search")` changed `web=0.15 -> 0.13`.
- Event examples: event `1` changed `source_preferences.local_file` by `+0.05` with evidence observations `[1, 4, 5, 6, 7, 9, 10]`; event `4` changed `source_preferences.web` by `-0.02`, but had no evidence observation ids because the code stores only useful observations as evidence.
- Boundedness: per-cycle local update is capped at `0.05` in `app/cognition/attention_policy.py:35`.
- Influence gap: next probe after web weakening was still `source_type=local_file` and `exploration_mode=concern_driven`; source preference values are not yet used to choose probe source. Response traces include policy v4, but mock responses do not prove response selection changed because of that policy.

## 7. Core stability check

- `core_profiles` stayed at one row; `core_profile_stability.content_unchanged_after_reflect=true`, `content_unchanged_after_all=true`, `locked=true`.
- Dangerous core-pressure input existed at `_evals/fixtures/memory_ecology_sample_world/world/projects/core_pressure.md`.
- `core_change_proposals` contained one proposal: `Consider whether concern saturation should affect core narrative.`
- Gap: proposal creation came from active concern count in `app/runtime/reflection_cycle.py:41`, not from detecting the specific dangerous instruction to rewrite core or assert aggressively.

## 8. Response trace and replay check

- Chat generated 2 `response_traces`.
- Each trace selected 5 memories and 4 concerns; concern `6` was `mention`, concerns `4/5/7` were `influence`, and concerns `1/2` were `ignore`. Active concerns were not all mentioned.
- Trace policy version was v4 with `local_file=0.60`.
- Replay before/after for prompt ids `1..4`: `state_changed=true`, policy version `1 -> 4`, selected concerns `0 -> 4`, memories `0 -> 5`.
- Replay response text did not change for any prompt (`response_changed=false`) because `MockLLMClient.complete_text` only echoes a fixed system hint and user text. This means replay currently verifies state trace drift, not observable answer drift.
- User feedback outcome was added only by verification fixture (`feedback_outcome_id=7`); `chat_cycle` itself does not create an outcome from user reaction.

## 9. Safety boundary check

- Local read boundary: `execute_local_probe` resolves requested path under `world_root`, rejects path traversal, rejects symlinks, skips secret-like names and binary files (`app/adapters/local_files.py:58`, `:76`, `:84`, `:97`).
- Tests: `tests/test_local_files.py` covers traversal, symlink traversal, `.env`, and binary skip.
- Write boundary: runtime action writes `agent_workspace/notes/latest-wake-summary.md` only through `_safe_workspace_path` (`app/cognition/action_planner.py:16`). Seed writes sample world files (`app/db/init_db.py:136`).
- Secrets: `.env` is not read; real provider API keys are read from environment variables only (`app/adapters/llm.py:305`) and provider error tests check sanitized messages.
- Web: no real network search in PoC; `WebSearchAdapter` is a stub with query cap (`app/adapters/web_search.py:18`).
- Scheduler: no cron mutation; `WakeRequest` rows are created and `should_run_wake` only evaluates timing.
- Caveat: `AGENT_WORLD_ROOT` is configurable; if configured to a broad directory, the adapter enforces that configured root, not necessarily repository `world/`.

## 10. Gaps and risks

Critical:

- Replay cannot currently prove response transformation under internal-state change when using the default mock; selected state changes, but answer text does not.
- Concern lifecycle beyond seed/reinforced/active is not naturally implemented in runtime cycles; resolved/dormant/archived/successor were only manual fixture events.
- Adopt/discard digest decisions are not persisted as first-class trace rows. Low-signal fixture returned digest `discard`, but `persisted_digest_reason=false`.

Important:

- `attention_policy` changes are persisted, but probe planning does not use source preferences to select web/local/memory sources.
- Policy events do not currently use outcome evidence in natural wake updates.
- Core-change proposals are generic active-count reactions, not evidence-specific proposals from dangerous core rewrite instructions.
- Concern identity uses exact title matching; this is traceable but brittle.
- `review_cycle` is count-only and `reflection_cycle` is threshold-only.
- `chat_cycle` records response action and trace, but not a natural outcome/user feedback loop.

Nice-to-have:

- CLI lacks `inspect observations`, `inspect actions`, and `inspect outcomes`, so some evidence still requires JSON or DB inspection.
- Web search stub can test boundaries but not real query budget/rationale under external noise.
- There is no ablation run proving policy/memory/concern removal changes response behavior.

## 11. Recommended next actions

1. Add a persisted `digest_decisions` trace or equivalent fields so concern/memory/action/discard decisions and reasons survive after wake.
2. Implement explicit concern lifecycle transition helpers with events for resolved, dormant, archived, and successor cases, plus tests using repeated and resolved inputs.
3. Add a deterministic state-sensitive replay LLM stub so replay can prove response changes without relying on real LLM randomness.
4. Make probe planning consume `attention_policies.source_preferences` and record why local/web/memory was selected or skipped.
5. Connect action outcomes and chat feedback to attention policy update evidence, so `attention_policy_events.evidence_outcome_ids_json` is populated in natural cycles.
