# Memory Ecology Agent PoC

Memory Ecology Agent PoC は、長期記憶つきチャットそのものではなく、入力環境から何を探索し、何を観測し、何を concern として保持し、どの action / outcome に変え、その結果 attention policy と応答がどう変わるかを trace するためのローカル CLI 実験です。

初期実装は賢さより traceability を優先しています。外部 API キーなしで `MockLLMClient` と `state_sensitive_mock` が動き、SQLite に probe、raw event、observation、digest decision、concern、memory、action、outcome、attention policy event、response trace、replay run を保存します。

## セットアップ

Python 3.12 と `uv` を使います。

```bash
uv run --python /home/penne/.local/bin/python3.12 python -m app.main init
uv run --python /home/penne/.local/bin/python3.12 python -m app.main seed
```

標準では次の場所を使います。

- DB: `data/agent.db`
- input ecology: `world/`
- agent writable workspace: `agent_workspace/`

テストや隔離実行では `--project-root` を指定できます。

```bash
tmpdir=$(mktemp -d)
uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root "$tmpdir" init
uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root "$tmpdir" seed
```

## 基本コマンド

```bash
uv run --python /home/penne/.local/bin/python3.12 python -m app.main wake --reason cron
uv run --python /home/penne/.local/bin/python3.12 python -m app.main inspect concerns
uv run --python /home/penne/.local/bin/python3.12 python -m app.main inspect digest-decisions
uv run --python /home/penne/.local/bin/python3.12 python -m app.main inspect attention-policy
uv run --python /home/penne/.local/bin/python3.12 python -m app.main inspect outcomes
uv run --python /home/penne/.local/bin/python3.12 python -m app.main chat "Should we implement now?"
uv run --python /home/penne/.local/bin/python3.12 python -m app.main eval run
uv run --python /home/penne/.local/bin/python3.12 python -m app.main eval compare --prompt-id 1
uv run --python /home/penne/.local/bin/python3.12 python -m app.main inspect traces
```

`wake` は `world/` を読み、probe から attention policy event までの縦切りを保存します。`chat` は現在の concern / memory / attention policy を context に入れて応答し、`response_traces` に選択状態を残します。`eval run` は seed 済み eval prompts への応答を `replay_runs` に保存します。

## Discord Adapter

Discord 統合は既定で無効です。Discord は source of truth ではなく、既存 CLI / DB / runtime を観測・入力・制御する adapter として動きます。

```bash
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord status
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord doctor
```

有効化時は `.env.example` の `AGENT_DISCORD_*` と `DISCORD_BOT_TOKEN` を shell で設定します。mode は段階的に上げます。

- `observe_only`: trace/status output と read-only `/status` / `/ping`。
- `ingest_enabled`: 明示的に ingestable な `agent_chat` / `agent_inbox` だけを `raw_events` 化。
- `command_enabled`: `/wake`, `/feedback`, `/inject`, `/mute`, `/replay` などの mutating command を action/outcome として trace。
- `autonomous_posting_enabled`: allowlist、mute、rate limit を満たす場合だけ user-visible post を準備。

live bot を起動する場合:

```bash
export AGENT_DISCORD_ENABLED=true
export AGENT_DISCORD_MODE=observe_only
export AGENT_DISCORD_MAX_MODE=observe_only
export AGENT_DISCORD_GUILD_ID="..."
export AGENT_DISCORD_CHANNEL_AGENT_ADMIN_ID="..."
export AGENT_DISCORD_CHANNEL_AGENT_TRACE_ID="..."
export DISCORD_BOT_TOKEN="..."
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord doctor --mode observe_only --live
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord run
```

ゲートウェイ接続なしで command tree と intents を確認する場合:

```bash
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord doctor --mode observe_only --live
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord run --dry-run
```

core cycle の trace output を Discord channel role 向けに準備する場合:

```bash
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord cycle wake --reason scheduled
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord cycle eval --prompt-id 1
```

詳細は `_docs/guide/Core/discord-integration/usage.md` と `_docs/reference/Core/discord-integration/reference.md` を参照してください。live Discord credentials がない環境では controller / CLI までを自動検証し、実 guild の command sync は手動 QA として扱います。

## Trace の読み方

- `inspect probes`: 何を、なぜ見に行ったか。
- `inspect digest-decisions`: 何が concern / memory / discard / action candidate になったか。discard reason と score snapshot も表示します。
- `inspect digest-proposals`: `AGENT_DIGEST_DECIDER=llm_shadow` で生成された LLM proposal、fallback、final decision link を表示します。
- `inspect concerns`: どの observation が未解決 concern になったか。
- `inspect attention-policy`: どの evidence で source preference が変わったか。
- `inspect outcomes`: action outcome が attention policy にどう効き得るか。
- `inspect traces`: chat response がどの memory / concern / policy に影響されたか。

DB を直接見る必要はありませんが、詳細確認には SQLite の各 table を参照できます。

## 安全境界

- local file adapter は `world/` 以下のみ read-only で読みます。
- `agent_workspace/` と SQLite DB 以外への書き込みは設計上行いません。
- path traversal、symlink traversal、binary file、`.env` / token / credential / secret らしきファイル名は raw event 化しません。
- Web search は stub です。実ネットワーク検索は初期 PoC では行いません。
- LLM provider の API key は環境変数からのみ読みます。DB、trace、docs、provider error message には保存しません。
- core profile は seed 後に自動更新しません。変更候補は `core_change_proposals` に留めます。
- Discord bot token は `DISCORD_BOT_TOKEN` または `AGENT_DISCORD_TOKEN_ENV_VAR` が指す環境変数からのみ読みます。DB / docs / status 出力には token 値を保存しません。

## LLM Provider

既定は `AGENT_LLM_PROVIDER=mock` です。外部 API key なしで `chat` / `eval run` / pytest が通ります。

observation extraction も既定は deterministic です。LLM を使う場合でも raw input
から structured observation proposal を作る段階だけに限定され、digest decisions、
concern lifecycle、memory creation、attention policy updates、actions/outcomes は
既存 deterministic pipeline が処理します。

digest decision も既定は deterministic です。`AGENT_DIGEST_DECIDER=llm_shadow`
を指定した場合だけ、observation ごとに LLM digest proposal を作り
`digest_decision_proposals` に保存します。shadow mode の final decision は
deterministic のままで、proposal は concern / memory / action / attention policy /
core profile を直接 mutate しません。`llm_assisted` は設定値として認識しますが、
この段階では conservative に deterministic final decision を維持します。

```bash
AGENT_OBSERVATION_EXTRACTOR=deterministic \
uv run --python /home/penne/.local/bin/python3.12 python -m app.main wake --reason cron
```

LLM observation extraction は明示 opt-in です。provider failure、credential 欠落、
invalid JSON、schema validation error では既定で deterministic fallback になり、
raw provider response は保存しません。検証目的で crash させる場合だけ
`AGENT_OBSERVATION_EXTRACTOR_FALLBACK=error` を指定します。

```bash
export AGENT_OBSERVATION_EXTRACTOR=llm
export AGENT_OBSERVATION_EXTRACTOR_FALLBACK=deterministic
export AGENT_LLM_PROVIDER=openrouter
export AGENT_LLM_MODEL=deepseek/deepseek-v4-pro
export OPENROUTER_API_KEY="..."
tmpdir=$(mktemp -d)
uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root "$tmpdir" init
uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root "$tmpdir" seed
uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root "$tmpdir" wake --reason manual-llm-observation-test
uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root "$tmpdir" inspect observations
uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root "$tmpdir" inspect digest-decisions
```

LLM digest proposal の manual smoke は observation extraction と同様に明示 opt-in です。
provider failure、invalid JSON、schema validation error、unsafe output は rejected proposal
として trace され、raw provider response は保存されず、wake pipeline は deterministic final
decision で継続します。

```bash
export AGENT_DIGEST_DECIDER=llm_shadow
export AGENT_LLM_PROVIDER=openrouter
export AGENT_LLM_MODEL=deepseek/deepseek-v4-pro
export OPENROUTER_API_KEY="..."
tmpdir=$(mktemp -d)
uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root "$tmpdir" init
uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root "$tmpdir" seed
uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root "$tmpdir" wake --reason manual-llm-digest-shadow-test
uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root "$tmpdir" inspect digest-decisions
uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root "$tmpdir" inspect digest-proposals
```

現在の extractor 設定は key 値を表示せずに確認できます。

```bash
uv run --python /home/penne/.local/bin/python3.12 python -m app.main inspect observation-extractor
```

replay の response text drift を外部 provider なしで検証する場合は、状態依存の fake provider を使えます。

```bash
AGENT_LLM_PROVIDER=state_sensitive_mock \
uv run --python /home/penne/.local/bin/python3.12 python -m app.main eval run
```

実 provider を使う場合は `.env.example` を参考に、環境変数を shell で export してから実行します。

```bash
export AGENT_LLM_PROVIDER=openai
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-4.1-mini"
uv run --python /home/penne/.local/bin/python3.12 python -m app.main chat "Should we implement now?"
```

対応 provider:

- `openai`: `OPENAI_API_KEY`, `OPENAI_MODEL` または `AGENT_LLM_MODEL`
- `claude`: `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` または `AGENT_LLM_MODEL`
- `gemini`: `GEMINI_API_KEY`, `GEMINI_MODEL` または `AGENT_LLM_MODEL`
- `openrouter`: `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` または `AGENT_LLM_MODEL`

現在の provider 設定は key 値を表示せずに確認できます。

```bash
uv run --python /home/penne/.local/bin/python3.12 python -m app.main inspect llm-provider
```

provider smoke は通常の cognition loop とは分離された疎通確認です。credential
がない環境では外部接続せず `SKIPPED` として trace します。

```bash
uv run --python /home/penne/.local/bin/python3.12 python -m app.main llm smoke
```

offline path を明示確認する場合:

```bash
AGENT_LLM_PROVIDER=mock \
uv run --python /home/penne/.local/bin/python3.12 python -m app.main llm smoke
```

real provider を 1 回だけ確認する場合は、provider、API key、model を shell で明示します。
複数 provider の credential が環境にある場合、`AGENT_LLM_PROVIDER` なしでは実行しません。

```bash
export AGENT_LLM_PROVIDER=openai
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-4.1-mini"
uv run --python /home/penne/.local/bin/python3.12 python -m app.main llm smoke
```

smoke は `provider-smoke-ok` marker、latency、usage metadata が取れた場合の
usage、sanitized error を `actions` / `outcomes` に保存します。API key、
Authorization header、raw request / response payload は保存しません。

## テストとドキュメント検証

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest
./scripts/check-docs.sh
```

GitHub Actions では `Pytest CI` が Python 3.12 と `uv sync --locked`
で依存関係を再現し、`AGENT_LLM_PROVIDER=mock`、
`AGENT_OBSERVATION_EXTRACTOR=deterministic`、
`AGENT_DISCORD_ENABLED=false`、`AGENT_DISCORD_MODE=observe_only`、
`AGENT_DISCORD_MAX_MODE=observe_only` で `uv run pytest` と deterministic
PoC verification script を実行します。verification JSON は runner temp に出力し、
リポジトリにはコミットしません。CI は実 LLM provider、実 Web search、live Discord、
secrets を要求しません。
ドキュメント検証は既存の `Docs CI` が `scripts/check-docs.sh` 相当の
validator 群を実行します。

QA 計画と検証証跡は `_docs/qa/Core/memory-ecology-poc/` にあります。実装判断は `_docs/intent/Core/memory-ecology-poc/decision.md`、詳細リファレンスは `_docs/reference/Core/memory-ecology-poc/reference.md` を参照してください。

## 既知の制限

- LLM は `MockLLMClient` が既定です。OpenAI / Claude / Gemini / OpenRouter は HTTPS JSON client として実装済みですが、streaming、tool call、multimodal、provider-specific structured output は未対応です。
- Web search は interface / stub のみです。
- scheduler は実 cron ではなく、`wake_requests` の採否として記録します。
- observation / digest / concern lifecycle / attention policy update は heuristic v0 です。
- Discord live guild startup / command sync は credentials がある環境での手動確認が必要です。
- dashboard、Postgres、pgvector、embedding search は未実装です。

## 履歴資料

実装元の一回限り prompt / reference は root active guidance から外し、非運用資料として `_evals/prompts/` に移しました。

- `_evals/prompts/memory-ecology-agent-poc.md`
- `_evals/prompts/memory-ecology-agent-reference.md`

## ライセンス

このリポジトリは [MIT License](LICENSE.txt) の下でライセンスされています。
