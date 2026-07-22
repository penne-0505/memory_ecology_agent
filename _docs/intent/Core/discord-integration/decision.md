---
title: Discord Integration Adapter Decision
status: active
draft_status: n/a
created_at: 2026-06-02
updated_at: 2026-06-02
references:
  - "_docs/plan/Core/discord-integration/plan.md"
  - "_docs/qa/Core/discord-integration/test-plan.md"
  - "_evals/prompts/discord-integration.md"
related_issues: []
related_prs: []
---

## Context

The PoC already traces probe, raw event, observation, concern, memory, action, outcome, attention policy, response trace, and replay state in SQLite. Discord integration must expose that ecology without letting Discord noise become canonical state or ordinary input by accident. The main risk is not implementation size; it is losing experimental validity through self-ingestion, unsafe posting, and untraceable intervention.

## Decision

- Implement Discord as an adapter and controller around existing DB/runtime functions.
- Represent runtime mode as an ordered feature gate: `observe_only < ingest_enabled < command_enabled < autonomous_posting_enabled`.
- Represent channel roles in config with explicit `ingestable` and `bot_output_allowed` flags.
- Persist Discord input as ordinary `raw_events` only after mode, channel, author, and attachment safety checks pass.
- Persist mutating commands and autonomous posts as `actions` plus `outcomes` where applicable.
- Keep live `discord.py` code thin and optional; tests exercise the controller without network credentials.
- Expose a local `discord doctor` readiness check so live token/channel/admin gaps are reported before gateway startup.
- Read Discord token from `DISCORD_BOT_TOKEN` only. Do not store or print it.
- Keep core profile locked; feedback can become outcomes or normal review input, not direct profile rewrites.

## Alternatives

- **Put Discord logic directly in slash command handlers**: rejected because it duplicates business logic and makes non-network tests weak.
- **Create Discord-specific state tables**: rejected because it risks making Discord a parallel source of truth.
- **Support only observe-only first**: rejected for this implementation pass because the requested adapter needs all layers wired, but each layer must remain feature-gated.
- **Avoid `discord.py` entirely**: rejected because local controller tests are enough for CI, but a practical bot runner still needs a maintained Discord client library.

## Rationale

The controller boundary keeps mode decisions and DB writes inspectable. `discord.py` remains an I/O shell: message events and interactions are converted into small DTOs, passed to controller methods, then rendered back into compact text. This preserves the existing PoC's trace-first design and lets automated tests prove safety behavior without a live Discord guild.

## Consequences / Impact

- New config surface is larger, but safe defaults keep Discord disabled.
- `discord.py` becomes a runtime dependency for the live bot path.
- Some live behavior, such as command registration and real channel permissions, cannot be fully verified without credentials and is recorded as manual QA/deferred if not run.
- Existing CLI/core runtime must remain green with Discord disabled.

## Quality Implications

- Mode gates must be tested as behavior, not only as config strings.
- Self-ingestion prevention must be a first-class invariant.
- Mutating operations must create traceable rows.
- Autonomous posting must be rate-limited and mute-aware.
- Output renderers must summarize and avoid raw full payloads.
- Live-readiness diagnostics must show token presence only as a boolean / env-var fact, never the token value.

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

## Rollback / Follow-ups

- Rollback by setting `AGENT_DISCORD_ENABLED=false` or lowering `AGENT_DISCORD_MODE=observe_only`.
- Live guild smoke, command sync, and reaction outcome handling require real Discord credentials or additional gateway handlers and should remain explicitly marked if not verified. Reply-to-autonomous-post outcomes are covered through recorded Discord message IDs.
