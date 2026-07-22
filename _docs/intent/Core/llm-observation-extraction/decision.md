---
title: LLM Observation Extraction Decision
status: active
draft_status: n/a
created_at: 2026-06-02
updated_at: 2026-06-02
references:
  - "_docs/plan/Core/llm-observation-extraction/plan.md"
  - "_docs/qa/Core/llm-observation-extraction/test-plan.md"
  - "_docs/intent/Core/llm-provider-integrations/decision.md"
related_issues: []
related_prs: []
---

## Context

Memory Ecology Agent PoC は traceability を優先し、observation extraction から digest、concern、memory、attention_policy update まで deterministic に動く。provider abstraction と OpenRouter support は既にあるが、normal cognition loop を real provider 前提にすると CI と安全境界が不安定になる。

今回の目的は、LLM を「raw input から observation proposal を作る」段階にだけ導入し、以後の判断は既存 deterministic pipeline に残すことである。

## Decision

- `AGENT_OBSERVATION_EXTRACTOR=deterministic|llm` を追加し、既定は `deterministic` とする。
- `llm` mode でも LLM が返すのは validated `ObservationDraft` proposal のみとする。
- LLM output は Pydantic schema、score clamp、allowed disposition、summary / rationale / evidence quote length limits を通してから採用する。
- fallback は既定で deterministic とし、sanitized metadata を observation rationale と digest metadata に残す。
- strict failure が必要な検証では `AGENT_OBSERVATION_EXTRACTOR_FALLBACK=error` を使う。
- provider は既存 `create_llm_client(settings)` を使い、manual live test の推奨は OpenRouter / `deepseek/deepseek-v4-pro` とする。

## Alternatives

- **LLM を digest decision にも使う**: routing の責任境界が広がり、concern / memory / policy mutation を LLM が実質的に左右するため不採用。
- **LLM extractor を既定にする**: CI とローカル検証が real provider / credential に依存するため不採用。
- **raw provider response を trace に保存する**: debugging 情報は増えるが、外部入力・secret・長文保存リスクが高まるため不採用。
- **schema validation failure で常に crash する**: provider instability が wake cycle 全体を止めるため既定にはしない。strict mode のみ許可する。

## Rationale

observation は raw input と deterministic digest の間にあるため、LLM を入れても影響範囲を proposal validation に閉じ込めやすい。fallback を deterministic に戻すことで、provider error があっても既存 trace loop を維持できる。metadata は sanitized summary に留めることで、traceability と安全性を両立する。

## Consequences / Impact

- `Settings` と wake cycle の extractor selection が増える。
- LLM mode は provider call の latency と non-determinism を持つが、明示 opt-in なので CI と既定実行には影響しない。
- LLM proposal の `possible_disposition` は保存されるが、最終 routing は既存 `digest_observation()` が決める。
- fallback 発生時も raw provider response は保存されないため、debugging は provider type / failure class / sanitized message に限定される。

## Quality Implications

- default offline behavior が壊れると PoC の検証可能性が落ちる。
- LLM output が schema をすり抜けると downstream deterministic pipeline に低品質な observation が入る。
- LLM が direct mutation できる形になると、trace-first contract と core safety boundary が崩れる。
- fallback trace がないと、LLM extraction を試みたかどうかを後から判定できない。

## Intent-derived Invariants

- INV-001: 既定設定では real provider call が発生せず、deterministic extractor が使われる。
- INV-002: LLM extractor は `ObservationDraft` proposal 以外の DB row を直接作成・更新しない。
- INV-003: unsupported disposition、invalid JSON、schema validation error、provider/config error は raw response persistence なしに deterministic fallback または strict error になる。
- INV-004: score fields は 0.0 から 1.0 に収まり、summary / rationale / evidence quote は bounded length になる。
- INV-005: digest trace metadata は extractor mode、provider、fallback status を secret なしで示す。
- INV-006: OpenRouter live usage は manual opt-in であり、CI / default path / Discord / Web search を有効化しない。

## Rollback / Follow-ups

Rollback は `AGENT_OBSERVATION_EXTRACTOR` を unset して deterministic default に戻す。follow-up 候補は provider-specific structured output、multiple observation proposals per raw event、manual quality evaluation、LLM-backed digest decision の別タスク化。
