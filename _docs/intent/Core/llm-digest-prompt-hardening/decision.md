---
title: LLM Digest Prompt Hardening Decision
status: active
draft_status: n/a
created_at: 2026-06-02
updated_at: 2026-06-02
references:
  - "_docs/plan/Core/llm-digest-prompt-hardening/plan.md"
  - "_docs/qa/Core/llm-digest-prompt-hardening/test-plan.md"
  - "_docs/intent/Core/llm-digest-decision-proposals/decision.md"
  - "_docs/qa/Core/llm-digest-proposal-quality-evaluation/verification.md"
related_issues: []
related_prs: []
---

# LLM Digest Prompt Hardening Decision

## Context

`llm_shadow` digest proposal は final state updater ではなく、deterministic digest decision と比較するための proposal generator として導入された。`Core-Test-13` の offline quality evaluation では、stable project facts や reusable user feedback を LLM が `memory_candidate` として提案し、deterministic の過 concern 傾向を点検できる可能性が見えた。

一方で、follow-up 風の observation に対して LLM が `action_candidate` を提案するリスクも観測された。LLM proposal は downstream state mutation に近い領域を扱うため、prompt / rubric が曖昧なまま評価を増やすと、将来の adoption 判断が危険な前提に乗る。

## Decision

- まず prompt / rubric と deterministic `should_apply` normalization を harden し、active `llm_assisted` adoption は実装しない。
- `concern_candidate` は unresolved tension / open loop / pending decision / recurring uncertainty / obligation / risk requiring later review に限定する。
- Stable project facts、durable user preferences、reusable user feedback、project requirements、policy/rubric information は live unresolved tension がない限り `memory_candidate` を優先する。
- `action_candidate` は extremely rare な weak suggestion とし、LLM proposal からは自動採用しない。
- `should_apply` は advisory field のままにし、high-confidence `memory_candidate` / `discard` を中心に限定する。model output は直接信頼せず、schema validation 後に deterministic code で normalized value を計算し、persisted `should_apply` は normalized value にする。
- confidence calibration と risk flags を prompt 内で明示し、evaluation report が decision distribution、boundary disagreement、risk flag distribution、selected qualitative examples を出せるようにする。
- final digest decisions、concerns、memories、attention_policy、actions、outcomes、core_profile、self_model、Discord mode、Web search、raw response persistence は変更しない。

## Alternatives

- **すぐに `llm_assisted` adoption rule を実装する**: quality evaluation が prompt hardening を先に推奨しており、`action_candidate` リスクが残るため不採用。
- **評価だけを増やして prompt は変えない**: 境界が曖昧なまま proposal を増やしても、agreement rate 以上の判断材料が増えにくいため不採用。
- **deterministic digest logic を修正する**: 今回の主目的は LLM shadow proposal の評価性と安全性を高めることなので範囲外。

## Rationale

Prompt hardening は、runtime state mutation を変えずに proposal quality の観測可能性を上げられる。特に memory-vs-concern と action adoption の境界を先に固定すると、今後の live provider evaluation で agreement rate だけに引きずられず、どの disagreement が有益でどれが危険かを読みやすくなる。

## Consequences / Impact

- 新しい prompt version の proposal rows は、旧 prompt と比較して model `should_apply=true` が保守的になり、risk flags が増える可能性がある。さらに persisted `should_apply` は deterministic normalization 後の値になる。
- Agreement rate は上がらない可能性がある。今回の成功条件は agreement rate ではなく boundary behavior の改善である。
- Offline fake evaluation は prompt text そのものを読んで推論する実 model ではないため、live v4pro quality は別途 SKIPPED / verified を明確に扱う必要がある。

## Quality Implications

- Prompt text tests が brittleness を生まないよう、重要境界の存在確認に限定する。
- Evaluation metrics は proposal adoption ではなく、shadow comparison と safety boundary inspection のために使う。
- `should_apply` は advisory metadata であり、今回の runtime path では final decision を変えない。

## Intent-derived Invariants

- INV-001: Prompt は `action_candidate` from the LLM must never be adopted automatically と同等の自動採用禁止を含む。
- INV-002: Prompt は LLM proposal が downstream state を mutate しないことを明示する。
- INV-003: Prompt は stable fact / user feedback / project requirement と unresolved tension を区別する。
- INV-004: `should_apply=true` は action / boundary / unknown / low-confidence cases で deterministic code により禁止される。
- INV-005: Evaluation report は memory-vs-concern、discard-vs-memory、action count、should_apply count、confidence、risk flags、qualitative examples を確認できる。
- INV-006: Runtime final digest decision は deterministic のままで、CI は mock/offline のまま通る。

## Rollback / Follow-ups

Rollback は prompt file、prompt version metadata、normalization persistence を前版へ戻す。Follow-up は live v4pro `llm_shadow` metrics をさらに集め、active adoption ではなく assisted-mode design の条件を別途判断すること。
