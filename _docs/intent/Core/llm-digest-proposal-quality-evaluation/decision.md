---
title: LLM Digest Proposal Quality Evaluation Decision
status: active
draft_status: n/a
created_at: 2026-06-02
updated_at: 2026-06-02
references:
  - "_docs/plan/Core/llm-digest-proposal-quality-evaluation/plan.md"
  - "_docs/qa/Core/llm-digest-proposal-quality-evaluation/test-plan.md"
  - "_evals/reports/llm_digest_proposal_quality_2026-06-02.md"
  - "_docs/intent/Core/llm-digest-decision-proposals/decision.md"
related_issues: []
related_prs: []
---

## Context

`llm_shadow` は LLM digest proposal を保存するが、final decision は deterministic のまま維持する。この状態は安全だが、`llm_assisted` を実装するには proposal がどの条件で deterministic decision より良い、または危険かを評価する必要がある。

## Decision

この follow-up では active adoption を実装せず、sample world 上の proposal quality evaluation を先に行う。2026-06-02 の offline mock evaluation では `PROMPT_HARDENING_FIRST` を推奨し、現時点では `llm_assisted` adoption implementation に進まない。

## Alternatives

- **すぐ `llm_assisted` を実装する**: quality evidence が足りず、final state update の安全境界を弱めるため不採用。
- **評価を行わず shadow を固定する**: 安全だが、LLM proposal の価値を判断できないため次段階の材料が残らない。

## Rationale

proposal quality は model、prompt、sample world の内容に依存する。先に比較 evidence を作ることで、adoption rule を実装する場合にも反証可能な条件を置ける。

2026-06-02 の評価では、live OpenRouter / `deepseek/deepseek-v4-pro` run は `AGENT_LLM_PROVIDER=openrouter` と `AGENT_LLM_MODEL` が明示されていなかったため SKIPPED とした。offline fake では schema-valid proposal、agreement / disagreement、discard / memory / concern / action boundary の比較はできたが、real model quality の根拠にはならない。

## Consequences / Impact

- evaluation artifact が増える。
- real provider を使う場合は optional manual run になる。
- `llm_assisted` implementation はこの評価完了後の別タスクになる。
- 次段階は prompt/rubric hardening と live v4pro 再評価であり、active adoption はまだ実装しない。

## Quality Implications

- disagreement examples を見ずに adoption rule を作ると、LLM proposal が deterministic safety boundary を弱める。
- fallback / invalid output を成功扱いすると、provider instability を過小評価する。

## Intent-derived Invariants

- INV-001: Evaluation は final state updater を LLM に変更しない。
- INV-002: Report は agreement だけでなく disagreement と fallback を含む。
- INV-003: Optional real provider run は credential を明示した環境でのみ実施し、CI の必須条件にしない。
- INV-004: LLM proposal から `action_candidate` を単独採用しない。
- INV-005: Digest proposal は `core_profile` / `self_model` / Discord mode / Web search / final digest decision を変更しない。

## Rollback / Follow-ups

Evaluation artifact は runtime behavior を変えない。live v4pro と prompt hardening の結果が十分なら、specific-case-only assisted adoption implementation を別 TODO にする。
