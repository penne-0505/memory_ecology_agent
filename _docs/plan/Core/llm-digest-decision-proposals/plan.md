---
title: LLM Digest Decision Proposals Plan
status: active
draft_status: n/a
created_at: 2026-06-02
updated_at: 2026-06-02
references:
  - "_docs/intent/Core/llm-digest-decision-proposals/decision.md"
  - "_docs/qa/Core/llm-digest-decision-proposals/test-plan.md"
  - "_docs/intent/Core/llm-observation-extraction/decision.md"
  - "_docs/intent/Core/llm-provider-integrations/decision.md"
related_issues: []
related_prs: []
---

## Overview

LLM-backed digest decision proposals を feature flag の背後に追加する。既定の digest decision は deterministic のままとし、`llm_shadow` mode でのみ LLM に observation ごとの proposal を生成させる。proposal は永続化して比較に使うが、concern、memory、attention policy、actions/outcomes、wake requests、self model、core profile を直接変更しない。

## Scope

- `AGENT_DIGEST_DECIDER=deterministic|llm_shadow|llm_assisted` を追加し、既定は `deterministic` にする。
- `llm_shadow` で deterministic digest decision を先に作り、LLM proposal を別テーブルへ保存し、agreement / disagreement / fallback を final digest trace の metadata に残す。
- `llm_assisted` は設定値として認識するが、今回の active behavior は conservative に deterministic final decision を維持する。
- LLM output は strict schema、allowed enum、score clamp、text length limit、known concern ID filtering、secret-like text redaction / rejection を通す。
- provider error、invalid JSON、schema-invalid output は wake / ingest pipeline を止めず、rejected proposal trace と deterministic final decision に fallback metadata を残す。
- `inspect digest-proposals` と `inspect digest-decisions` で deterministic decision、LLM proposal、final decision、arbitration reason を確認できるようにする。

## Non-Goals

- deterministic digest pipeline を既定で置き換えない。
- LLM proposal から concern / memory / action / attention policy / self model / core profile を直接 mutate しない。
- real provider credential を CI で要求しない。
- real Web search や Discord operational mode を変更しない。
- raw provider response を永続化しない。
- `llm_assisted` で LLM proposal を final decision に採用する active implementation は今回の必須範囲に含めない。

## Requirements

- **Functional**: deterministic mode では provider call と proposal persistence が発生しない。
- **Functional**: llm_shadow mode では proposal record と final digest decision metadata から比較結果を追跡できる。
- **Functional**: malformed / unsafe provider output は rejected proposal と fallback metadata になり、wake pipeline は継続する。
- **Functional**: discard proposal も trace される。
- **Non-Functional**: raw response、API key、Authorization header、secret-like text は保存しない。
- **Non-Functional**: tests は fake / mock provider のみで完結する。

## Tasks

- Settings に digest decider mode と proposal confidence threshold を追加する。
- `DigestDecisionProposal` model と JSON-safe persistence helper を追加する。
- prompt file `app/prompts/digest_decision_llm.md` を追加する。
- digest proposal generation / validation / arbitration helper を追加する。
- wake cycle と Discord ingest path を helper 経由に更新する。
- CLI inspect に `digest-proposals` と decider config 表示を追加する。
- offline unit / integration tests と docs / verification を追加する。

## QA Plan

- QA document: `_docs/qa/Core/llm-digest-decision-proposals/test-plan.md`
- Risk level: High
- Test strategy:
  - Unit: proposal schema validation、fallback、secret redaction、unknown concern filtering。
  - Integration: default deterministic、llm_shadow proposal persistence、final deterministic decision、no direct downstream mutation。
  - E2E: temp-root deterministic smoke と fake-provider llm_shadow smoke。
  - Manual QA: OpenRouter / `deepseek/deepseek-v4-pro` は credential が明示された場合のみ optional smoke。
  - Validator / static check: `pytest`、`./scripts/check-docs.sh`、verification script。

## Deployment / Rollout

既定は `AGENT_DIGEST_DECIDER=deterministic` なので rollback は env var を unset するだけでよい。manual live test は isolated temp project root で `AGENT_LLM_PROVIDER=openrouter`、`AGENT_LLM_MODEL=deepseek/deepseek-v4-pro`、`AGENT_DIGEST_DECIDER=llm_shadow` を明示して実施する。
