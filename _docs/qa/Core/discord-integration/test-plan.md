---
title: "QA Test Plan: Discord Integration Adapter"
status: active
draft_status: n/a
qa_status: planned
risk: High
created_at: 2026-06-02
updated_at: 2026-06-02
references:
  - "_docs/intent/Core/discord-integration/decision.md"
  - "_docs/plan/Core/discord-integration/plan.md"
  - "_evals/prompts/discord-integration.md"
related_issues: []
related_prs: []
---

# QA Test Plan: `Discord Integration Adapter`

## Source of Intent

- TODO: `Core-Feat-7`
- Plan: `_docs/plan/Core/discord-integration/plan.md`
- Intent: `_docs/intent/Core/discord-integration/decision.md`
- Prompt source: `_evals/prompts/discord-integration.md`

## Quality Goal

Discord can be enabled as an observation, input, and control adapter while the existing runtime and SQLite DB remain canonical. The implementation must prove mode separation, self-ingestion prevention, explicit channel ingestability, traceable mutations, and safe autonomous posting behavior without requiring live Discord credentials for automated tests.

## Acceptance Criteria

- AC-001: Discord runtime mode is visible and enforceable through config/status output.
- AC-002: channel role and ingestability are explicit and testable.
- AC-003: self-ingestion prevention rejects bot messages and non-ingestable trace/admin surfaces.
- AC-004: allowed user messages in ingest-enabled mode become `raw_events` with Discord metadata.
- AC-005: command-enabled dispatch exposes required commands and mutating commands create trace rows.
- AC-006: autonomous posting is feature-gated, rate-limited, mute-aware, allowlisted, logged, and user replies/reactions can become outcomes when ingestion is enabled.
- AC-007: token/secret handling and attachment limits prevent unsafe persistence or posting.
- AC-008: existing CLI/core behavior remains compatible when Discord is disabled.

## Intent-derived Invariants

- INV-001: Discord disabled or `observe_only` mode never ingests ordinary Discord messages into `raw_events`.
- INV-002: Bot-authored messages, trace/policy/eval/admin channel messages, and bot trace output are not ingestable by default.
- INV-003: Ingested Discord events include author type, channel role, ingestability, source, Discord IDs, thread metadata, and timestamps.
- INV-004: Mutating commands create `Action` and `Outcome` rows or a documented equivalent trace.
- INV-005: Autonomous posting cannot occur unless the mode, channel allowlist, mute state, and rate limit all allow it.
- INV-006: Discord feedback and commands do not directly mutate `core_profiles`.
- INV-007: Discord token and secrets are never persisted in DB payloads, docs, or logs.
- INV-008: Existing core CLI commands and tests work when Discord is disabled.
- INV-009: `discord doctor` reports live startup blockers without connecting to Discord or printing token values.

## Risk Assessment

- Risk level: High
- Risk rationale: Discord integration touches external API credentials, user input ingestion, command mutation, autonomous posting, and secret leakage boundaries.
- Regression risk: New config and dependency must not break existing CLI/core tests.
- Data safety risk: Attachments or Discord messages could accidentally ingest unsafe content without strict size/type/path checks.
- Security / privacy risk: Bot token and private trace channels must not leak into DB payloads, docs, or logs.
- UX risk: Status and trace output must be concise enough to use in Discord without dumping raw payloads.
- Agent misbehavior risk: It is easy to claim live Discord success from controller tests; verification must distinguish automated coverage from unverified live guild behavior.

## Test Strategy

- Unit: mode capability checks, channel-role decisions, metadata construction, attachment validation, renderers, rate limit/mute gates.
- Integration: controller methods run against temporary DB and assert `raw_events`, `actions`, `outcomes`, `wake_requests`, `replay_runs`, and selected state.
- E2E: CLI smoke for `discord status`, `discord doctor`, and existing core commands with Discord disabled.
- Manual QA: live bot startup, command sync, actual Discord message ingestion, and real channel posting only if credentials are available.
- Validator / static check: `uv run --python /home/penne/.local/bin/python3.12 pytest` and `./scripts/check-docs.sh`.
- Diff review: confirm token is env-only and no parallel source-of-truth state store is added.

## Test Matrix

| ID | Source | Requirement / Invariant | Test Type | Command / File | Expected Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| AC-001 | TODO | Runtime mode is visible and enforceable, including observe-only trace preparation. | unit/integration/CLI | `tests/test_discord_integration.py`; `discord cycle wake`; `discord cycle eval` | status includes mode; mode gates allow only intended capabilities; cycle trace posts are prepared for configured role channels. | planned |
| AC-002 | TODO | Channel role and ingestability are explicit. | unit | `tests/test_discord_integration.py` | channel config maps IDs to roles and ingest flags. | planned |
| AC-003 | TODO | Self-ingestion prevention rejects bot/trace/admin messages. | unit/integration | `tests/test_discord_integration.py` | rejected messages do not create `raw_events`. | planned |
| AC-004 | TODO | Allowed messages create raw events with metadata. | integration | `tests/test_discord_integration.py` | `raw_events` row payload has Discord source metadata. | planned |
| AC-005 | TODO | Required commands dispatch and mutating commands trace actions/outcomes. | integration | `tests/test_discord_integration.py` | `/wake`, `/feedback`, `/inject`, `/mute`, `/mode`, `/replay` create expected rows. | planned |
| AC-006 | TODO | Autonomous posting is gated, limited, logged, and user replies/reactions can become outcomes. | integration | `tests/test_discord_integration.py` | denied posts do not create actions; allowed post creates action/outcome; reply and reaction to recorded autonomous post create outcomes. | planned |
| AC-007 | TODO | Token/secret/attachment safety holds. | unit/diff review | `tests/test_discord_integration.py` / code review | token env var is not persisted; unsafe attachments are rejected. | planned |
| AC-008 | TODO | Existing core runtime remains compatible. | regression | `uv run --python /home/penne/.local/bin/python3.12 pytest` | Full pytest suite passes. | planned |
| INV-001 | intent | Disabled/observe-only does not ingest ordinary messages. | integration | `tests/test_discord_integration.py` | raw event count stays unchanged. | planned |
| INV-002 | intent | Bot and trace/admin channels are not ingestable by default. | integration | `tests/test_discord_integration.py` | rejection reason identifies author/channel gate. | planned |
| INV-003 | intent | Ingested events include required metadata. | integration | `tests/test_discord_integration.py` | payload has author/channel/source/message/thread timestamps. | planned |
| INV-004 | intent | Mutating commands are traceable. | integration | `tests/test_discord_integration.py` | `Action` and `Outcome` rows exist for mutating command. | planned |
| INV-005 | intent | Autonomous posting requires all gates and reply/reaction outcomes attach to the original post action. | integration | `tests/test_discord_integration.py` | rate limit/mute/channel denial paths and reply/reaction outcome mapping are covered. | planned |
| INV-006 | intent | Discord cannot directly mutate `core_profiles`. | integration | `tests/test_discord_integration.py` | core profile content is unchanged after commands. | planned |
| INV-007 | intent | Token/secrets are not persisted. | diff review/unit | `.env.example`, `app/adapters/discord_bot.py` | token loaded from env; status redacts token; payload has no token. | planned |
| INV-008 | intent | Discord disabled preserves existing behavior. | regression | existing test suite | non-Discord tests pass without Discord env vars. | planned |
| INV-009 | intent | Live-readiness diagnostics do not connect to Discord or print token values. | unit/CLI | `tests/test_discord_integration.py`; `discord doctor` | readiness gaps return non-zero when blocking; ready config omits token value. | planned |

## Manual QA Checklist

- [ ] Start the bot with a real `DISCORD_BOT_TOKEN` in `observe_only`.
- [ ] Run `discord doctor --mode observe_only --live` before live startup and resolve any `ERROR` rows.
- [ ] Confirm command registration/sync in the configured guild.
- [ ] Confirm `/status` responds without exposing secrets.
- [ ] Confirm an `agent_chat` user message ingests only in `ingest_enabled` or higher.
- [ ] Confirm trace/admin channel messages are ignored unless explicitly marked ingestable.
- [ ] Confirm autonomous posts appear only in allowlisted channels and are logged.

## Regression Checklist

- [ ] Existing `wake`, `chat`, `eval`, and `inspect` CLI commands still work.
- [ ] `pytest` passes without live Discord credentials.
- [ ] `scripts/check-docs.sh` passes.
- [ ] Verification clearly marks live Discord gaps if credentials are unavailable.

## High-risk Checklist

- [ ] Rollback or recovery path is documented.
- [ ] Data safety has been checked.
- [ ] Security / privacy implications have been checked.
- [ ] Failure mode is understood.

## Out of Scope

- Full production daemon supervision.
- Production daemon supervision and richer reaction analytics beyond recording outcome evidence.
- Rich embeds as a requirement; compact plain text is acceptable.
- Direct core profile rewrites from Discord.

## Open Questions

- Live Discord guild IDs and channel IDs are deployment-specific and not available in automated tests.
