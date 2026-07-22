---
title: LLM Provider Integrations Design Intent
status: active
draft_status: n/a
created_at: 2026-05-30
updated_at: 2026-06-02
references:
  - "_docs/plan/Core/llm-provider-integrations/plan.md"
  - "_docs/qa/Core/llm-provider-integrations/test-plan.md"
  - "_docs/reference/Core/memory-ecology-poc/reference.md"
related_issues: []
related_prs: []
---

## Context

初期 PoC は外部 API key なしで検証できるよう `MockLLMClient` を既定にし、real LLM provider は `ManualLLMClient` stub に留めていた。次の段階では OpenAI、Claude、Gemini (Google AI Studio)、OpenRouter を実 provider として差し替え可能にする必要がある。ただし、PoC の品質軸は traceability と安全境界であり、secret 漏洩や provider 依存でテストが不安定になることは避ける。

provider 本体の fake transport 検証だけでは、credential がある環境で「1 回だけ安全に実 provider を呼ぶ」運用 path は確認できない。そこで product loop を real provider 化せず、専用の smoke command と trace record だけを追加する。

## Decision

- SDK ではなく標準ライブラリの HTTPS JSON transport を使う。
- provider は `AGENT_LLM_PROVIDER` で選ぶ。既定は `mock`。
- API key は provider-specific env var から読み、model は `AGENT_LLM_MODEL` または provider-specific model env var から読む。
- OpenAI / OpenRouter は Chat Completions compatible client として共通化する。
- Claude は Messages API client として実装する。
- Gemini は `generateContent` client として実装する。
- provider 出力の JSON は text から抽出して Pydantic validation する。validation failure と HTTP error は secret や provider response body を含めない message で例外にする。
- request / response logging はしない。fake transport による unit test で request shape を確認する。
- real provider 疎通は `python -m app.main llm smoke` に閉じ込める。
- `llm smoke` は credential がない場合に skip し、複数 provider credential がある場合は `AGENT_LLM_PROVIDER` の明示選択を要求する。
- `llm smoke` は marker `provider-smoke-ok` を低 token budget / 短 timeout で確認し、結果を `llm_provider_smoke` action と outcome に sanitized metadata として保存する。
- LLM-backed observation extraction と digest decision proposals は同じ provider factory を使えるが、各 feature flag が明示されるまで provider call は行わない。

## Alternatives

- **公式 SDK を追加する**: provider ごとの保守は楽になるが依存が増え、PoC の境界が重くなるため不採用。
- **OpenAI-compatible API だけに寄せる**: OpenRouter には合うが、Claude / Gemini の native API 指定を満たさないため不採用。
- **real provider を既定にする**: 外部 API key なしの検証性を壊すため不採用。
- **provider response を raw_event に保存する**: traceability は増えるが、外部入力や secret 周辺情報の保存リスクが増えるため不採用。

## Rationale

`LLMClient` の `complete_text` / `complete_json` 境界を保つと、runtime cycles は provider 詳細を知らずに済む。標準ライブラリの HTTP transport と fake transport を分けることで、実 API 呼び出しなしに request shape / parse / validation をテストできる。model を明示設定にすることで、provider のモデル名変更に引きずられにくくする。

## Consequences / Impact

- 実 provider 利用には API key と model の明示設定が必要になる。
- JSON mode / structured output の provider-specific 機能は使わず、prompt + Pydantic validation に留める。
- provider API の仕様変更時は adapter と docs の更新が必要。
- OpenRouter の optional attribution headers は環境変数がある場合のみ送る。
- credential がない環境の `llm smoke` は PASS ではなく SKIPPED として扱われる。
- smoke trace は provider response text 全文や raw HTTP headers を残さないため、品質評価や debugging の情報量は意図的に制限される。

## Quality Implications

- 既定で外部接続しないことをテストで守る。
- API key が不足している場合、値を表示せずに設定エラーにする。
- Authorization / key header をログや DB に残さない。
- provider response の parse 失敗は明示的な例外とし、DB state update を進めない。
- smoke trace は success / failure / skipped を区別し、secret 値を payload に含めない。
- smoke command は core profile、Discord mode、Web search stub、CI offline 境界を変更しない。

## Intent-derived Invariants

- INV-001: `AGENT_LLM_PROVIDER` 未指定時は `MockLLMClient` を使い、外部ネットワークに接続しない。
- INV-002: real provider client は API key と model が未設定なら secret を含まない configuration error を返す。
- INV-003: OpenAI / OpenRouter request は Chat Completions compatible body (`model`, `messages`, `max_completion_tokens`) と Bearer auth を使う。
- INV-004: Claude request は `x-api-key`, `anthropic-version`, `messages`, `max_tokens` を含む Messages API body を使う。
- INV-005: Gemini request は `x-goog-api-key` header と `generateContent` contents body を使う。
- INV-006: `complete_json` は JSON 抽出後に Pydantic validation し、失敗時は secret を含めず例外にする。
- INV-007: CLI `chat` / `eval run` は provider factory を使い、Mock 既定の既存挙動を保つ。
- INV-008: `llm smoke` は credential 未設定時に skip し、外部 network call を行わない。
- INV-009: `llm smoke` は複数 real provider credential を明示 selection なしに自動選択しない。
- INV-010: `llm smoke` trace は API key、Authorization header、raw request / response payload、secret 値を保存しない。
- INV-011: `llm smoke` は core profile を変更せず、Discord / Web search / normal CI を有効化しない。

## Rollback / Follow-ups

- rollback は `AGENT_LLM_PROVIDER=mock` に戻すだけでよい。
- follow-up 候補: provider-specific structured output、streaming、tool call、retry/backoff、usage metadata の安全な集計。
