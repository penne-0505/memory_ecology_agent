---
title: LLM Digest Prompt Hardening Plan
status: active
draft_status: n/a
created_at: 2026-06-02
updated_at: 2026-06-02
references:
  - "_docs/intent/Core/llm-digest-prompt-hardening/decision.md"
  - "_docs/qa/Core/llm-digest-prompt-hardening/test-plan.md"
  - "_docs/intent/Core/llm-digest-decision-proposals/decision.md"
  - "_docs/intent/Core/llm-digest-proposal-quality-evaluation/decision.md"
related_issues: []
related_prs: []
---

# LLM Digest Prompt Hardening Plan

## Overview

`Core-Test-13` の live quality evaluation は JSON adherence と `should_apply` conservatism の hardening を必要とした。今回の作業では、`llm_shadow` の digest proposal prompt / rubric を短く厳格にし、stable project facts と unresolved concerns、low-signal discard、manual follow-up action の境界をより明確にする。さらに model の `should_apply` を信頼せず、schema validation 後に deterministic code で正規化する。

この作業は prompt / rubric hardening であり、active `llm_assisted` adoption ではない。final digest decision は deterministic のまま維持する。

## Scope

- `app/prompts/digest_decision_llm.md` の decision definitions、`should_apply`、confidence calibration、risk flag rubric、few-shot examples を短く厳格にする。
- digest proposal persistence で `model_should_apply` と normalized `should_apply` を分け、stored `should_apply` は deterministic normalization 後の値にする。
- prompt version metadata を必要に応じて更新し、評価対象の prompt が識別できるようにする。
- prompt/rubric の重要境界を検証する unit tests を追加する。
- `_evals/scripts/evaluate_llm_digest_proposals.py` の metrics / qualitative examples を、prompt hardening 後の比較に必要な形へ補強する。
- offline mock quality evaluation を再実行して、prompt hardening 後の metrics を残す。
- reference / QA verification を必要最小限更新する。

## Non-Goals

- `llm_assisted` による active adoption を実装しない。
- LLM proposal を final digest decision に採用しない。
- default `AGENT_DIGEST_DECIDER=deterministic` を変更しない。
- Discord operational mode を変更しない。
- real Web search を実装しない。
- LLM proposal から `core_profile`、`self_model`、final digest decisions、concerns、memories、attention_policy、actions、outcomes を直接 mutate しない。
- raw provider response を永続化しない。
- CI で real provider credentials を要求しない。

## Requirements

- **Functional**: prompt は `concern_candidate` を unresolved tension / open loop に限定し、重要なだけの stable fact を concern にしない。
- **Functional**: prompt は stable user feedback、project requirement、durable context を `memory_candidate` として扱う基準を示す。
- **Functional**: prompt は low-signal / repetitive content を `discard` にする基準を示す。
- **Functional**: prompt は `action_candidate` を rare / weak suggestion とし、自動採用禁止を明示する。
- **Functional**: `should_apply=true` は conservative advisory signal とし、boundary risk flags では禁止する。model output は直接信頼せず、code で normalized value を計算する。
- **Functional**: evaluation report は required metrics と selected qualitative examples を出力する。
- **Non-Functional**: runtime final decision、Discord mode、Web search、raw response persistence、CI credentials boundary は変えない。

## Tasks

- TODO / Plan / Intent / QA を作成して scope と non-goals を固定する。
- prompt の decision definitions、`should_apply`、confidence、risk flags、examples、schema section を更新する。
- deterministic `should_apply` normalization と proposal metadata persistence を追加する。
- prompt version を更新する。
- prompt text tests と評価 script metrics tests を追加する。
- evaluation script の memory-vs-concern / discard-vs-memory / selected qualitative examples を補強する。
- reference / QA verification を更新する。
- `pytest`、`./scripts/check-docs.sh`、PoC verification、quality evaluation を実行する。

## QA Plan

- QA document: `_docs/qa/Core/llm-digest-prompt-hardening/test-plan.md`
- Risk level: Medium
- Test strategy:
  - Unit: prompt text が hardening 境界を含むことを検証する。
  - Unit: fake examples で `action_candidate` の `should_apply=false`、stable fact / true concern / repeated noise の expected route を検証する。
  - Unit: model `should_apply=true` が低 confidence / blocked flag で false に正規化され、高 confidence allowed flags のみ true になることを検証する。
  - Script: evaluation metrics が required fields を含むことを検証する。
  - Regression: existing digest / wake / observation / replay / Discord tests を full pytest で確認する。
  - Validator: docs consistency を `./scripts/check-docs.sh` で確認する。
  - E2E-ish: `_evals/scripts/verify_memory_ecology_poc.py`、offline digest proposal quality evaluation、live v4pro shadow evaluation を isolated temp root で実行する。

## Deployment / Rollout

Runtime rollout は不要。prompt version が変わるため、以後の `llm_shadow` proposal rows では new prompt version を使って識別する。proposal table に正規化 metadata columns が追加されるため、既存 SQLite DB では init 時に不足列を追加する。rollback は prompt file、prompt version metadata、normalization persistence を前版へ戻すことで可能。
