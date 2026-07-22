---
title: "QA Test Plan: LLM Provider Integrations"
status: active
draft_status: n/a
qa_status: planned
risk: High
created_at: 2026-05-30
updated_at: 2026-06-02
references:
  - "_docs/intent/Core/llm-provider-integrations/decision.md"
  - "_docs/plan/Core/llm-provider-integrations/plan.md"
related_issues: []
related_prs: []
---

# QA Test Plan: `LLM Provider Integrations`

## Source of Intent

- TODO: `Core-Enhance-6`, `Core-Enhance-10`
- Plan: `_docs/plan/Core/llm-provider-integrations/plan.md`
- Intent: `_docs/intent/Core/llm-provider-integrations/decision.md`
- Existing reference: `_docs/reference/Core/memory-ecology-poc/reference.md`

## Quality Goal

OpenAI、Claude、Gemini、OpenRouter を `LLMClient` 境界に追加しつつ、既定では外部 API に接続せず、secret を保存・表示しないことを確認する。実 API 呼び出しは credentials 依存のため自動テスト対象にせず、fake transport で request shape と response parsing を検証する。

追加の smoke path では、credential がある環境で 1 provider だけを opt-in で呼べること、credential がない環境では `SKIPPED` として扱うこと、結果が `actions` / `outcomes` に secret なしで trace されることを確認する。

## Acceptance Criteria

- AC-001: `AGENT_LLM_PROVIDER` と provider-specific API key / model 環境変数から OpenAI、Claude、Gemini、OpenRouter の client を生成できる。
- AC-002: 各 provider client が公式 API 仕様に沿った HTTPS JSON request を組み立て、text response を `complete_text` として返す。
- AC-003: `complete_json` は provider output を JSON として parse し、Pydantic validation 成功時だけ schema instance を返し、失敗時は secret を含めない error log を残して例外にする。
- AC-004: CLI の `chat` / `eval run` が `Settings` の provider 選択を使い、既定では外部 API に接続しない Mock のまま動く。
- AC-005: README / reference / `.env.example` に provider 選択、必要な環境変数、安全境界、実 API smoke の注意が書かれている。
- AC-006: pytest が外部 API key なしで、factory、request shape、response parse、JSON validation、CLI default mock を検証して通る。
- AC-007: `python -m app.main llm smoke` が mock/offline path で deterministic marker を確認できる。
- AC-008: `llm smoke` は credential がない場合に外部接続せず `SKIPPED: no real provider credentials configured` を返す。
- AC-009: `llm smoke` は複数 real provider credential を検出した場合、明示 provider selection なしに provider を選ばない。
- AC-010: fake transport による real provider smoke success / failure が action/outcome trace に保存され、secret 値を含まない。
- AC-011: `llm smoke` は core profile、Discord mode、Web search stub、normal CI の offline 境界を変更しない。

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

## Risk Assessment

- Risk level: High
- Risk rationale: 外部 API、secret、network error、provider-specific payload に触れる。
- Regression risk: 既存の Mock default / pytest / CLI smoke を壊す可能性がある。
- Data safety risk: request / response body や API key を DB / logs に残さない必要がある。
- Security / privacy risk: Authorization / API key header の漏洩が主リスク。
- UX risk: env var 不足時の error がわかりにくいと利用時に迷う。
- Agent misbehavior risk: 実 API key なしの環境で real provider smoke を「通った」と書くリスクがある。
- Trace risk: smoke 結果を保存するときに provider response body や secret-like error を保存してしまうリスクがある。

## Test Strategy

- Unit: provider factory、configuration error、request body/header shape、response text extraction、JSON extraction / validation。
- Integration: CLI `chat` / `eval run` default mock smoke。
- Integration: CLI `llm smoke` mock success と no-credential skipped path。
- E2E: 実 provider smoke は credentials がある場合のみ任意で実施し、未実施なら verification に明記する。
- Manual QA: README / reference / `.env.example` が secret を書かず、env var 名と安全境界を示すこと。
- Validator / static check: `./scripts/check-docs.sh`, `git diff --check`。
- Diff review: API key 値、Authorization header 値、request payload をログに出していないこと。

## Test Matrix

| ID | Source | Requirement / Invariant | Test Type | Command / File | Expected Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| AC-001 | TODO | provider env から各 client を生成できる。 | unit | `tests/test_llm.py` | OpenAI / Claude / Gemini / OpenRouter の factory tests が通る。 | verified |
| AC-002 | TODO | 各 provider が正しい request shape を組む。 | unit | `tests/test_llm.py` | fake transport が URL / header / body を確認する。 | verified |
| AC-003 | TODO | complete_json が JSON parse + Pydantic validation を行う。 | unit | `tests/test_llm.py` | valid JSON は schema、invalid は例外。 | verified |
| AC-004 | TODO | CLI が factory を使い、default mock を維持する。 | integration | `tests/test_chat_replay_context.py` / CLI smoke | 外部 key なしで chat / eval が通る。 | verified |
| AC-005 | TODO | docs が provider env と安全境界を説明する。 | diff review | `README.md`, `.env.example`, reference | key 値を書かず env var 名だけを説明する。 | verified |
| AC-006 | TODO | pytest が外部 API key なしで通る。 | automated | `uv run --python /home/penne/.local/bin/python3.12 pytest` | 全テスト PASS。 | verified |
| AC-007 | TODO | `llm smoke` mock/offline path が marker を確認する。 | integration | `tests/test_llm_smoke.py` / CLI smoke | `status=success`, marker present, no network。 | verified |
| AC-008 | TODO | credential なしは skipped で外部接続しない。 | integration | `tests/test_llm_smoke.py` / CLI smoke | `SKIPPED: no real provider credentials configured`。 | verified |
| AC-009 | TODO | 複数 credential は明示選択なしに選ばない。 | unit | `tests/test_llm_smoke.py` | nonzero / configuration error message が出る。 | verified |
| AC-010 | TODO | fake real smoke success/failure が sanitized trace になる。 | unit | `tests/test_llm_smoke.py` | action/outcome payload に provider/model/status/usage/error があり secret がない。 | verified |
| AC-011 | TODO | smoke は core profile と offline 境界を変えない。 | integration | `tests/test_llm_smoke.py` / docs diff | core profile row unchanged; CI docs remain mock/offline。 | verified |
| INV-001 | intent | default は Mock で外部接続しない。 | unit | `tests/test_llm.py` | no env factory returns MockLLMClient。 | verified |
| INV-002 | intent | missing key/model は secret なし config error。 | unit | `tests/test_llm.py` | error message に key 値が含まれない。 | verified |
| INV-003 | intent | OpenAI / OpenRouter は Chat Completions compatible。 | unit | `tests/test_llm.py` | `/chat/completions`, Bearer auth, `messages`, `max_completion_tokens`。 | verified |
| INV-004 | intent | Claude は Messages API shape。 | unit | `tests/test_llm.py` | `/messages`, `x-api-key`, `anthropic-version`, `max_tokens`。 | verified |
| INV-005 | intent | Gemini は generateContent shape。 | unit | `tests/test_llm.py` | `:generateContent`, `x-goog-api-key`, `contents`。 | verified |
| INV-006 | intent | JSON validation failure は secret なしで例外。 | unit | `tests/test_llm.py` | `ValidationError` or provider parse error。 | verified |
| INV-007 | intent | chat/eval は factory を使う。 | integration | `tests/test_chat_replay_context.py` | default mock response が維持される。 | verified |
| INV-008 | intent | no credential smoke は network なしで skip。 | unit | `tests/test_llm_smoke.py` | fake transport call count 0。 | verified |
| INV-009 | intent | 複数 credential は自動選択されない。 | unit | `tests/test_llm_smoke.py` | explicit provider を求める error。 | verified |
| INV-010 | intent | smoke trace は secret / raw payload を保存しない。 | unit | `tests/test_llm_smoke.py` | DB payload と stdout に key 値がない。 | verified |
| INV-011 | intent | smoke は core profile / Discord / Web search / CI offline を変えない。 | integration | `tests/test_llm_smoke.py`, `.github/workflows/pytest-ci.yml` | core profile unchanged; CI remains mock/offline。 | verified |

## Manual QA Checklist

- [x] `.env.example` に API key の実値がない。
- [x] README が provider 選択の env var を示している。
- [x] README / QUICKSTART が `llm smoke` の skipped / mock / real opt-in 境界を示している。
- [x] reference が provider ごとの endpoint family と response parsing を説明している。
- [x] verification が実施していない real API smoke を PASS と書いていない。

## Regression Checklist

- [x] 既存 13 tests が引き続き通る。
- [x] `chat` / `eval run` が no API key で Mock として通る。
- [x] `llm smoke` が no API key で skipped として通る。
- [x] docs validators が通る。

## High-risk Checklist

- [x] Rollback path is documented: set `AGENT_LLM_PROVIDER=mock`.
- [x] Recovery path is documented: missing credentials fail before network calls.
- [x] Data safety has been checked: no API key values in docs, tests, logs, or DB writes.
- [x] Security / privacy implications have been checked: request/response payloads are not logged.
- [x] Failure mode is understood: network/provider errors raise provider errors without state mutation by `complete_json` callers.

## Out of Scope

- Streaming、tool call、multimodal、provider-specific structured output。
- 実 API credentials を使った CI。
- usage/cost metadata の永続化。

## Open Questions

- なし。model 名は provider 側の変更に追従するため env var で明示指定する。
