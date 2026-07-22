---
title: "QA Test Plan: Memory Ecology Agent PoC"
status: active
draft_status: n/a
qa_status: planned
risk: High
created_at: 2026-05-29
updated_at: 2026-06-02
references:
  - "_docs/intent/Core/memory-ecology-poc/decision.md"
  - "_docs/plan/Core/memory-ecology-poc/plan.md"
  - "_evals/prompts/memory-ecology-agent-poc.md"
  - "_evals/prompts/memory-ecology-agent-reference.md"
related_issues: []
related_prs: []
---

# QA Test Plan: `Memory Ecology Agent PoC`

## Source of Intent

- TODO: `Core-Feat-5`
- Plan: `_docs/plan/Core/memory-ecology-poc/plan.md`
- Intent: `_docs/intent/Core/memory-ecology-poc/decision.md`
- Prompt source: `_evals/prompts/memory-ecology-agent-poc.md`
- Reference source: `_evals/prompts/memory-ecology-agent-reference.md`

## Quality Goal

Memory Ecology Agent PoC が外部 API なしで動作し、wake / chat / replay eval の各縦切りで「何を見に行ったか」「何を拾ったか」「何を捨てたか」「どの concern / attention policy / response trace に効いたか」を DB と CLI から検証できることを確認する。High risk の主対象は local file boundary と secret leakage、および trace されない state mutation であり、`world/` 外読み取りと core profile 自動更新を防ぐことを必須条件にする。

## Acceptance Criteria

- AC-001: `python -m app.main init` と `python -m app.main seed` が SQLite schema と初期 core profile / attention policy / self model / eval prompts / world sample files を作成する。
- AC-002: `python -m app.main wake --reason cron` が `world/` 以下だけを読み、probe、raw_event、observation、concern、concern_event、action、outcome、attention_policy_event、wake_request を trace 可能な形で保存する。
- AC-003: `python -m app.main chat "..."` が concern / memory / attention_policy を使って応答し、response_trace と respond action を保存する。
- AC-004: `python -m app.main eval run` と `python -m app.main eval compare --prompt-id 1` が replay_run を保存・比較表示できる。
- AC-005: local file adapter が path traversal、symlink traversal、`world/` 外、binary、secret / credential らしきファイルを拒否またはスキップする。
- AC-006: pytest が外部 API キーなしの MockLLMClient で source prompt の最低 13 テスト観点をカバーして通る。
- AC-007: README にセットアップ、CLI 実行例、設計境界、trace の読み方、既知の制限がプロジェクト固有の内容として書かれている。
- AC-008: digest decision が first-class trace として永続化され、concern_candidate / memory_candidate / discard / action_candidate の理由と score snapshot を inspect できる。
- AC-009: concern lifecycle が seed / active / dormant / resolved / archived / successor path を deterministic helper と review/runtime flow で遷移できる。
- AC-010: deterministic concern identity が同一 tension を reinforce し、無関係な observation を別 concern として分離する。
- AC-011: attention_policy が future probe planning の source ranking に効き、selected source と skipped source reason が probe metadata に残る。
- AC-012: outcome evidence と Discord feedback が bounded attention_policy_event を生成し、outcome id evidence を残す。
- AC-013: state-sensitive fake LLM provider が selected state に応じた deterministic replay response text drift を示す。
- AC-014: replay verification が selected-state drift、response-text drift、core_profile stability を区別して報告する。
- AC-015: GitHub Actions の pytest CI が Python 3.12 / uv / mock provider / Discord disabled で、secrets や live external services なしに `uv run pytest` と deterministic PoC verification script を実行する。

## Intent-derived Invariants

- INV-001: `world/` 外のファイル、path traversal、symlink traversal は raw_event 化されない。
- INV-002: `.env`, key, credential, secret らしきファイル名と binary file は raw_event 化されない。
- INV-003: LLM JSON 出力は Pydantic で検証し、検証失敗時は state update を進めない。
- INV-004: concern current state の変更時は `concern_events` に reason と delta が残る。
- INV-005: attention policy の変更時は `attention_policy_events` に reason、target_field、evidence が残る。
- INV-006: core profile は seed 後に自動更新されず、変更候補は `core_change_proposals` に留まる。
- INV-007: chat response は selected concern / memory / attention policy と concern mode を `response_traces` に残す。
- INV-008: replay eval は同じ prompt への応答変容を比較できるよう `replay_runs` に選択状態を保存する。
- INV-009: digest decisions は source observation/raw_event、decision、reason、confidence、score snapshot、related concern ids を保存する。
- INV-010: concern lifecycle event は previous_state / new_state と evidence observation/action/outcome ids を delta または dedicated fields に残す。
- INV-011: probe metadata は policy-driven source ranking と skipped source reason を構造化して残す。
- INV-012: outcome-driven attention policy event は evidence_outcome_ids_json を空にしない。
- INV-013: state-sensitive replay は response text を変えても core_profile を自動更新しない。

## Risk Assessment

- Risk level: High
- Risk rationale: local file adapter が境界を誤ると `world/` 外や secret らしきファイルを raw_event 化する可能性がある。DB schema と CLI も広範囲に追加される。
- Regression risk: テンプレート由来 docs / validators と新規 Python package が共存するため、ドキュメント validator と pytest の両方で確認する。
- Data safety risk: PoC DB と sample files の生成は局所的だが、ユーザーの実ファイルを読まないことが重要。
- Security / privacy risk: path traversal、symlink traversal、secret file name、binary file のスキップが必須。
- UX risk: inspect 出力が読みにくいと traceability の目的を満たせない。
- Agent misbehavior risk: root-level one-off prompt を active guidance として残し続ける、または実行していない検証を verification に書くリスクがある。

## Test Strategy

- Unit: SQLAlchemy init、JSON helper、local file safety、LLM wrapper validation、context builder classification、core profile immutability。
- Integration: seed / wake / review / reflect / chat / replay eval を temporary DB / world で実行し、必要な table rows と trace field を確認する。
- Integration: digest decisions、concern lifecycle、identity matching、policy-driven probe ranking、outcome-driven policy event、state-sensitive replay drift を deterministic に確認する。
- E2E: CLI smoke として `python -m app.main init`, `seed`, `wake --reason cron`, `chat`, `eval run`, `eval compare`, `inspect` を実行する。
- Manual QA: inspect output と README の実行例を見比べ、trace が人間に読めることを確認する。
- Validator / static check: `./scripts/check-docs.sh`、`python -m pytest`。
- Diff review: root prompt handling、README、reference、TODO、verification が docs operations と矛盾していないことを確認する。

## Test Matrix

| ID | Source | Requirement / Invariant | Test Type | Command / File | Expected Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| AC-001 | TODO | init / seed が schema と初期データを作る。 | integration | `tests/test_db_seed.py` / CLI smoke | core_profiles, attention_policies, self_model_snapshots, eval_prompts, world samples が存在する。 | planned |
| AC-002 | TODO | wake が probe から policy event まで保存する。 | integration | `tests/test_wake_cycle.py` | input_probes, raw_events, observations, concerns, concern_events, actions, outcomes, attention_policy_events, wake_requests が作られる。 | planned |
| AC-003 | TODO | chat が response_trace と respond action を保存する。 | integration | `tests/test_chat_replay_context.py` | response_traces と actions(action_type=respond) が保存される。 | planned |
| AC-004 | TODO | replay eval が保存・比較表示できる。 | integration | `tests/test_chat_replay_context.py` / CLI smoke | replay_runs が保存され、compare 出力が run 一覧を含む。 | planned |
| AC-005 | TODO | local adapter が危険な path / file を読まない。 | unit | `tests/test_local_files.py` | traversal / symlink / secret / binary が raw_event input にならない。 | planned |
| AC-006 | TODO | MockLLMClient で source prompt の最低 13 観点をカバーして pytest が通る。 | automated | `uv run --python /home/penne/.local/bin/python3.12 pytest` | 全テスト PASS。 | planned |
| AC-007 | TODO | README が project-specific setup / usage / boundaries / limitations を説明する。 | diff review | `README.md` | テンプレート汎用文ではなく PoC の実行手順と境界が書かれている。 | planned |
| AC-008 | TODO | digest decision が first-class trace として永続化される。 | integration | `tests/test_wake_cycle.py` / `inspect digest-decisions` | concern / memory / discard / action candidate と reason / score snapshot が保存される。 | planned |
| AC-009 | TODO | concern lifecycle が自然 transition と successor path を持つ。 | integration | `tests/test_concern_lifecycle.py` | seed -> active -> dormant -> active -> resolved -> archived と successor events が作られる。 | planned |
| AC-010 | TODO | deterministic concern identity が reinforce と separation を分ける。 | unit | `tests/test_concern_lifecycle.py` | 同一 tension は同じ concern、無関係 tension は別 concern になる。 | planned |
| AC-011 | TODO | attention_policy が future probe planning に効く。 | unit/integration | `tests/test_policy_probe_replay.py` | policy 設定で selected probe source または ranking が変わり、metadata に理由が残る。 | planned |
| AC-012 | TODO | outcomes と Discord feedback が bounded policy event を作る。 | integration | `tests/test_policy_probe_replay.py` / `tests/test_discord_integration.py` | attention_policy_event に evidence_outcome_ids_json が入る。 | planned |
| AC-013 | TODO | state-sensitive fake LLM が deterministic response drift を示す。 | integration | `tests/test_policy_probe_replay.py` | before/after replay の response_text が selected state に応じて変わる。 | planned |
| AC-014 | TODO | replay verification が state drift / text drift / core stability を区別する。 | automated/manual | `_evals/scripts/verify_memory_ecology_poc.py` | evidence JSON に drift と core unchanged が別項目で出る。 | planned |
| AC-015 | TODO | pytest CI が offline/mock 設定で tests と deterministic verification を再現する。 | CI/diff review | `.github/workflows/pytest-ci.yml` / `uv run pytest` / `_evals/scripts/verify_memory_ecology_poc.py` | workflow が Python 3.12、`uv sync --locked`、`uv run pytest`、runner temp への verification output、mock/offline env を含む。 | planned |
| INV-001 | intent | `world/` 外 / traversal / symlink は raw_event 化されない。 | unit | `tests/test_local_files.py` | 該当 path が拒否またはスキップされる。 | planned |
| INV-002 | intent | secret らしきファイル名と binary file は raw_event 化されない。 | unit | `tests/test_local_files.py` | `.env`, key, credential, secret, binary が除外される。 | planned |
| INV-003 | intent | LLM JSON 出力検証失敗時に state update を進めない。 | unit | `tests/test_llm.py` | Pydantic validation error が発生し、DB 書き込み前に止まる。 | planned |
| INV-004 | intent | concern 更新には concern_event が残る。 | integration | `tests/test_wake_cycle.py` | concern_events に reason / delta_json がある。 | planned |
| INV-005 | intent | attention policy 更新には policy event が残る。 | integration | `tests/test_wake_cycle.py` | attention_policy_events に target_field / reason / evidence がある。 | planned |
| INV-006 | intent | core profile は自動更新されない。 | unit | `tests/test_chat_replay_context.py` | wake / reflect 後も core_profiles row は更新されない。 | planned |
| INV-007 | intent | chat response は selected state と concern mode を trace に残す。 | integration | `tests/test_chat_replay_context.py` | response_traces に selected_* と concern_modes_json がある。 | planned |
| INV-008 | intent | replay_runs が応答変容比較に必要な選択状態を保存する。 | integration | `tests/test_chat_replay_context.py` | replay_runs に selected_concerns / selected_memories / selected_attention_policy がある。 | planned |
| INV-009 | intent | digest decisions は source と score snapshot を保存する。 | integration | `tests/test_wake_cycle.py` | digest_decisions に source_observation_id / source_raw_event_id / reason / snapshot がある。 | planned |
| INV-010 | intent | lifecycle event は previous/new state と evidence ids を残す。 | integration | `tests/test_concern_lifecycle.py` | concern_events.delta_json に state transition と evidence ids がある。 | planned |
| INV-011 | intent | probe metadata は policy ranking と skipped source reason を残す。 | integration | `tests/test_policy_probe_replay.py` | input_probes.budget_used_json または metadata に ranking/skips がある。 | planned |
| INV-012 | intent | outcome-driven policy event は outcome id evidence を残す。 | integration | `tests/test_policy_probe_replay.py` / `tests/test_discord_integration.py` | evidence_outcome_ids_json が空でない。 | planned |
| INV-013 | intent | state-sensitive replay は core_profile を更新しない。 | integration | `tests/test_policy_probe_replay.py` | response text が変わっても core profile content は同一。 | planned |

## Manual QA Checklist

- [ ] `inspect concerns` の出力から concern title、state、activation、opened reason が読める。
- [ ] `inspect attention-policy` の出力から latest policy と update event の理由が読める。
- [ ] `inspect traces` の出力から chat response の selected concern / memory / policy が読める。
- [ ] `inspect digest-decisions` の出力から discard reason と score snapshot が読める。
- [ ] `inspect outcomes` と `inspect attention-policy` から outcome evidence の policy event が追える。
- [ ] README のコマンドを順に実行して PoC の流れを再現できる。

## Regression Checklist

- [ ] `scripts/check-docs.sh` が TODO / QA / front-matter / links を通す。
- [ ] `python -m pytest` が外部 API キーなしで通る。
- [ ] GitHub Actions pytest workflow が secrets、live Discord、実 LLM provider、実 Web search を要求しない。
- [ ] `state_sensitive_mock` は実 provider API を呼ばない。
- [ ] Web search source が選ばれても stub と skip reason の範囲に留まり、実ネットワーク検索を行わない。
- [ ] 実行していない検証を verification に書いていない。
- [ ] root-level one-off prompt の扱いが documentation operations と矛盾していない。

## High-risk Checklist

- [ ] Rollback path is documented: generated SQLite DB can be recreated with `init` and no irreversible repository operation is required.
- [ ] Recovery path is documented: failed cycle records outcomes instead of mutating core profile or reading broader files.
- [ ] Data safety has been checked: local adapter reads only `world/` and writes only through DB / `agent_workspace/`.
- [ ] Security / privacy implications have been checked: path traversal, symlink traversal, binary files, and secret-like file names are tested.
- [ ] Failure mode is understood: LLM validation failure does not apply state updates.

## Out of Scope

- Discord bot、本番 scheduler、外部 Web 検索 API、dashboard UI。
- Postgres / pgvector / embedding search。
- core profile の自動更新。

## Open Questions

- なし。実 LLM provider や Web search の具体 API は後続タスクで決める。
