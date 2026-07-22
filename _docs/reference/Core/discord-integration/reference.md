---
title: Discord Integration Adapter Reference
status: active
draft_status: n/a
created_at: 2026-06-02
updated_at: 2026-06-02
references:
  - "_docs/intent/Core/discord-integration/decision.md"
  - "_docs/plan/Core/discord-integration/plan.md"
  - "_docs/qa/Core/discord-integration/test-plan.md"
  - "_docs/qa/Core/discord-integration/verification.md"
related_issues: []
related_prs: []
---

## Overview

The Discord adapter is split into config, controller, command dispatch, renderers, and an optional live bot runner. The controller is the tested boundary; `discord.py` only translates Discord events/interactions into controller DTOs.

## API

### `app.adapters.discord_config`

- **Summary**: Loads env-backed Discord settings.
- **Key classes**:
  - `DiscordSettings`: enabled state, mode, max mode, guild, channel roles, admin users, attachment limits, autonomous allowlist/rate limit.
  - `DiscordChannelConfig`: role, ID, `ingestable`, and `bot_output_allowed`.
  - `DiscordReadinessReport`: non-network readiness checks for token presence, mode clamps, channels, admin path, and autonomous output.
- **Important functions**:
  - `diagnose_discord_settings(settings, target_mode=..., live_run=...)`: returns `ok`, `warning`, and `error` checks without printing token values.
- **Important env vars**:
  - `AGENT_DISCORD_ENABLED`
  - `AGENT_DISCORD_MODE`
  - `AGENT_DISCORD_MAX_MODE`
  - `AGENT_DISCORD_GUILD_ID`
  - `AGENT_DISCORD_CHANNEL_<ROLE>_ID`
  - `AGENT_DISCORD_ADMIN_USER_IDS`
  - `AGENT_DISCORD_ALLOW_MODE_COMMAND`
  - `DISCORD_BOT_TOKEN`

### `app.runtime.modes.DiscordRuntimeMode`

- **Summary**: Ordered runtime mode enum.
- **Modes**: `observe_only`, `ingest_enabled`, `command_enabled`, `autonomous_posting_enabled`.
- **Capability helpers**: `can_ingest`, `can_run_commands`, `can_post_autonomously`.

### `app.runtime.discord_controller.DiscordController`

- **Summary**: Canonical adapter logic and DB integration.
- **Important methods**:
  - `effective_mode(session)`: reads config and optional DB-backed mode-change action.
  - `ingest_message(session, DiscordMessageInput)`: applies mode/channel/author/attachment gates and persists `raw_events`.
  - `dispatch_command(session, DiscordCommandContext)`: handles slash-command-like requests.
  - `prepare_trace_post(session, role, content)`: prepares compact bot trace output.
  - `prepare_autonomous_post(session, role, content, reason=...)`: applies autonomous gates and creates post action/outcome.
  - `record_post_delivery(session, action_id, discord_message_id=...)`: records the Discord message ID after the live adapter sends a prepared post.
  - `render_status(session)`: renders `/status` output.
  - `render_trace_summary(session, run_id="latest")`: renders compact trace output.
- **DB writes**:
  - Discord user messages: `raw_events`.
  - Optional review hookup: `observations`, concerns, memories, policy updates through existing cognition modules.
  - Mutating commands: `actions` and `outcomes`.
  - `/wake`: existing `wake_cycle` plus Discord command action/outcome.
  - `/replay`: existing replay eval plus Discord command action/outcome.
  - Autonomous posts: `discord_autonomous_post` action/outcome.
  - User replies to recorded autonomous posts: outcome on the original autonomous post action when ingestion is enabled.
  - User reactions to recorded autonomous posts: outcome on the original autonomous post action when ingestion is enabled.

### `app.adapters.discord_bot.run_discord_bot`

- **Summary**: Optional live `discord.py` runner.
- **Behavior**:
  - Reads token from `settings.discord.token_env_var`.
  - Enables `message_content` intent when `AGENT_DISCORD_MAX_MODE` can ingest.
  - Syncs slash commands to `AGENT_DISCORD_GUILD_ID` when configured.
  - Handles raw reaction-add events for recorded autonomous posts.
  - Registers `/ping`, `/status`, `/wake`, `/concerns`, `/concern`, `/policy`, `/trace`, `/replay`, `/feedback`, `/inject`, `/mute`, `/mode`.
  - `python -m app.main discord run --dry-run` builds the same command tree and reports intents without connecting to Discord.

### CLI commands

- **Summary**: Local smoke and trace-preparation commands for Discord integration.
- **Commands**:
  - `python -m app.main discord status`: show adapter status and safe public config.
  - `python -m app.main discord doctor [--mode <mode>] [--live]`: check config readiness without connecting to Discord.
  - `python -m app.main discord run`: start the live Discord bot.
  - `python -m app.main discord run --dry-run`: build command tree/intents without connecting.
  - `python -m app.main discord command <name>`: local command-dispatch smoke.
  - `python -m app.main discord post --role <role> --message <text>`: prepare a trace or autonomous post.
  - `python -m app.main discord cycle <wake|review|reflect|eval>`: run a canonical core cycle and prepare compact Discord trace posts for the configured role channels.

## Channel Roles

| Role | Default ingestable | Default bot output | Purpose |
| --- | --- | --- | --- |
| `agent_chat` | yes | yes | User-facing chat/input. |
| `agent_inbox` | yes | no | Loose input, notes, links, scraps. |
| `agent_trace` | no | yes | Private trace output. |
| `agent_concerns` | no | yes | Concern lifecycle output. |
| `agent_policy` | no | yes | Attention policy updates. |
| `agent_eval` | no | yes | Replay/eval summaries. |
| `agent_admin` | no | yes | Admin commands/control. |

## Commands

- `/ping`: read-only smoke.
- `/status`: mode, active concerns, attention policy summary, recent action, next wake, mute/autonomous state.
- `/wake reason:<text>`: creates Discord command action/outcome and runs normal `wake_cycle`.
- `/concerns`: concise concern list.
- `/concern id:<id>`: concern detail and recent concern events.
- `/policy`: current attention policy and recent policy events.
- `/trace run_id:<id|latest>`: response trace detail for numeric ID or latest count/action summary.
- `/replay prompt_id:<id optional>`: runs replay eval and logs action/outcome.
- `/feedback target_id:<id> type:<...> note:<text>`: records feedback as outcome evidence.
- `/inject note:<text>`: explicit raw event from Discord command, always passed through the observation/digest pipeline.
- `/mute duration:<duration>`: mutes autonomous posting. `0` / `off` clears mute.
- `/mode mode:<mode>`: restricted to configured admin users and cannot exceed `AGENT_DISCORD_MAX_MODE`.

## Notes

- The adapter does not create a separate Discord state store.
- `/trace` uses existing response trace/action summaries because this PoC does not yet have a first-class cycle-run table.
- Attachment ingestion is disabled by default and accepts only configured text content types within size limits.
- Live Discord operation follows `discord.py` application command sync and gateway-intent behavior.

## Verification

- QA plan: `_docs/qa/Core/discord-integration/test-plan.md`
- Verification: `_docs/qa/Core/discord-integration/verification.md`
