---
title: LLM Provider Integrations Plan
status: active
draft_status: n/a
created_at: 2026-05-30
updated_at: 2026-06-02
references:
  - "_docs/intent/Core/llm-provider-integrations/decision.md"
  - "_docs/qa/Core/llm-provider-integrations/test-plan.md"
  - "_docs/reference/Core/memory-ecology-poc/reference.md"
related_issues: []
related_prs: []
---

## Overview

`app/adapters/llm.py` の `LLMClient` 境界を維持したまま、OpenAI、Claude、Gemini (Google AI Studio)、OpenRouter の実 HTTP provider を追加する。既定は外部 API に接続しない `MockLLMClient` のままとし、provider は環境変数で明示選択する。

## Scope

- provider factory を追加し、`AGENT_LLM_PROVIDER` で `mock`, `manual`, `openai`, `claude`, `gemini`, `openrouter` を選択できるようにする。
- API key と model は環境変数から読む。secret は DB、ログ、docs、trace に保存しない。
- OpenAI / OpenRouter は OpenAI-compatible Chat Completions request を組み立てる。
- Claude は Anthropic Messages API request を組み立てる。
- Gemini は Google AI Studio / Gemini `generateContent` REST request を組み立てる。
- `complete_json` は provider 出力を JSON として抽出し、Pydantic validation 成功時だけ返す。
- CLI の `chat` と `eval run` は factory から client を取得する。
- `llm smoke` CLI を追加し、mock/offline smoke と opt-in real provider smoke を分けて実行できるようにする。
- observation extraction と digest decision proposals は provider factory を利用できるが、どちらも明示 feature flag がない限り real provider を呼ばない。
- real provider smoke は credential がない場合に skip し、複数 provider credential がある場合は `AGENT_LLM_PROVIDER` の明示選択を要求する。
- smoke 結果は既存の `actions` / `outcomes` に、secret を含まない provider / model / status / marker / latency / usage / error metadata として保存する。
- fake transport を使った unit tests を追加し、外部 API key なしで request shape と response parse を検証する。
- README、reference、`.env.example` を更新する。

## Non-Goals

- SDK package の追加。
- streaming、tool call、multimodal、function calling、structured output API の provider-specific 最適化。
- 実 API credential を使った自動 CI。
- provider response / request payload の DB 永続化。
- `llm smoke` から wake / review / reflection / observation extraction を実 provider 化すること。
- digest decision proposal を既定で有効化すること。
- 複数 real provider の benchmark や品質評価。

## Requirements

- **Functional**: `create_llm_client(settings)` が provider 名から適切な `LLMClient` を返す。
- **Functional**: model 未設定または API key 未設定の real provider は、secret を含まない configuration error を返す。
- **Functional**: `complete_text` は provider response から text を抽出する。
- **Functional**: `complete_json` は markdown fence 付き JSON も許容して schema validation する。
- **Functional**: `chat` / `eval run` は default mock のまま従来テストを壊さず、provider 環境変数がある場合のみ real provider を使う。
- **Functional**: `llm smoke` は credential 未設定時に `SKIPPED: no real provider credentials configured` を表示し、外部接続しない。
- **Functional**: `llm smoke` は複数 real provider credential が検出され、明示 provider がない場合に nonzero で止まる。
- **Functional**: `llm smoke` は marker `provider-smoke-ok` を小さい prompt / token budget / timeout で確認する。
- **Non-Functional**: network call は fake transport で差し替え可能にする。
- **Non-Functional**: API key、Authorization header、request payload、provider response body はログや provider error message に出さない。
- **Non-Functional**: smoke trace は core profile を変更せず、Discord / Web search / normal CI を有効化しない。

## Tasks

- `Settings` に provider / model / timeout / max_tokens を追加する。
- `app/adapters/llm.py` に HTTP transport、configuration error、provider clients、factory を追加する。
- `app/runtime/chat_cycle.py`、`app/eval/replay.py`、`app/cli/commands.py` を provider factory に接続する。
- `app/runtime/llm_smoke.py` を追加し、provider selection、marker check、sanitized action/outcome trace を閉じ込める。
- `app/cli/commands.py` に `llm smoke` subcommand を追加する。
- provider request / response tests と factory tests を追加する。
- provider smoke の skipped / mock success / fake real success / sanitized failure / core profile stability tests を追加する。
- README / reference / `.env.example` / QA verification を更新する。

## QA Plan

- QA document: `_docs/qa/Core/llm-provider-integrations/test-plan.md`
- Risk level: High
- Test strategy:
  - Unit: provider factory、request headers/body、response parse、JSON validation failure。
  - Integration: CLI default mock smoke、`llm smoke` skipped path、existing wake/chat/eval tests。
  - Manual QA: docs の env var と provider safety boundary を確認。
  - Static check: `./scripts/check-docs.sh`、`git diff --check`。
- 実 API key を使った smoke は任意。verification では未実施なら未実施と明記する。

## Deployment / Rollout

- 既定 provider は `mock` のままなので、既存ローカル実行と pytest は外部接続しない。
- real provider を使う場合のみ環境変数を export する。
- 問題があれば `AGENT_LLM_PROVIDER=mock` に戻す。
