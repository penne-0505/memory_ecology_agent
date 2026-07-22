---
title: "QA Verification: Discord Integration Adapter"
status: active
draft_status: n/a
qa_status: verified
risk: High
created_at: 2026-06-02
updated_at: 2026-06-02
references:
  - "_docs/intent/Core/discord-integration/decision.md"
  - "_docs/plan/Core/discord-integration/plan.md"
  - "_docs/qa/Core/discord-integration/test-plan.md"
  - "_docs/guide/Core/discord-integration/usage.md"
  - "_docs/reference/Core/discord-integration/reference.md"
related_issues: []
related_prs: []
---

# QA Verification: `Discord Integration Adapter`

## Summary

Discord integration was implemented as a config-gated adapter around the existing PoC runtime and SQLite DB. Automated verification covers controller-level observe-only, ingest-enabled, command-enabled, autonomous-posting-enabled behavior, and non-network live-readiness diagnostics. Live Discord credentials were later provided; live bot startup, guild command sync, channel provisioning, and a real `agent_trace` channel post were verified.

## Verification Verdict

Verdict: PASS

Rationale: core implementation, config, DB integration, command dispatch, autonomous gates, readiness diagnostics, docs, regression tests, live startup, live command sync, real channel posting, human-triggered `/status` delivery, live `ingest_enabled` user-message ingestion, live non-ingestable-channel ignore behavior, and live autonomous allow/deny paths are verified.

Completion scope: `Core-Feat-7` was first accepted as a limited `PARTIAL` completion for the Discord adapter/controller, CLI, dry-run behavior, and observe-only live smoke. Follow-up `Core-Test-9` then verified the remaining live `ingest_enabled` and `autonomous_posting_enabled` paths.

## Commands Run

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord status
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord doctor
AGENT_DISCORD_ENABLED=true AGENT_DISCORD_MODE=ingest_enabled AGENT_DISCORD_MAX_MODE=ingest_enabled uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord doctor --mode ingest_enabled --live
AGENT_DISCORD_ENABLED=true AGENT_DISCORD_MODE=autonomous_posting_enabled ... DISCORD_BOT_TOKEN=dummy-token-for-doctor-smoke uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord doctor --mode autonomous_posting_enabled --live
set -a; source .env; set +a; uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord doctor --mode observe_only --live
set -a; source .env; set +a; timeout 20s uv run --python /home/penne/.local/bin/python3.12 python -u -m app.main discord run
setsid -f bash -lc 'cd /home/penne/dev/active/memory_ecology_agent && set -a; source .env; set +a; exec uv run --python /home/penne/.local/bin/python3.12 python -u -m app.main discord run >> agent_workspace/scratch/discord-bot.log 2>&1'
Discord API smoke: GET guild application commands and POST one trace-channel smoke message
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord command status
AGENT_DISCORD_ENABLED=true AGENT_DISCORD_MODE=command_enabled ... python -m app.main --project-root "$tmpdir" discord command inject --user-id 42 --channel-id 300 --option 'note=CLI injected Discord concern policy risk.'
AGENT_DISCORD_ENABLED=true AGENT_DISCORD_MODE=observe_only ... python -m app.main --project-root "$tmpdir" discord post --role agent_trace --message 'trace smoke'
AGENT_DISCORD_ENABLED=true AGENT_DISCORD_MODE=command_enabled AGENT_DISCORD_MAX_MODE=command_enabled python -m app.main discord run --dry-run
AGENT_DISCORD_ENABLED=true AGENT_DISCORD_MODE=observe_only ... python -m app.main --project-root "$tmpdir" discord cycle wake --reason scheduled
AGENT_DISCORD_ENABLED=true AGENT_DISCORD_MODE=observe_only ... python -m app.main --project-root "$tmpdir" discord cycle eval --prompt-id 1 --reason manual_eval
uv run --python /home/penne/.local/bin/python3.12 python - <<'PY'
from app.adapters.discord_bot import run_discord_bot
from app.adapters.discord_config import load_discord_settings
print(run_discord_bot.__name__)
print(load_discord_settings({'AGENT_DISCORD_MODE': 'observe_only'}).mode.value)
PY
git diff --check
./scripts/check-docs.sh
```

Result:

```text
pytest: 44 passed, 1 warning from discord.py audioop import on Python 3.12
discord status: PASS, shows disabled observe_only config without token exposure
discord doctor default: PASS, reports no errors for disabled local config and warns about live-only gaps
discord doctor live blockers: PASS, exits 1 and reports missing token/trace/ingest config without connecting
discord doctor ready dummy env: PASS, exits 0 and reports token presence without printing token value
discord doctor live observe-only: PASS, exits 0 with real token/guild/trace-channel env loaded from `.env`
discord live startup: PASS, Gateway connected and `discord bot ready` logged with `commands=12`
discord guild command API check: PASS, guild has 12 commands: concern, concerns, feedback, inject, mode, mute, ping, policy, replay, status, trace, wake
discord real trace-channel post: PASS, posted smoke message to configured `agent_trace` channel
discord human `/status`: PASS, Discord client returned observe-only adapter status to the user
discord command status: PASS, read-only local dispatch works while disabled
discord command inject CLI smoke: PASS, created raw_event in isolated project root
discord post trace CLI smoke: PASS, prepared trace smoke in isolated project root
discord run --dry-run: PASS, built command tree and reported message_content intent without starting gateway
discord cycle wake CLI smoke: PASS, prepared trace/concern/policy posts for configured channels
discord cycle eval CLI smoke: PASS, prepared eval trace post for configured eval channel
discord_bot import smoke: PASS, imported live runner without starting gateway
git diff --check: PASS
check-docs: PASS
```

## Automated Test Results

| Command / Test | Result | Notes |
| --- | --- | --- |
| `uv run --python /home/penne/.local/bin/python3.12 pytest` | PASS | `44 passed`, 1 `discord.py` deprecation warning from `audioop`; includes dry-run command tree, readiness diagnostics, observe-only cycle trace preparation, controller, command dispatch, autonomous reply/reaction outcomes, and existing core regression tests. |
| `python -m app.main discord status` | PASS | Shows mode, enabled state, channel config, token presence boolean, and no token value. |
| `python -m app.main discord doctor` | PASS | Reports disabled local config as non-error and identifies live-only token/guild/trace gaps as warnings. |
| `python -m app.main discord doctor --mode ingest_enabled --live` with missing live config | PASS | Expected exit 1; reports missing token, trace channel, and ingest channel without a network connection. |
| `python -m app.main discord doctor --mode autonomous_posting_enabled --live` with dummy token/channel env | PASS | Expected exit 0; reports token presence without printing the dummy token value. |
| `python -m app.main discord doctor --mode observe_only --live` with real `.env` | PASS | Real token presence, guild ID, and `agent_trace` channel are configured; no token value printed. |
| live `python -m app.main discord run` | PASS | Gateway connected and ready log reported `commands=12`; the foreground smoke was stopped with `timeout` after readiness. |
| detached live bot process | PASS | Bot is running from `.env`; PID recorded in `agent_workspace/scratch/discord-bot.pid`, logs in `agent_workspace/scratch/discord-bot.log`. |
| Discord API guild command check | PASS | Guild application command list contains all 12 expected slash commands. |
| Discord API trace-channel post smoke | PASS | Bot posted one smoke message to the configured `agent_trace` channel; evidence stored in `agent_workspace/scratch/discord-live-smoke.json`. |
| human `/status` invocation in Discord UI | PASS | User reported the Discord client response: mode `observe_only`, enabled `True`, autonomous posting disabled, mute off, no current action/wake/concerns. |
| `python -m app.main discord command status` | PASS | Minimal read-only dispatch works without live Discord. |
| `python -m app.main --project-root "$tmpdir" discord command inject ...` | PASS | Mutating command dispatch created `raw_event_1` in isolated project root. |
| `python -m app.main --project-root "$tmpdir" discord post --role agent_trace ...` | PASS | Observe-only trace post preparation succeeded for configured private trace channel. |
| `python -m app.main discord run --dry-run` | PASS | Built command tree with `concern, concerns, feedback, inject, mode, mute, ping, policy, replay, status, trace, wake`; no gateway connection attempted. |
| `python -m app.main --project-root "$tmpdir" discord cycle wake ...` | PASS | Ran canonical wake cycle and prepared trace, concern, and policy posts for configured roles. |
| `python -m app.main --project-root "$tmpdir" discord cycle eval ...` | PASS | Ran replay eval and prepared eval trace post for configured role. |
| import smoke for `app.adapters.discord_bot` | PASS | Live runner module imports; gateway startup is covered by the live run above. |
| `git diff --check` | PASS | No whitespace errors. |
| `./scripts/check-docs.sh` | PASS | Front-matter, TODO, links, QA validators, and validator fixtures passed. |

## Manual QA Results

| Checklist Item | Result | Notes |
| --- | --- | --- |
| Start live bot in `observe_only` | PASS | Gateway connected; `discord bot ready` logged. |
| Confirm command registration/sync in guild | PASS | Ready log and guild command API returned 12 expected commands. |
| Confirm `/status` in Discord | PASS | User reported live Discord UI response in `observe_only`. |
| Confirm `agent_chat` user message ingestion in live Discord | PASS | Follow-up `Core-Test-9` live run verified user-authored `agent_inbox` ingestion as `raw_event_4`; current operational mode was rolled back to `observe_only`. |
| Confirm trace/admin channel messages are ignored live | PASS | Follow-up `Core-Test-9` live run verified user-authored `agent_trace` ignored with raw event count unchanged. |
| Confirm autonomous post appears in allowlisted channel | PASS | Follow-up `Core-Test-9` live run verified allowlisted autonomous send, delivery message ID recording, rate-limit deny, and allowlist deny paths. |

## Mode Verification

| Mode | Automated Result | Live Result | Evidence |
| --- | --- | --- | --- |
| `observe_only` | PASS | PASS | `test_ac001_inv001_observe_only_does_not_ingest_messages`; CLI status, trace post, cycle wake/eval smokes, live startup, command sync, and trace-channel post. |
| `ingest_enabled` | PASS | PASS | `test_ac004_inv003_ingest_enabled_creates_raw_event_with_metadata`; live user-message ingestion; bot/trace rejection; autonomous-reply outcome test. |
| `command_enabled` | PASS | PASS | wake/feedback/inject/replay/mute/mode controller tests plus isolated CLI inject smoke; live `/status` verified. |
| `autonomous_posting_enabled` | PASS | PASS | autonomous allowlist/rate limit/mute tests plus live allowlisted send, delivery recording, and deny paths. |

## Acceptance Criteria Coverage

| ID | Result | Evidence |
| --- | --- | --- |
| AC-001 | PASS | `DiscordRuntimeMode`, `DiscordSettings`, `DiscordController.render_status`, CLI `discord status`, `discord doctor`, `discord cycle`, tests. |
| AC-002 | PASS | `DiscordChannelConfig`, env channel role loader, `_channels()` tests. |
| AC-003 | PASS | bot author and trace channel rejection tests; trace posts are actions/outcomes and do not create `discord_bot_trace` raw events. |
| AC-004 | PASS | Discord user message creates `raw_events` with metadata and optional observation pipeline in tests. |
| AC-005 | PASS | Command dispatch covers `/wake`, `/feedback`, `/inject`, `/replay`, `/mute`, `/mode`; read-only renderers cover status/concerns/concern/policy/trace; CLI inject smoke passed. |
| AC-006 | PASS | Autonomous post gate test covers mode, allowlist, rate limit, mute, action/outcome logging, delivery message ID recording, and user reply/reaction outcome mapping. |
| AC-007 | PASS | token env-only config, public status and `discord doctor` do not print token values, unsafe attachment/sensitive post tests. |
| AC-008 | PASS | Full pytest suite passes with Discord disabled by default. |

## Invariant Coverage

| ID | Result | Evidence |
| --- | --- | --- |
| INV-001 | PASS | observe-only ingest rejection test. |
| INV-002 | PASS | bot author and trace channel rejection test. |
| INV-003 | PASS | raw event payload assertions for Discord metadata, including parent/reply metadata path. |
| INV-004 | PASS | mutating command action/outcome assertions and correction feedback review-path test. |
| INV-005 | PASS | autonomous mode/allowlist/rate/mute tests plus delivery/reply/reaction outcome mapping. |
| INV-006 | PASS | core profile content unchanged after Discord mutating commands. |
| INV-007 | PASS | token env-only design and sensitive attachment/post tests. |
| INV-008 | PASS | existing non-Discord tests pass in full suite. |
| INV-009 | PASS | `diagnose_discord_settings` and `discord doctor` tests cover live blockers, ready dummy config, non-zero exit, and token-value omission. |

## Deferred / Not Covered

| ID | Reason | Follow-up |
| --- | --- | --- |
| Rich attachment ingestion | Attachment ingestion is intentionally conservative and disabled by default. | Separate safety design if richer file handling is needed. |
| First-class cycle-run trace table | `/trace` summarizes existing probes/actions/response traces. | Consider only if trace history needs a dedicated run entity. |

## Follow-up Execution Notes

### `Core-Test-9` follow-up live run: 2026-06-02 JST

Additional live checks were started after `Core-Feat-7` was split into `Core-Test-9`.

| Check | Result | Evidence |
| --- | --- | --- |
| `discord doctor --mode ingest_enabled --live` with `.env` as-is | EXPECTED BLOCKER | Failed only because `.env` keeps `AGENT_DISCORD_MAX_MODE=observe_only`; token value was not printed. |
| `discord doctor --mode ingest_enabled --live` with temporary `AGENT_DISCORD_MODE=ingest_enabled AGENT_DISCORD_MAX_MODE=ingest_enabled` | PASS | `errors=0`, with Message Content warning accepted because the user confirmed the Developer Portal intent is enabled. |
| `discord doctor --mode autonomous_posting_enabled --live` with temporary autonomous env | PASS | `errors=0`, autonomous output roles configured, token value not printed. |
| Live `ingest_enabled` bot startup | PASS | Gateway connected; ready log showed `mode=ingest_enabled max_mode=ingest_enabled commands=12`. |
| User-authored `agent_inbox` message ingestion | PASS | User posted the requested smoke message; bot logged `discord message ingested: raw_event_id=4`; DB shows `raw_events=4`, `raw_event_4.source_type=discord_user_message`, `discord_channel_role=agent_inbox`, `author_type=user`. |
| Bot-authored trace-channel post ignore | PASS | Bot sent a smoke message to `agent_trace`; immediate and delayed DB checks kept `raw_events=4`; no ingest log was emitted. |
| Live autonomous allowlisted send | PASS | Prepared `discord_autonomous_post` action `act_3`, sent the message to `agent_chat` through the Discord API, and recorded Discord delivery message ID on the action; outcomes increased to 4. |
| Live autonomous deny path | PASS | A second `agent_chat` autonomous attempt with rate limit enabled returned `rate_limited_3421s`; an `agent_policy` attempt returned `channel_not_in_autonomous_allowlist`. |
| Rollback / mode lowering | PASS | Temporary `ingest_enabled` bot process was stopped; pre-existing observe-only bot process remained running. `.env` still has `AGENT_DISCORD_MODE=observe_only` and `AGENT_DISCORD_MAX_MODE=observe_only`. |
| User-authored trace/admin/policy/eval ignore | PASS | User posted in `agent_trace`; DB check showed `raw_events_after_trace_user_post=4`, with latest raw event still `raw_event_4 source_type=discord_user_message event_type=user_message` from the earlier `agent_inbox` ingest. |

`Core-Test-9` is complete. Temporary `ingest_enabled` bot process was stopped after the final ignore-path check; the pre-existing observe-only bot process remained running.

## Residual Risks

None

## Follow-up TODOs

- None required for this PASS.
