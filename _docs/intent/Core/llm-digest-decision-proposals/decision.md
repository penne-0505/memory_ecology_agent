---
title: LLM Digest Decision Proposals Decision
status: active
draft_status: n/a
created_at: 2026-06-02
updated_at: 2026-06-02
references:
  - "_docs/plan/Core/llm-digest-decision-proposals/plan.md"
  - "_docs/qa/Core/llm-digest-decision-proposals/test-plan.md"
  - "_docs/intent/Core/llm-observation-extraction/decision.md"
  - "_docs/intent/Core/llm-provider-integrations/decision.md"
related_issues: []
related_prs: []
---

## Context

LLM-backed observation extraction は、LLM を proposal generator に限定し、後段の digest / concern / memory / attention policy は deterministic pipeline に残す設計で導入された。次の cognition step では、observation が digest される直前に LLM proposal を生成し、deterministic final decision と比較できるようにする必要がある。

この段階は concern / memory creation に近いため、observation extraction より安全境界が厳しい。LLM proposal が final state updater になると、trace-first PoC の検証可能性と CI の offline 性が崩れる。

## Decision

- `AGENT_DIGEST_DECIDER=deterministic|llm_shadow|llm_assisted` を導入し、既定は `deterministic` とする。
- `llm_shadow` は deterministic final decision を維持したまま、LLM proposal と comparison metadata を保存する。
- proposal は `digest_decision_proposals` に保存し、raw provider response は保存しない。
- final `digest_decisions` は既存テーブルを維持し、metadata に `digest_decider`、`proposal_id`、`proposal_agreement`、`arbitration_reason`、`fallback` を残す。
- `llm_assisted` は認識可能な mode として残すが、今回の実装では shadow と同じ final deterministic behavior に制限する。
- invalid JSON、schema-invalid output、provider error、unsafe text は rejected proposal と deterministic fallback になる。

## Alternatives

- **digest_decisions に proposal columns を追加する**: 最小に見えるが、rejected proposal や provider error を final decision と同じ row に押し込むため inspection が曖昧になる。
- **proposal と arbitration の二つの新テーブルを作る**: 正規化は進むが PoC としては過剰で、既存 CLI inspection が重くなる。
- **llm_assisted で proposal 採用まで実装する**: 次の品質評価なしに LLM proposal が final state update に影響するため、今回の主目的から外す。
- **raw response を保存する**: debugging はしやすいが、secret / 長文 / 外部入力漏洩リスクが高いため不採用。

## Rationale

別テーブル proposal と final trace metadata の組み合わせは、既存 digest pipeline を壊さずに比較可能性を追加できる。LLM output を proposal として保存することで quality evaluation の材料は残る一方、final state mutation は deterministic branch のままなので fallback と rollback が単純になる。

## Consequences / Impact

- DB schema に `digest_decision_proposals` が増える。
- `llm_shadow` mode は observation ごとに provider call を行うため latency と provider failure が増えるが、fallback は deterministic で継続する。
- `llm_assisted` は明示されても今回の final decision は deterministic なので、名称と active behavior の差を docs / metadata で明示する必要がある。
- proposal reason / evidence は短く保存されるが、secret-like pattern を含む場合は redacted / rejected になる。

## Quality Implications

- default deterministic behavior が壊れると CI と PoC の reproducibility が落ちる。
- proposal failure が wake pipeline を止めると provider instability が core loop の障害になる。
- raw response や secret-like text が残ると safety boundary が破れる。
- agreement / disagreement が trace されないと LLM proposal quality の評価ができない。

## Intent-derived Invariants

- INV-001: 既定設定では digest proposal provider call と proposal persistence は発生しない。
- INV-002: `llm_shadow` では final digest decision が deterministic decision と一致する。
- INV-003: LLM proposal は concern、memory、attention policy、actions/outcomes、wake requests、self model、core profile を直接作成・更新しない。
- INV-004: invalid JSON、schema-invalid output、provider error、unsafe output は raw response persistence なしで rejected / fallback trace になる。
- INV-005: proposal/final agreement、disagreement、fallback、provider/model、reason は inspection 可能である。
- INV-006: real provider usage は manual opt-in であり、CI / default path / Discord mode / Web search を有効化しない。

## Rollback / Follow-ups

Rollback は `AGENT_DIGEST_DECIDER` を unset するか `deterministic` に戻す。follow-up は sample world 上で proposal quality を評価し、十分な evidence が揃ってから conservative `llm_assisted` adoption rule を実装すること。
