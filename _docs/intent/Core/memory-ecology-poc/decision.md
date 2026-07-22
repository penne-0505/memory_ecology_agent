---
title: Memory Ecology Agent PoC Design Intent
status: active
draft_status: n/a
created_at: 2026-05-29
updated_at: 2026-06-02
references:
  - "_docs/plan/Core/memory-ecology-poc/plan.md"
  - "_docs/qa/Core/memory-ecology-poc/test-plan.md"
  - "_evals/prompts/memory-ecology-agent-poc.md"
  - "_evals/prompts/memory-ecology-agent-reference.md"
related_issues: []
related_prs: []
---

## Context

source prompt は「長期記憶つきチャット」ではなく、入力 ecology から probe / observation / concern / action / outcome / attention policy / response trace がどう変化するかを観測する PoC を要求している。初期実装では、賢い推論よりも、なぜ見に行ったか、何を拾ったか、なぜ保存/廃棄したか、どの concern と policy に効いたかを後から追えることが重要である。

## Decision

- SQLite と SQLAlchemy model を中心に、重要な判断を current state table と event / trace table の両方へ保存する。
- LLM provider は `LLMClient` interface に閉じ込め、初期は `MockLLMClient` を既定にする。
- local file adapter は `world/` 以下だけを read-only にし、symlink traversal、path traversal、secret らしきファイル、binary file を拒否またはスキップする。
- 書き込み先は `agent_workspace/` と SQLite DB に限定する。
- Web search は source boundary と budget を持つ interface / stub として実装し、実 API 接続は後続差し替えにする。
- core profile は seed で作成し、自動更新しない。変更可能性は `core_change_proposals` に留める。
- context builder は active concern を全投入せず、`mention` / `influence` / `ignore` に分類して応答 trace に残す。
- replay eval は現在状態からの応答を保存し、同一 prompt の過去 run と比較できる CLI を提供する。
- digest decision は `memories` や `concerns` になったものだけでなく、discard / action candidate も first-class trace として保存する。
- concern identity は embedding ではなく deterministic key / canonical object / token overlap で行い、同じ unresolved tension を reinforce しつつ無関係な tension を分離する。
- concern lifecycle は seed / active / dormant / resolved / archived / successor の状態変化を helper に閉じ込め、review/runtime が自然に呼べる deterministic heuristic にする。
- attention_policy は after-the-fact record ではなく future probe planning の source ranking に効く current state として扱う。
- outcomes と user feedback は小さく bounded な policy updates へ変換し、evidence_outcome_ids を必ず trace に残す。
- replay response text drift は実 provider ではなく state-sensitive fake LLM provider で deterministic に検証する。

## Alternatives

- **単純な JSON ファイル保存**: 実装は軽いが、event / trace / inspect の関係を追いづらくなるため不採用。
- **実 LLM API を前提にする**: 応答品質は上がるが、外部キーなしで検証できず、PoC の traceability より provider 依存が強くなるため不採用。
- **Web 検索を先に実装する**: 入力 ecology は広がるが、初期 PoC の安全境界と検証範囲が大きくなるため stub に留める。
- **UI / dashboard を作る**: trace 可視性は高まるが、初期ゴールの CLI 縦切りを遅らせるため不採用。
- **real embedding / semantic search で concern identity を解く**: 長期的には有用だが、今回の閉ループ検証では provider 依存と非決定性が増えるため不採用。
- **discard を observation field だけで代用する**: 何をなぜ無視したかが後から query できないため不採用。

## Rationale

event sourcing 的に全てを厳密化しすぎると初期実装が重くなる一方、current state だけでは「なぜそうなったか」が消える。そこで、current state table と event / trace table を併用し、計算式や採用/棄却理由を JSON と reason field に残す。MockLLMClient を既定にすることで、LLM の賢さに依存せずに concern lifecycle と attention policy update をテストできる。

## Consequences / Impact

- DB schema は広いが、初期 PoC の inspect と replay が安定する。
- heuristic 実装は粗いが、reason / rationale / delta を保存することで後続改善の比較対象になる。
- High risk の主対象は local file boundary と secret leakage であり、adapter と tests で重点的に確認する。
- source prompt と source reference は実装後に root active guidance として残すべきではないため、historical / non-operational な場所へ移す。

## Quality Implications

- schema と CLI が通るだけでは不十分で、wake / chat / replay の trace が意味を持って保存される必要がある。
- local adapter は安全境界を破らないことを自動テストで確認する必要がある。
- core profile が自動更新されないことは、テストで明示的に守る。
- context builder は concern を全投入せず、`mention` より `influence` を優先できる必要がある。
- 実行していない検証は verification に書かない。
- digest decision、probe source selection、policy update、replay drift は自然 runtime で観測できる必要があり、manual fixture だけで成功扱いしない。

## Intent-derived Invariants

- INV-001: `world/` 外のファイル、path traversal、symlink traversal は raw_event 化されない。
- INV-002: `.env`, key, credential, secret らしきファイル名と binary file は raw_event 化されない。
- INV-003: LLM JSON 出力は Pydantic で検証し、検証失敗時は state update を進めない。
- INV-004: concern current state の変更時は `concern_events` に reason と delta が残る。
- INV-005: attention policy の変更時は `attention_policy_events` に reason、target_field、evidence が残る。
- INV-006: core profile は seed 後に自動更新されず、変更候補は `core_change_proposals` に留まる。
- INV-007: chat response は selected concern / memory / attention policy と concern mode を `response_traces` に残す。
- INV-008: replay eval は同じ prompt への応答変容を比較できるよう `replay_runs` に選択状態を保存する。
- INV-009: digest decisions は concern / memory / discard / action/no-op の判断理由と source observation/raw_event を保存する。
- INV-010: concern lifecycle event は previous_state / new_state / evidence ids を delta に含める。
- INV-011: probe metadata は policy-driven source ranking と skipped source reason を構造化して残す。
- INV-012: outcome-driven attention policy event は evidence_outcome_ids_json を空にしない。
- INV-013: state-sensitive replay は response text drift と selected-state drift を示しても core_profile を変えない。

## Rollback / Follow-ups

- ローカル PoC の rollback は、生成 DB を使わず `init` で再作成することを基本にする。ユーザー許可なしに `rm` は使わない。
- 後続候補: 実 LLM provider、Web search 実装、dashboard、embedding search、scheduler daemon、Discord bot。
