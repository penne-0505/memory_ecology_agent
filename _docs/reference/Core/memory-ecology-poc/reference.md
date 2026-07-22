---
title: Memory Ecology Agent PoC Reference
status: active
draft_status: n/a
created_at: 2026-05-29
updated_at: 2026-06-02
references:
  - "_docs/intent/Core/memory-ecology-poc/decision.md"
  - "_docs/plan/Core/memory-ecology-poc/plan.md"
  - "_docs/qa/Core/memory-ecology-poc/test-plan.md"
  - "_docs/qa/Core/memory-ecology-poc/verification.md"
related_issues: []
related_prs: []
---

## Overview

Memory Ecology Agent PoC は、ローカル CLI と SQLite で probe / raw event / observation / digest decision / concern / memory / action / outcome / attention policy / response trace / replay run を保存する trace-first 実験である。

## Package Layout

- `app/main.py`: `python -m app.main` entrypoint。
- `app/cli/commands.py`: argparse command routing。
- `app/config.py`: DB、`world/`、`agent_workspace/` の path 設定。
- `app/db/models.py`: source prompt の table set を SQLAlchemy 2.x model として定義。
- `app/db/init_db.py`: schema init と seed。
- `app/adapters/local_files.py`: `world/` read-only adapter。
- `app/adapters/llm.py`: `LLMClient`, `MockLLMClient`, provider factory, OpenAI / Claude / Gemini / OpenRouter clients。
- `app/adapters/web_search.py`: Web search interface / stub。
- `app/cognition/`: probe planning、observation extraction、digest、concern / memory / attention policy / action / context management。
- `app/runtime/`: chat / wake / review / reflection cycles。
- `app/eval/replay.py`: replay eval run / compare。
- `tests/`: AC / INV に対応する pytest。

## CLI Commands

```bash
python -m app.main init
python -m app.main seed
python -m app.main wake --reason cron
python -m app.main review
python -m app.main reflect
python -m app.main chat "Should we implement now?"
python -m app.main eval run
python -m app.main eval compare --prompt-id 1
python -m app.main inspect concerns
python -m app.main inspect probes
python -m app.main inspect observations
python -m app.main inspect digest-decisions
python -m app.main inspect digest-proposals
python -m app.main inspect attention-policy
python -m app.main inspect actions
python -m app.main inspect outcomes
python -m app.main inspect wake-requests
python -m app.main inspect traces
python -m app.main inspect llm-provider
python -m app.main inspect observation-extractor
python -m app.main llm smoke
```

`--project-root <path>` を渡すと、DB / world / workspace を指定 root 配下へ切り替える。

## Data Model Notes

- JSON fields are stored as TEXT and read/written through `app/db/json_utils.py`.
- current state tables (`concerns`, `attention_policies`, `memories`) and event / trace tables (`concern_events`, `attention_policy_events`, `response_traces`, `replay_runs`) are intentionally separate.
- `digest_decisions` stores the final decision for each observation, including concern / memory / discard / action candidates, reason, score snapshots, source observation/raw event, related concern ids, and optional LLM proposal comparison metadata.
- `digest_decision_proposals` stores LLM-backed digest proposals when `AGENT_DIGEST_DECIDER=llm_shadow` or `llm_assisted` is enabled. It stores provider/model, prompt version, proposed decision, short reason/evidence, filtered related concern ids, schema/fallback/error flags, and a raw response hash only. It does not store raw provider response text.
- `input_probes.budget_json` and `budget_used_json` include `policy_selection` metadata with candidate ranking, selected source, exploration randomness, and skipped source reasons.
- `core_profiles.locked` is true in seed data. Runtime cycles do not mutate `core_profiles`.
- `attention_policies` creates a new version for a bounded preference adjustment.

## Wake Cycle

1. `probe_planner.plan_probes` selects a bounded local probe.
2. `local_files.execute_local_probe` reads safe files under `world/`.
3. `events.persist_raw_event` stores raw events.
4. `observation_extractor` creates observations. The default extractor is deterministic; `AGENT_OBSERVATION_EXTRACTOR=llm` can opt into LLM-backed observation proposals.
5. `digestor` creates the deterministic digest decision. If `AGENT_DIGEST_DECIDER=llm_shadow`, `digest_decider` also asks the LLM for a proposal and stores it separately.
6. `digestor.persist_digest_decision` writes every final concern / memory / discard / action decision to `digest_decisions`.
7. `concern_manager` creates, activates, reinforces, reactivates, resolves, archives, or links successor concerns and writes `concern_events`.
8. `memory_manager` creates lightweight observation digest memories.
9. `attention_policy.update_policy_from_observations` and `update_policy_from_outcomes` create bounded policy versions and `attention_policy_events`.
10. `action_planner` writes an internal note and a wake request when concerns exist.

## Concern Lifecycle

Concern identity is deterministic and local: titles are normalized into an `identity_key` in `object_json`, canonical object/tension data is compared, and token overlap is used as a fallback. No embeddings or provider calls are used.

Supported lifecycle paths:

- `seed -> active`: related observation or review threshold.
- `active -> dormant`: low activation, low unresolvedness, and low pressure.
- `dormant -> active`: related observation reactivates the concern.
- `active/dormant/seed -> resolved`: outcome evidence with closure modes such as `completed`, `answered`, `accepted`, `abandoned`, `absorbed`, `transformed`, `superseded`, or `irrelevant`.
- `resolved -> archived`: resolved low-activation concern after a later review.
- successor: transformed / absorbed / superseded outcomes create a new seed concern and link `successor_concern_id`.

## Chat Cycle

1. User message is saved as a `raw_event`.
2. `context_builder` selects recent memories, active concerns, and latest attention policy.
3. Concern modes are assigned as `mention`, `influence`, or `ignore`.
4. `create_llm_client(settings)` selects the configured provider. The default provider is `mock`.
5. A `respond` action and `response_trace` are saved.

## LLM Providers

Provider selection is environment-variable based. API key values must not be committed, logged, or copied into docs.

| Provider | Selector | Required key | Model env |
| --- | --- | --- | --- |
| Mock | `AGENT_LLM_PROVIDER=mock` | None | None |
| State-sensitive mock | `AGENT_LLM_PROVIDER=state_sensitive_mock` | None | None |
| OpenAI | `AGENT_LLM_PROVIDER=openai` | `OPENAI_API_KEY` | `OPENAI_MODEL` or `AGENT_LLM_MODEL` |
| Claude | `AGENT_LLM_PROVIDER=claude` | `ANTHROPIC_API_KEY` | `ANTHROPIC_MODEL` or `AGENT_LLM_MODEL` |
| Gemini | `AGENT_LLM_PROVIDER=gemini` | `GEMINI_API_KEY` | `GEMINI_MODEL` or `AGENT_LLM_MODEL` |
| OpenRouter | `AGENT_LLM_PROVIDER=openrouter` | `OPENROUTER_API_KEY` | `OPENROUTER_MODEL` or `AGENT_LLM_MODEL` |

Implementation notes:

- OpenAI and OpenRouter use Chat Completions compatible `POST /chat/completions` with `max_completion_tokens`.
- Claude uses Anthropic Messages API `POST /messages` with `anthropic-version: 2023-06-01`.
- Gemini uses Google AI Studio Gemini `generateContent` with `x-goog-api-key`.
- `complete_json` asks for JSON text, extracts plain or fenced JSON, and validates it with Pydantic.
- Provider request bodies, provider response bodies, and API key headers are not written to DB or provider error messages.
- `StateSensitiveFakeLLMClient` is deterministic and offline. It changes response text based on selected concerns, memories, and attention policy so replay can prove response-text drift without a real provider.

## LLM Observation Extraction

Observation extraction is controlled separately from provider selection.

| Env var | Default | Values | Meaning |
| --- | --- | --- | --- |
| `AGENT_OBSERVATION_EXTRACTOR` | `deterministic` | `deterministic`, `llm` | Selects the extraction mode used by wake cycle. |
| `AGENT_OBSERVATION_EXTRACTOR_FALLBACK` | `deterministic` | `deterministic`, `error` | Chooses whether LLM extraction failures fall back or raise. |

The LLM extractor is proposal-only. It returns up to five validated
`ObservationDraft` proposals with summary, entities, bounded scores,
`possible_disposition`, rationale, short evidence quote, and confidence.
It does not directly create or update
digest decisions, concerns, memories, attention policies, core profiles,
actions, outcomes, Discord state, or Web search.

Validation and fallback behavior:

- provider output must be JSON matching the observation proposal schema;
- score fields are clamped to `0.0..1.0`;
- unsupported dispositions are rejected by schema validation;
- summary, rationale, and evidence quote are length-bounded;
- provider/config/JSON/schema failures use deterministic fallback by default;
- fallback trace stores only extractor/provider/failure-class metadata, not raw provider responses.

Trace behavior:

- `observations.rationale` states whether the observation came from deterministic extraction, LLM proposal, or deterministic fallback.
- `digest_decisions.metadata_json` includes `extractor`, `provider`, `fallback`, `proposal_index`, and when applicable `requested_extractor`, `fallback_reason`, and `fallback_provider`.

Manual OpenRouter test, outside CI/default behavior:

```bash
export AGENT_OBSERVATION_EXTRACTOR=llm
export AGENT_OBSERVATION_EXTRACTOR_FALLBACK=deterministic
export AGENT_LLM_PROVIDER=openrouter
export AGENT_LLM_MODEL=deepseek/deepseek-v4-pro
export OPENROUTER_API_KEY="..."
tmpdir=$(mktemp -d)
python -m app.main --project-root "$tmpdir" init
python -m app.main --project-root "$tmpdir" seed
python -m app.main --project-root "$tmpdir" wake --reason manual-llm-observation-test
python -m app.main --project-root "$tmpdir" inspect digest-decisions
```

## LLM Digest Decision Proposals

Digest decision proposal mode is controlled separately from observation extraction.

| Env var | Default | Values | Meaning |
| --- | --- | --- | --- |
| `AGENT_DIGEST_DECIDER` | `deterministic` | `deterministic`, `llm_shadow`, `llm_assisted` | Selects whether LLM digest proposals are requested. |
| `AGENT_DIGEST_PROPOSAL_CONFIDENCE_THRESHOLD` | `0.75` | float | Reserved threshold for future conservative assisted adoption. |

Behavior:

- `deterministic`: default. No provider call and no proposal rows.
- `llm_shadow`: deterministic digest remains the final decision; the LLM proposal is stored in `digest_decision_proposals` and comparison metadata is stored on the final `digest_decisions` row.
- `llm_assisted`: recognized but conservatively scaffolded in this task. Final decisions remain deterministic until a later quality evaluation defines adoption rules.

Validation and fallback behavior:

- provider output must parse as JSON matching the digest proposal schema;
- `decision` and `alternative_decision` must be one of `concern_candidate`, `memory_candidate`, `discard`, `action_candidate`, or `no_op`;
- `confidence` is clamped to `0.0..1.0`;
- reason, evidence summary, and evidence quote are length-bounded;
- unknown `related_concern_ids` are dropped;
- secret-like output is rejected and stored without the unsafe text;
- provider/config/JSON/schema failures create rejected proposal rows and final deterministic digest decisions continue;
- raw provider response text is not persisted.

Prompt rubric boundary:

- prompt version `digest_decision_llm.v2` treats `concern_candidate` as unresolved tension / open-loop evidence, not merely important content;
- stable user feedback, project requirements, durable facts, and explanatory project framing are usually `memory_candidate` unless they create a live unresolved tension;
- low-signal repetitive ambient material is `discard`, but short user feedback, safety constraints, and project requirements must not be discarded just because they are short;
- `action_candidate` is a rare weak suggestion only, and LLM `action_candidate` must never be adopted automatically;
- `should_apply` is advisory and is limited to high-confidence memory/discard proposals without boundary risk flags;
- boundary flags such as `manual_follow_up`, `safety_boundary`, `core_profile_boundary`, `self_model_boundary`, `discord_mode_boundary`, `unknown_context`, and `low_confidence` force conservative handling.

Inspection:

```bash
python -m app.main inspect digest-decisions
python -m app.main inspect digest-proposals
python -m app.main inspect observation-extractor
```

Manual OpenRouter digest shadow test, outside CI/default behavior:

```bash
export AGENT_DIGEST_DECIDER=llm_shadow
export AGENT_LLM_PROVIDER=openrouter
export AGENT_LLM_MODEL=deepseek/deepseek-v4-pro
export OPENROUTER_API_KEY="..."
tmpdir=$(mktemp -d)
python -m app.main --project-root "$tmpdir" init
python -m app.main --project-root "$tmpdir" seed
python -m app.main --project-root "$tmpdir" wake --reason manual-llm-digest-shadow-test
python -m app.main --project-root "$tmpdir" inspect digest-decisions
python -m app.main --project-root "$tmpdir" inspect digest-proposals
```

`llm smoke` is a bounded provider connectivity check outside the cognition loop.
It uses the marker prompt `provider-smoke-ok`, a low max-token budget, a short
timeout, and deterministic temperature where the provider adapter supports it.
For OpenRouter smoke only, it also sends `reasoning: {"effort": "none",
"exclude": true}` so reasoning-capable models can return the marker within the
small completion budget. Normal OpenRouter `chat` / `eval run` calls do not add
this smoke-specific payload.

Selection behavior:

- `AGENT_LLM_PROVIDER=mock` runs an offline marker smoke.
- If `AGENT_LLM_PROVIDER` names one real provider, that provider's key and model
  env vars are required before the network call is attempted.
- If no provider is explicit and no real credential exists, the command writes a
  skipped action/outcome and prints `SKIPPED: no real provider credentials configured`.
- If no provider is explicit and multiple real provider credentials exist, the
  command fails and asks for explicit `AGENT_LLM_PROVIDER`.
- If exactly one real credential exists and no provider is explicit, the command
  may auto-select that provider and records `selected_from_credentials=true`.

Trace behavior:

- `actions.action_type` is `llm_provider_smoke`.
- `actions.payload_json` stores provider, model, command path, success/failure/skipped,
  marker presence, latency, usage metadata when available, sanitized error class/message,
  and creation time.
- `outcomes` stores the smoke result with `direct_effect=none`.
- API key values, Authorization headers, raw HTTP headers, raw request payloads,
  and raw response payloads are not stored.
- The command does not update `core_profiles`, Discord mode, Web search, wake cycle,
  review cycle, reflection cycle, or normal CI behavior.

## Replay Eval

`seed` registers four eval prompts. `eval run` answers them with current state and stores selected concerns / memories / attention policy in `replay_runs`. `eval compare --prompt-id <id>` prints previous runs for the same prompt. With `state_sensitive_mock`, replay can distinguish selected-state drift from deterministic response-text drift while `core_profiles` remains unchanged.

## Safety Boundaries

- `world/` is read-only and the only local file input surface.
- `agent_workspace/` is the only file workspace written by runtime actions.
- The adapter skips path traversal, symlink traversal, binary files, and secret-like names such as `.env`, token, credential, private, password, and api key.
- Web search does not call the network in this PoC.
- LLM JSON is validated with Pydantic; validation failures raise before state mutation.
- Real LLM provider keys are read from environment variables only.

## Known Limitations

- The cognition modules are heuristic v0 implementations.
- There is no dashboard or daemon scheduler.
- Web search is stubbed.
- LLM streaming, tool call, multimodal input, and provider-specific structured output are not implemented.
- SQLite schema migrations are not implemented; this PoC uses `create_all`.
