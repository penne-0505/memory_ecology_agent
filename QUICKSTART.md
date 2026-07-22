# Quickstart

Memory Ecology Agent PoC は、入力 ecology から probe / observation / concern / action / outcome / attention policy / response trace がどう変化するかを観測するためのローカル CLI 実験です。このファイルは、初回実行と検証の最短導線です。

## 1. 最初に読むファイル

- [AGENTS.md](AGENTS.md)
- [TODO.md](TODO.md)
- [README.md](README.md)
- [_docs/documentation_guide.md](_docs/documentation_guide.md)
- [_docs/standards/documentation_guidelines.md](_docs/standards/documentation_guidelines.md)
- [_docs/standards/documentation_operations.md](_docs/standards/documentation_operations.md)
- [_docs/standards/quality_assurance.md](_docs/standards/quality_assurance.md)
- [_docs/standards/security_for_agents.md](_docs/standards/security_for_agents.md)
- [_docs/reference/Core/memory-ecology-poc/reference.md](_docs/reference/Core/memory-ecology-poc/reference.md)

## 2. 初回セットアップと実行

```bash
uv run --python /home/penne/.local/bin/python3.12 python -m app.main init
uv run --python /home/penne/.local/bin/python3.12 python -m app.main seed
uv run --python /home/penne/.local/bin/python3.12 python -m app.main wake --reason cron
uv run --python /home/penne/.local/bin/python3.12 python -m app.main chat "Should we implement now?"
uv run --python /home/penne/.local/bin/python3.12 python -m app.main eval run
```

隔離環境で試す場合:

```bash
tmpdir=$(mktemp -d)
uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root "$tmpdir" init
uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root "$tmpdir" seed
uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root "$tmpdir" wake --reason cron
```

## 3. Trace inspection

```bash
uv run --python /home/penne/.local/bin/python3.12 python -m app.main inspect concerns
uv run --python /home/penne/.local/bin/python3.12 python -m app.main inspect probes
uv run --python /home/penne/.local/bin/python3.12 python -m app.main inspect digest-decisions
uv run --python /home/penne/.local/bin/python3.12 python -m app.main inspect digest-proposals
uv run --python /home/penne/.local/bin/python3.12 python -m app.main inspect attention-policy
uv run --python /home/penne/.local/bin/python3.12 python -m app.main inspect outcomes
uv run --python /home/penne/.local/bin/python3.12 python -m app.main inspect wake-requests
uv run --python /home/penne/.local/bin/python3.12 python -m app.main inspect traces
uv run --python /home/penne/.local/bin/python3.12 python -m app.main inspect llm-provider
uv run --python /home/penne/.local/bin/python3.12 python -m app.main llm smoke
uv run --python /home/penne/.local/bin/python3.12 python -m app.main eval compare --prompt-id 1
```

replay の response text drift を deterministic に確認する場合:

```bash
AGENT_LLM_PROVIDER=state_sensitive_mock \
uv run --python /home/penne/.local/bin/python3.12 python -m app.main eval run --prompt-id 1
```

credential がない環境で `llm smoke` を実行すると、外部接続せず
`SKIPPED: no real provider credentials configured` を表示します。real provider を
1 回だけ確認する場合は、`AGENT_LLM_PROVIDER`、provider-specific API key、model を
shell で明示してから `llm smoke` を実行します。複数 provider credential がある環境では
明示 provider なしに自動選択しません。

LLM digest proposal を見る場合は、通常の smoke とは別に isolated project root で
`AGENT_DIGEST_DECIDER=llm_shadow` を明示します。credential がない環境では実 provider
smoke は SKIPPED とし、CI では mock/fake provider のみを使います。

## 4. Discord adapter smoke

Discord は既定で無効です。設定の見え方と既存 DB との接続は token なしで確認できます。

```bash
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord status
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord doctor
```

live bot を動かす場合は `.env.example` の `AGENT_DISCORD_*` と `DISCORD_BOT_TOKEN` を shell で設定してから実行します。

```bash
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord doctor --mode observe_only --live
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord run --dry-run
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord cycle wake --reason scheduled
uv run --python /home/penne/.local/bin/python3.12 python -m app.main discord run
```

mode は `observe_only` から始め、検証後に `ingest_enabled`、`command_enabled`、`autonomous_posting_enabled` へ段階的に上げます。詳しくは [_docs/guide/Core/discord-integration/usage.md](_docs/guide/Core/discord-integration/usage.md) を参照してください。

## 5. 作業ルール

- `world/` は read-only input ecology。
- `agent_workspace/` は agent が書き込める作業領域。
- root の一回限り prompt は active guidance にしない。履歴として残す場合は `_evals/prompts/` に置き、非運用資料と明記する。
- `rm` / `git rm` は使わない。
- Size >= M または Risk >= Medium の変更では Plan / Intent / QA / Verification を更新する。

## 6. 検証コマンド

アプリ側:

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest
```

ドキュメント側:

```bash
deno fmt --check scripts/*.mjs
deno run --allow-read scripts/validate-frontmatter.mjs
deno run --allow-read scripts/validate-todo.mjs
deno run --allow-read scripts/validate-doc-links.mjs
deno run --allow-read scripts/validate-qa.mjs
deno run --allow-read --allow-run scripts/test-validators.mjs
```

まとめて実行する場合:

```bash
./scripts/check-docs.sh
```
