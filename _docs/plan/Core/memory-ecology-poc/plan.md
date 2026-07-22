---
title: Memory Ecology Agent PoC Implementation Plan
status: active
draft_status: n/a
created_at: 2026-05-29
updated_at: 2026-06-02
references:
  - "_docs/intent/Core/memory-ecology-poc/decision.md"
  - "_docs/qa/Core/memory-ecology-poc/test-plan.md"
  - "_evals/prompts/memory-ecology-agent-poc.md"
  - "_evals/prompts/memory-ecology-agent-reference.md"
related_issues: []
related_prs: []
---

## Overview

`_evals/prompts/memory-ecology-agent-poc.md` に基づき、Memory Ecology Agent PoC の最初の縦切りを Python で実装する。目的は賢いチャットボットではなく、入力環境から何を探索し、何を観測し、何を concern として保持し、どの action / outcome に変え、attention policy と応答がどう変わったかを SQLite に trace できる状態にすること。

## Scope

- Python 3.12 / SQLite / SQLAlchemy 2.x / Pydantic v2 / pytest のプロジェクト構成を追加する。
- source prompt の最低テーブル群を SQLAlchemy model として実装し、JSON helper を用意する。
- CLI として `init`, `seed`, `chat`, `wake`, `review`, `reflect`, `eval run`, `eval compare`, `inspect` を実装する。
- `world/` は read-only input ecology、`agent_workspace/` は writeable workspace として扱う。
- local file adapter は path traversal、symlink traversal、secret らしきファイル、binary file、budget 超過を防ぐ。
- Web search は実装差し替え可能な interface / stub のみ作る。
- MockLLMClient を標準にし、外部 API キーなしでテストと CLI smoke を動かせるようにする。
- wake cycle で probe -> raw_event -> observation -> concern -> action/outcome -> attention_policy_event -> wake_request の縦切りを保存する。
- chat cycle で concern / memory / attention_policy を context に使い、response_trace を保存する。
- replay eval で eval_prompt への応答を保存し、同一 prompt の過去 run を比較表示する。
- deterministic closed loop 強化として、digest decision、concern lifecycle transition、attention_policy-driven probe selection、outcome-driven policy update、state-sensitive fake LLM replay を外部 provider なしで検証可能にする。
- README と reference にセットアップ、実行例、設計境界、trace の読み方、既知の制限を書く。

## Non-Goals

- Discord bot、本番 scheduler、dashboard UI、外部 Web 検索 API、任意コマンド実行は実装しない。
- core profile の自動更新は行わない。変更候補は `core_change_proposals` に留める。
- LLM の賢さや自然な人格表現は優先しない。traceability を優先する。
- Postgres / pgvector / embedding search は初期 PoC では扱わない。

## Requirements

- **Functional**: `python -m app.main init`, `seed`, `wake --reason cron`, `chat`, `eval run`, `eval compare`, `inspect concerns`, `inspect probes`, `inspect attention-policy`, `inspect traces` が動作する。
- **Functional**: seed により core profile、initial attention policy、initial self model、eval prompts、world sample files が作られる。
- **Functional**: wake cycle は probe rationale、observation rationale、concern event reason、attention policy event reason、action/outcome を保存する。
- **Functional**: chat cycle は selected memories / concerns / attention policy と concern mode (`mention` / `influence` / `ignore`) を response_trace に保存する。
- **Functional**: replay eval は response_text と選択状態を replay_runs に保存する。
- **Functional**: digest decision は concern / memory / discard / action の全判断を first-class trace として保存し、discard reason を CLI から inspect できる。
- **Functional**: concern lifecycle は seed / active / dormant / resolved / archived / successor を deterministic helper と review flow で遷移させ、previous/new state と evidence を concern_events に残す。
- **Functional**: probe planning は latest attention_policy の source_preferences と exploration_randomness を使い、source ranking と skipped source reason を probe metadata に残す。
- **Functional**: outcome evidence は bounded attention_policy_events に変換され、outcome id evidence を残す。
- **Functional**: state-sensitive fake LLM は selected concerns / memories / policy に応じて deterministic な response text drift を replay で示す。
- **Non-Functional**: 外部 API キーがなくても MockLLMClient で全テストが通る。
- **Non-Functional**: local file adapter は `world/` 外を読まず、`agent_workspace/` 以外へ書かない設計にする。
- **Non-Functional**: 重要な判断は DB event または trace field に理由を残す。
- **Non-Functional**: core profile は自動更新せず、変化の必要がある場合は proposal に留める。

## Tasks

- Project skeleton: `pyproject.toml`, `app/`, `tests/`, package init、設定。
- DB: SQLAlchemy models、session、schema init、JSON helper、seed。
- Adapters: clock、LLM wrapper、local files、web search stub。
- Cognition: probe planner、observation extractor、digestor、concern manager、memory manager、attention policy updater、action planner、context builder、self model helper。
- Runtime: chat cycle、wake cycle、review cycle、reflection cycle、scheduler helper。
- Eval: replay run / compare、ablation placeholder。
- CLI: argparse based commands と readable inspect。
- Tests: PROMPT の 13 観点と safety boundary を pytest で確認する。
- Docs: README、reference、verification、root prompt の非運用化判断を反映する。
- Closed-loop hardening: `digest_decisions` trace、concern identity/lifecycle helpers、policy-ranked probes、outcome-based policy updates、state-sensitive fake LLM、verification script evidence を追加する。

## QA Plan

- QA document: `_docs/qa/Core/memory-ecology-poc/test-plan.md`
- Risk level: High
- Test strategy:
  - Unit: DB init、JSON helper、local adapter safety、context builder classification、core profile immutability。
  - Integration: seed / wake / chat / replay eval の SQLite 縦切り。
  - Integration: digest decisions、concern lifecycle、outcome-driven policy event、policy-driven probe ranking、state-sensitive replay drift を一時 project root で確認する。
  - E2E: CLI smoke for `init`, `seed`, `wake`, `chat`, `eval run`, `inspect`。
  - Manual QA: inspect output が trace を読めること、README の実行例が現実と一致すること。
  - Validator / static check: `scripts/check-docs.sh` と pytest。
- AC と intent-derived invariant は QA test-plan の Test Matrix に割り当てる。
- High risk 観点として rollback/recovery は DB ファイル再生成、data safety は path / symlink / secret exclusion、security は read/write boundary で確認する。

## Deployment / Rollout

- PoC はローカル CLI として導入する。デプロイや常駐 process は不要。
- 破壊的 migration は行わない。検証時は一時 DB path または test tmpdir を使う。
- 問題が出た場合は生成された `data/agent.db` を使わず、`init` で再生成できる構成にする。恒久削除はユーザー許可なしに行わない。
