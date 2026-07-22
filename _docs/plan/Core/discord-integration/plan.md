---
title: Discord Integration Adapter Plan
status: active
draft_status: n/a
created_at: 2026-06-02
updated_at: 2026-06-02
references:
  - "_docs/intent/Core/discord-integration/decision.md"
  - "_docs/qa/Core/discord-integration/test-plan.md"
  - "_evals/prompts/discord-integration.md"
related_issues: []
related_prs: []
---

## Overview

Discord integration is added as an adapter around the existing Memory Ecology Agent PoC. Discord must not become canonical state. The SQLite DB, runtime cycles, scheduler model, and CLI remain the source of truth; Discord exposes observation, explicit input, and controlled intervention surfaces.

## Scope

- Add config-level Discord settings for enabled state, runtime mode, guild, channels, admins, rate limits, mute, and attachment limits.
- Add runtime mode and channel-role helpers that can be tested without connecting to Discord.
- Add a controller that maps Discord input, commands, trace posts, feedback, and autonomous posts onto existing DB tables and runtime cycles.
- Add a minimal command dispatch layer for slash-command-like behavior.
- Add an optional `discord.py` bot runner that registers commands and delegates all business logic to the controller.
- Add CLI support for inspecting Discord config/status, checking live readiness, and running the optional bot.
- Add tests for observe-only, ingest-enabled, command-enabled, autonomous posting, and compatibility with existing core runtime.
- Add guide/reference docs for local setup and mode behavior.

## Non-Goals

- Do not build a general-purpose Discord assistant.
- Do not create a Discord-only database or source-of-truth state store.
- Do not implement unrestricted attachment ingestion or arbitrary file reads.
- Do not bypass normal wake budgets, safety constraints, or locked core profile behavior.
- Do not require live Discord credentials for automated tests.

## Requirements

- **Functional**: `observe_only`, `ingest_enabled`, `command_enabled`, and `autonomous_posting_enabled` are enforceable feature gates.
- **Functional**: channel roles define `ingestable` and `bot_output_allowed`; trace/policy/eval/admin roles are not ingestable by default.
- **Functional**: Discord user messages in allowed ingestable channels become `raw_events` with source metadata.
- **Functional**: command dispatch supports status, wake, concerns, concern detail, policy, trace, replay, feedback, inject, mute, and restricted mode change where configured.
- **Functional**: mutating commands and autonomous posts create actions/outcomes or equivalent trace rows.
- **Functional**: trace posts are compact summaries and never raw full file/secret dumps.
- **Non-Functional**: Discord disabled mode preserves existing CLI/core behavior.
- **Non-Functional**: automated tests use controller objects and do not require a real Discord connection.
- **Security**: Discord token is read from environment only and is never persisted.
- **Security**: self-ingestion prevention rejects bot-authored messages and non-ingestable channel roles by default.

## Tasks

- Config: extend `Settings` with `DiscordSettings`, channel definitions, mode parsing, admin checks, and safe defaults.
- Runtime: add mode helpers, channel safety helpers, controller, renderer, and command dispatch.
- Adapter: add optional `discord.py` bot runner with slash commands and message ingestion hooks.
- DB integration: use existing `RawEvent`, `Action`, `Outcome`, `WakeRequest`, `ResponseTrace`, `ReplayRun`, concerns, and attention policy rows.
- CLI: add `discord status`, `discord doctor`, `discord run`, and local dispatch/smoke commands where useful.
- Tests: cover each mode, self-ingestion, commands, autonomous rate limit/mute, and disabled compatibility.
- Docs: update README, `.env.example`, guide, reference, QA verification.

## QA Plan

- QA document: `_docs/qa/Core/discord-integration/test-plan.md`
- Risk level: High
- Test strategy:
  - Unit: mode ordering, channel role decision, metadata rendering, rate limiting, mute, command guards.
  - Integration: controller creates `raw_events`, actions/outcomes, wake requests, replay runs using temporary DB.
  - E2E: CLI smoke for Discord status, Discord doctor, and existing core commands without credentials.
  - Manual QA: live Discord bot startup and command sync remain deferred unless credentials are available.
  - Validator / static check: `uv run --python /home/penne/.local/bin/python3.12 pytest` and `./scripts/check-docs.sh`.

## Deployment / Rollout

- Default `AGENT_DISCORD_ENABLED=false` keeps the existing PoC behavior unchanged.
- First rollout should use `observe_only`, then `ingest_enabled`, then `command_enabled`, and only then `autonomous_posting_enabled`.
- Rollback is disabling `AGENT_DISCORD_ENABLED` or lowering `AGENT_DISCORD_MODE`; no schema-destructive migration is required.
- Live Discord startup requires a bot token in `DISCORD_BOT_TOKEN` and configured channel IDs.
