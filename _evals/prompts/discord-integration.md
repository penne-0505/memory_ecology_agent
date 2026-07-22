# Historical prompt: Discord integration

This file preserves the one-off implementation prompt as non-operational historical context. Current project guidance remains `AGENTS.md`, `TODO.md`, and `_docs/**`.

Date captured: 2026-06-02

## Summary

Implement Discord as an end-to-end adapter for the Memory Ecology Agent PoC without making Discord the source of truth. The core runtime, database, scheduler, and CLI remain canonical. Discord should act as an observation window, input window, and control surface.

Required modes:

- `observe_only`: Discord may receive trace/status output. It must not ingest messages or run mutating commands. Minimal read-only `/ping` or `/status` is allowed.
- `ingest_enabled`: explicitly ingestable Discord channels may create `raw_events` with Discord source metadata. Bot messages and trace/admin channels are ignored by default.
- `command_enabled`: slash-command-like dispatch exposes status, wake, concerns, concern detail, policy, trace, replay, feedback, inject, mute, and optionally restricted mode change. Mutating commands create traceable action/outcome records.
- `autonomous_posting_enabled`: controlled asynchronous posts, digests, concern changes, replay/eval summaries, and chosen questions are allowed only with rate limits, mute support, and channel allowlists. All autonomous posts are logged as actions.

Required channel roles:

- `agent_chat`
- `agent_inbox`
- `agent_trace`
- `agent_concerns`
- `agent_policy`
- `agent_eval`
- `agent_admin`

Mandatory safety:

- Discord bot token comes from environment or existing secret mechanism.
- Never log/post secrets or raw unrestricted file contents.
- Local file and attachment ingestion must be bounded by configured safe paths, type limits, and size limits.
- Prevent self-ingestion: bot-authored messages and trace/policy/eval/admin channels are not normal input by default.
- Core profile is not rewritten automatically through Discord.
- Existing DB structures remain canonical; no Discord-only source-of-truth store.

Acceptance requires mode-specific verification for observe-only, ingest-enabled, command-enabled, and autonomous-posting-enabled behavior. Do not claim full success for a partially implemented mode.
