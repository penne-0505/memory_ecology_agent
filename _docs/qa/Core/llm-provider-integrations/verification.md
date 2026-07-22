---
title: "QA Verification: LLM Provider Integrations"
status: active
draft_status: n/a
qa_status: verified
risk: High
created_at: 2026-05-30
updated_at: 2026-06-02
references:
  - "_docs/qa/Core/llm-provider-integrations/test-plan.md"
  - "_docs/intent/Core/llm-provider-integrations/decision.md"
  - "_docs/plan/Core/llm-provider-integrations/plan.md"
  - "_docs/reference/Core/memory-ecology-poc/reference.md"
related_issues: []
related_prs: []
---

## Summary

OpenAI、Claude、Gemini (Google AI Studio)、OpenRouter の provider client を `LLMClient` 境界に追加し、default mock の既存挙動を維持した。さらに `python -m app.main llm smoke` を追加し、mock/offline smoke、credential 未設定時の skipped path、fake transport による real provider success/failure trace、複数 credential の明示選択 gate を確認した。

provider API key は環境変数からのみ読み、request / response body と API key header を DB、trace、docs、provider error message に保存しない構成を確認した。2026-06-02 に OpenRouter / `deepseek/deepseek-v4-pro` の live smoke も実行し、reasoning token が marker 出力を阻害しないよう smoke に限って OpenRouter reasoning を無効化したうえで PASS を確認した。

## Verification Verdict

Verdict: PASS

## Commands Run

| Command / Test | Result |
| --- | --- |
| `date +%F` | PASS: `2026-06-02` |
| `uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_llm.py tests/test_llm_smoke.py -q` | PASS: 20 passed |
| `uv run --python /home/penne/.local/bin/python3.12 pytest` | PASS: 59 passed, 1 warning from `discord/player.py` using deprecated `audioop` |
| `git diff --check` | PASS: no whitespace errors |
| `./scripts/check-docs.sh` | PASS: docs validators and validator fixtures passed |
| `uv run --python /home/penne/.local/bin/python3.12 python -m app.main inspect llm-provider` | PASS: provider `mock`, model unset/provider-specific, `max_tokens=1024`, `timeout_seconds=30.0`; no key value displayed |
| `AGENT_LLM_PROVIDER=mock uv run --python /home/penne/.local/bin/python3.12 python -m app.main llm smoke` | PASS: `OK: provider-smoke-ok`, provider `mock`, marker present, action/outcome trace created |
| `env -u ... uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root "$tmpdir" llm smoke` | PASS: `SKIPPED: no real provider credentials configured`, no real provider selected, action/outcome trace created |
| `AGENT_LLM_PROVIDER=openrouter OPENROUTER_MODEL=deepseek/deepseek-v4-pro ... python -m app.main llm smoke` | ATTEMPTED: provider responded, usage returned, but marker absent because all 16 completion tokens were reasoning tokens |
| `AGENT_LLM_PROVIDER=openrouter OPENROUTER_MODEL=deepseek/deepseek-v4-pro ... python -m app.main llm smoke` after OpenRouter smoke reasoning disable | PASS: `OK: provider-smoke-ok`, provider `openrouter`, response model `deepseek/deepseek-v4-pro-20260423`, marker present, usage returned |

## Automated Test Results

`uv run --python /home/penne/.local/bin/python3.12 pytest`

```text
59 passed, 1 warning in 0.93s
```

`uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_llm.py tests/test_llm_smoke.py -q`

```text
20 passed
```

`git diff --check`

```text
no output
```

`./scripts/check-docs.sh`

```text
Checked 5 files
PASS todo _evals/validator-fixtures/todo/valid/basic.md
PASS qa _evals/validator-fixtures/qa/valid
```

## Manual QA Results

- `inspect llm-provider` displayed provider, model selector state, max token setting, and timeout without showing any API key value.
- `llm smoke` with `AGENT_LLM_PROVIDER=mock` returned `provider-smoke-ok` and wrote `llm_provider_smoke` action/outcome records.
- `llm smoke` with all known provider env vars unset returned `SKIPPED: no real provider credentials configured` in an isolated project root.
- fake transport tests confirmed real provider smoke request uses low token budget (`16`), short timeout (`15.0`), and deterministic temperature (`0.0`) without writing API key or raw payload to trace.
- OpenRouter live smoke with `deepseek/deepseek-v4-pro` initially failed marker detection because the model used the whole completion budget for reasoning tokens; smoke now sends `reasoning: {"effort": "none", "exclude": true}` for OpenRouter only.
- OpenRouter live smoke then returned `OK: provider-smoke-ok` with response model `deepseek/deepseek-v4-pro-20260423`, `marker_present=true`, `latency_ms=1866`, `total_tokens=37`, and `reasoning_tokens=0`.
- `.env.example`, README, QUICKSTART, and reference docs were checked for env var names only; no API key values are present.
- Official API families were checked against provider docs: [OpenAI Chat Completions](https://platform.openai.com/docs/api-reference/chat/create), [Anthropic Messages](https://docs.anthropic.com/ja/api/messages), [Gemini `generateContent`](https://ai.google.dev/api/generate-content), [OpenRouter Chat Completions](https://openrouter.ai/docs/api-reference/chat-completion), and [OpenRouter reasoning tokens](https://openrouter.ai/docs/use-cases/reasoning-tokens).

## Acceptance Criteria Coverage

- AC-001: PASS. `tests/test_llm.py` covers provider factory creation for OpenAI, Claude, Gemini, and OpenRouter using env-based API key / model selection.
- AC-002: PASS. Fake transport tests verify each provider's URL, auth header, request body, and text response parsing.
- AC-003: PASS. Provider `complete_json` extracts fenced/plain JSON and validates with Pydantic; invalid output raises without logging secret values.
- AC-004: PASS. CLI `chat` and `eval run` pass `Settings` into the provider factory while preserving the default mock path.
- AC-005: PASS. README, `.env.example`, and reference docs describe provider selection, required env vars, safety boundaries, and real API smoke caveats.
- AC-006: PASS. Full pytest passed without external API credentials.
- AC-007: PASS. `tests/test_llm_smoke.py` and CLI smoke verify `llm smoke` mock/offline marker success.
- AC-008: PASS. `tests/test_llm_smoke.py` and isolated CLI smoke verify credential-less skipped behavior without network calls.
- AC-009: PASS. `tests/test_llm_smoke.py` verifies multiple real provider credentials fail without explicit `AGENT_LLM_PROVIDER`.
- AC-010: PASS. `tests/test_llm_smoke.py` verifies fake real provider success/failure traces include provider/model/status/usage/error metadata without secret values.
- AC-011: PASS. `tests/test_llm_smoke.py` verifies core profile stability; docs and CI remain mock/offline.

## Invariant Coverage

- INV-001: PASS. Default factory returns `MockLLMClient` and tests do not perform network calls.
- INV-002: PASS. Missing real-provider API key produces `LLMConfigurationError` without key values; HTTP error messages omit provider response bodies.
- INV-003: PASS. OpenAI / OpenRouter tests verify `POST /chat/completions`, Bearer auth, `messages`, and `max_completion_tokens`.
- INV-004: PASS. Claude test verifies `POST /messages`, `x-api-key`, `anthropic-version`, `messages`, and `max_tokens`.
- INV-005: PASS. Gemini test verifies `:generateContent`, `x-goog-api-key`, `contents`, and `generationConfig.maxOutputTokens`.
- INV-006: PASS. JSON validation success and failure paths are covered, including fenced JSON extraction.
- INV-007: PASS. Existing chat / replay eval tests and CLI smoke confirm runtime calls provider factory and default mock behavior remains intact.
- INV-008: PASS. No-credential smoke returns skipped and fake transport call count remains zero.
- INV-009: PASS. Multiple credential smoke fails with an explicit provider selection message.
- INV-010: PASS. Smoke action payload includes sanitized metadata only; tests assert API key value, Authorization header, and raw message payload are absent.
- INV-011: PASS. Smoke does not mutate `core_profiles` and does not enable Discord, Web search, wake, review, reflection, or CI real provider behavior.

## Deferred / Not Covered

- Live real API smoke was run for OpenRouter with `deepseek/deepseek-v4-pro` only. OpenAI, Claude, Gemini, and other OpenRouter models were not run.
- Real provider quality, latency benchmarking, retry/backoff, streaming, tool calls, multimodal support, and provider-specific structured output remain out of scope.

## Residual Risks

None

## Follow-up TODOs

None. Run `python -m app.main llm smoke` with an explicit provider and credential/model pair when a human wants to verify live connectivity.
