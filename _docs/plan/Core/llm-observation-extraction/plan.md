---
title: LLM Observation Extraction Plan
status: active
draft_status: n/a
created_at: 2026-06-02
updated_at: 2026-06-02
references:
  - "_docs/intent/Core/llm-observation-extraction/decision.md"
  - "_docs/qa/Core/llm-observation-extraction/test-plan.md"
  - "_docs/reference/Core/memory-ecology-poc/reference.md"
  - "_docs/qa/Core/llm-provider-integrations/verification.md"
related_issues: []
related_prs: []
---

## Overview

LLM-backed observation extraction を feature flag の背後に追加する。LLM は raw input から `ObservationDraft` proposal を作るだけで、保存後の digest decision、concern lifecycle、memory creation、attention_policy update、action / outcome、replay trace は既存 deterministic pipeline に通す。

## Scope

- `AGENT_OBSERVATION_EXTRACTOR=deterministic|llm` を追加し、既定は `deterministic` にする。
- LLM extraction mode では `create_llm_client(settings)` 経由で provider を呼び、validated observation proposal を返す。
- LLM output schema を Pydantic で検証し、score clamp、disposition allowlist、長さ制限、短い evidence quote を適用する。
- fallback mode は既定で deterministic に戻し、observation rationale と digest metadata に sanitized warning を残す。
- prompt file を追加し、observation と digest / concern / memory / attention_policy の境界を明示する。
- tests と docs で default offline、opt-in LLM、fallback、安全境界を確認する。

## Non-Goals

- real provider usage を既定にしない。
- CI で real provider credential を要求しない。
- deterministic extractor を置き換えない。
- LLM-backed digest decision、concern mutation、memory creation、attention_policy update、core_profile mutation を実装しない。
- real Web search と Discord operational mode は変更しない。
- raw provider response は DB / trace / docs に保存しない。

## Requirements

- **Functional**: `AGENT_OBSERVATION_EXTRACTOR` が `deterministic` のとき既存 wake behavior を維持する。
- **Functional**: `AGENT_OBSERVATION_EXTRACTOR=llm` のときだけ LLM extraction を試みる。
- **Functional**: LLM extraction failure は既定で deterministic fallback になり、strict mode のみ例外を許可する。
- **Functional**: digest trace metadata から extractor、provider、fallback reason を確認できる。
- **Non-Functional**: provider API key、Authorization header、raw request / response payload、長い input quote を保存しない。
- **Non-Functional**: tests は mock/fake transport のみで実行できる。

## Tasks

- Settings に observation extractor mode と fallback mode を追加する。
- `app/cognition/observation_extractor.py` を deterministic / LLM / selector に分ける。
- prompt file `app/prompts/observation_extraction_llm.md` を追加する。
- wake cycle を selector に接続し、digest metadata に extractor metadata を渡す。
- tests に deterministic default、LLM success、fallback、strict failure、安全な trace metadata を追加する。
- README / reference / QA docs を更新する。

## QA Plan

- QA document: `_docs/qa/Core/llm-observation-extraction/test-plan.md`
- Risk level: Medium
- Test strategy:
  - Unit: LLM output validation、clamp、disposition allowlist、fallback metadata。
  - Integration: wake cycle default deterministic と opt-in LLM path。
  - E2E: real provider live test は手順のみ。自動実行しない。
  - Manual QA: OpenRouter / `deepseek/deepseek-v4-pro` 手順と non-default 境界を確認する。
  - Validator / static check: `pytest` と `./scripts/check-docs.sh`。

## Deployment / Rollout

既定値は deterministic のままなので rollback は env var を unset するだけでよい。manual live test は明示的に `AGENT_OBSERVATION_EXTRACTOR=llm`, `AGENT_LLM_PROVIDER=openrouter`, `AGENT_LLM_MODEL=deepseek/deepseek-v4-pro` と provider key を export した一回限りの isolated project root で実施する。
