---
title: Discord Integration Adapter Usage
status: active
draft_status: n/a
created_at: 2026-06-02
updated_at: 2026-06-02
references:
  - "_docs/intent/Core/discord-integration/decision.md"
  - "_docs/plan/Core/discord-integration/plan.md"
  - "_docs/qa/Core/discord-integration/test-plan.md"
  - "_docs/qa/Core/discord-integration/verification.md"
  - "_docs/reference/Core/discord-integration/reference.md"
related_issues: []
related_prs: []
---

## Overview

Discord integration lets the PoC publish compact trace/status output, ingest explicitly allowed user messages, accept controlled commands, and prepare rate-limited autonomous posts. The SQLite DB and runtime cycles remain canonical.

## Prerequisites

- Python 3.12 and `uv`.
- A Discord application/bot token for live operation.
- Channel IDs for the roles you plan to use.
- Message Content intent enabled in the Discord Developer Portal when using `ingest_enabled` or higher. The code also enables `message_content` when `AGENT_DISCORD_MAX_MODE` can ingest.

## Setup / Usage

Start with disabled/local status:

```bash
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord status
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord doctor
```

Configure observe-only:

```bash
export AGENT_DISCORD_ENABLED=true
export AGENT_DISCORD_MODE=observe_only
export AGENT_DISCORD_MAX_MODE=observe_only
export AGENT_DISCORD_GUILD_ID="..."
export AGENT_DISCORD_CHANNEL_AGENT_ADMIN_ID="..."
export AGENT_DISCORD_CHANNEL_AGENT_TRACE_ID="..."
export DISCORD_BOT_TOKEN="..."
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord doctor --mode observe_only --live
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord run --dry-run
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord run
```

Move one layer at a time:

```bash
export AGENT_DISCORD_MODE=ingest_enabled
export AGENT_DISCORD_MAX_MODE=ingest_enabled
export AGENT_DISCORD_CHANNEL_AGENT_CHAT_ID="..."
export AGENT_DISCORD_CHANNEL_AGENT_INBOX_ID="..."
```

```bash
export AGENT_DISCORD_MODE=command_enabled
export AGENT_DISCORD_MAX_MODE=command_enabled
export AGENT_DISCORD_ADMIN_USER_IDS="1234567890"
```

```bash
export AGENT_DISCORD_MODE=autonomous_posting_enabled
export AGENT_DISCORD_MAX_MODE=autonomous_posting_enabled
export AGENT_DISCORD_AUTONOMOUS_OUTPUT_ROLES=agent_chat,agent_concerns,agent_eval
export AGENT_DISCORD_AUTONOMOUS_RATE_LIMIT_SECONDS=3600
```

Useful local smokes:

```bash
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord doctor --mode observe_only --live
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord run --dry-run
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord command status
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord command ping
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord post --role agent_trace --message "trace smoke"
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord cycle wake --reason scheduled
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord cycle eval --prompt-id 1
```

## Best Practices

- Keep `AGENT_DISCORD_ENABLED=false` unless actively testing Discord.
- Use private trace/policy/eval/admin channels.
- Keep `agent_trace`, `agent_policy`, `agent_eval`, and `agent_admin` non-ingestable unless there is a deliberate manual-injection reason.
- Treat `/inject` as explicit input. It is not the same as ordinary chat ingestion.
- Replies or reactions to recorded autonomous posts become outcomes when ingestion is enabled; the bot's original post remains non-ingestable.
- Use `/mute duration:1h` before enabling autonomous posting in a noisy server.
- Set `AGENT_DISCORD_MAX_MODE` to the highest mode you are willing to allow; `/mode` cannot exceed it.
- Run `discord doctor --mode <mode> --live` before `discord run`; fix `ERROR` rows before treating the setup as live-ready.

## Verified Behavior

Automated verification covers controller-level mode gates, raw event metadata, self-ingestion prevention, command traces, autonomous rate limits, mute behavior, attachment rejection, live-readiness diagnostics, and existing core regressions. Live Discord command sync and real guild posting require manual QA with credentials.

## Troubleshooting

- Slash commands do not appear: confirm the bot started, guild ID is correct, and command sync completed in logs.
- `discord doctor` reports `token_missing`: export the token in the configured env var; the command only reports presence and never prints the value.
- User messages do not ingest: confirm mode is `ingest_enabled` or higher, channel ID matches an ingestable role, and Message Content intent is enabled in the Developer Portal and code.
- `/mode` fails: set `AGENT_DISCORD_ALLOW_MODE_COMMAND=true`, configure `AGENT_DISCORD_ADMIN_USER_IDS`, and ensure requested mode does not exceed `AGENT_DISCORD_MAX_MODE`.
- Autonomous post is denied: check mode, mute status, rate limit, channel allowlist, and `bot_output_allowed`.

## References

- `_docs/reference/Core/discord-integration/reference.md`
- `_docs/qa/Core/discord-integration/test-plan.md`
- `_docs/qa/Core/discord-integration/verification.md`
