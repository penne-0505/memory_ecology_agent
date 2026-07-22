---
title: Project Handoff Reference
status: active
draft_status: n/a
created_at: 2026-06-09
updated_at: 2026-06-09
references:
  - "_docs/intent/Core/memory-ecology-poc/decision.md"
  - "_docs/reference/Core/memory-ecology-poc/reference.md"
  - "_docs/qa/Core/memory-ecology-poc/verification.md"
  - "_docs/intent/Core/llm-observation-extraction/decision.md"
  - "_docs/intent/Core/llm-digest-decision-proposals/decision.md"
  - "_docs/intent/Core/llm-assisted-readiness-gate/decision.md"
  - "_docs/qa/Core/llm-assisted-readiness-gate/verification.md"
  - "_docs/intent/Core/discord-integration/decision.md"
  - "_docs/qa/Core/discord-integration/verification.md"
related_issues: []
related_prs: []
---

# Project Handoff Reference

この文書は、次の作業エージェントが過去チャットなしで
Memory Ecology Agent PoC の意図、現在地、守るべき境界を把握するための
handoff である。API 辞書ではなく、intent の圧縮版として読む。

## What This Project Is Trying To Build

Memory Ecology Agent は、長期記憶つきチャットそのものを作るプロジェクトではない。
目標は、人間や環境から流れ込む入力の中で、何を見に行き、何を観測し、
何を未解決の concern として保持し、何を memory / discard / action candidate
へ分け、その結果として次の注意配分や応答がどう変わったかを追跡できる
ローカル実験環境を作ることである。

ここでいう "memory ecology" は、単に情報を保存する仕組みではない。
重要なのは、保存された内容そのものよりも、保存・棄却・再訪・行動・応答の
関係があとから読めることにある。したがって、この PoC の中心価値は
「賢い返答」ではなく「なぜその入力が意味を持ったのか、または持たなかったのか」
を trace として残すことにある。

将来的に作りたいものは、おそらく次のような agent である。

- 周辺環境やユーザー入力をただ蓄積せず、未解決の tension と安定した記憶を分けて扱う。
- concern が seed / active / dormant / resolved / archived / successor として変化する過程を持つ。
- action と outcome が attention policy に戻り、次に何を見るかを変える。
- core profile や self model を安易に自動更新せず、変更候補として提案に留める。
- LLM を使う場合も、いきなり agent の最終判断者にせず、proposal として検証可能に挿入する。

## Current Shape

現状は Python 3.12、SQLite、SQLAlchemy、ローカル CLI を使う trace-first PoC である。
既定では外部 LLM provider、実 Web search、live Discord credentials なしで動く。

標準の実行単位は `wake`、`chat`、`review`、`reflect`、`eval run` である。
特に `wake` は次の縦切りを保存する。

1. `input_probes`: 何を、なぜ見に行くか。
2. `raw_events`: probe から得た入力。
3. `observations`: raw input から抽出した観測。
4. `digest_decisions`: concern / memory / discard / action candidate などの最終分類。
5. `concerns` and `concern_events`: 未解決 tension の current state と履歴。
6. `memories`: 安定した observation digest。
7. `actions` and `outcomes`: agent が何をしたか、または何をしようとしたか。
8. `attention_policies` and `attention_policy_events`: 次に何へ注意を向けるか。
9. `response_traces` and `replay_runs`: 応答がどの state を参照したか。

コード上の入口は `app/main.py` と `app/cli/commands.py`。
runtime の中心は `app/runtime/wake_cycle.py`、DB schema は `app/db/models.py`、
認知処理は `app/cognition/`、外部境界は `app/adapters/` に分かれている。

## The Main Design Bet

このプロジェクトの賭けは、agent の知性を「一回の推論能力」ではなく、
「環境からの入力を時間方向にどう扱ったかの履歴」として捉えることにある。

そのため、現在の実装は意図的に地味である。Mock LLM、deterministic heuristics、
SQLite、CLI inspection を優先している。これは能力不足の妥協ではなく、
後から比較できる基準線を作るための設計判断である。

LLM や Discord や Web search は、agent の能力を増やす方向の入口ではある。
ただし、この PoC では、それらを source of truth にしない。外部入力や provider 出力は、
既存の trace loop に入る前に gate され、proposal / raw event / action / outcome
として扱われる。

## What Has Been Proven

現物確認済みの verification に基づく現在地は以下である。

### Deterministic Closed Loop

`_docs/qa/Core/memory-ecology-poc/verification.md` は PASS である。
外部 provider なしで、digest decision persistence、concern lifecycle、
policy-driven probe planning、outcome-driven policy update、state-sensitive replay drift、
core profile stability が検証されている。

重要な点は、schema と CLI が通るだけでなく、自然 runtime の中で
discard reason、concern transition、policy event、replay drift が観測できることである。

### LLM Observation Extraction

`AGENT_OBSERVATION_EXTRACTOR=llm` は明示 opt-in である。
LLM は raw input から `ObservationDraft` proposal を作るだけで、
digest decision、concern、memory、attention policy、action、outcome、core profile
を直接更新しない。

既定は `deterministic`。provider failure、invalid JSON、schema validation error は
既定で deterministic fallback になり、raw provider response は保存しない。

### LLM Digest Proposal Shadow Mode

`AGENT_DIGEST_DECIDER=llm_shadow` では、LLM が digest proposal を出すが、
final digest decision は deterministic のままである。proposal は
`digest_decision_proposals` に保存され、agreement / disagreement / fallback を
評価できる。

`llm_assisted` は mode 名として認識されるが、現時点では production final decision
を変更する実装としては扱わない。これは混同しやすいので、次のエージェントは
必ず intent と verification を確認すること。

### Assisted Readiness Gate

`_docs/qa/Core/llm-assisted-readiness-gate/verification.md` は PASS である。
ただし PASS の意味は「limited assisted-mode design へ進む準備がある」であり、
active adoption が証明されたという意味ではない。

三つの prompt-hardened qwen structured runs は schema-valid `16/16`、
fallback `0/16`、provider error `0`、malformed JSON `0`、
raw response persisted `0` を満たした。これにより、次の設計課題として
限定的な assisted-mode design を検討できる。

一方で、`action_candidate` の自動採用、Pydantic gate の緩和、
raw response persistence、Discord/Web search/default decider の変更は
引き続き no-go である。

### Discord Adapter

Discord は core runtime の source of truth ではなく adapter である。
`observe_only < ingest_enabled < command_enabled < autonomous_posting_enabled`
という ordered gate を持ち、message ingestion、mutating command、
autonomous posting は mode、channel role、author、allowlist、mute、rate limit
を通る必要がある。

`_docs/qa/Core/discord-integration/verification.md` は PASS。
controller tests、doctor、dry-run、live guild startup、command sync、
user message ingestion、autonomous allow/deny path が検証されている。
ただし `.env` の live state や Discord guild 状態は runtime-sensitive なので、
作業前に再確認する。

## What Is Intentionally Not Solved

この PoC はまだ以下を解いていない。

- 実 Web search。interface / stub はあるが、実ネットワーク検索は初期 PoC の外。
- semantic embedding による concern identity。現状は deterministic key / token overlap。
- production-grade scheduler。`wake_requests` の記録はあるが、実 cron daemon ではない。
- dashboard / UI。CLI inspection と reports が主な観測面。
- migration framework。SQLite schema は PoC として fresh root / `create_all` 前提が強い。
- active `llm_assisted` adoption。readiness gate は design consideration まで。
- rich Discord attachment ingestion。安全側に倒している。

これらは欠落というより、traceability を崩さずに進めるための意図的な保留である。

## Operating Boundaries

次の作業エージェントは、以下を境界条件として扱う。

- `world/` は read-only input ecology。path traversal、symlink traversal、binary、
  secret-like file は raw event 化しない。
- 書き込み先は SQLite DB と `agent_workspace/` が基本。
- API key、Authorization header、raw provider request / response payload は保存しない。
- core profile は seed 後に自動更新しない。変更は `core_change_proposals` に留める。
- LLM output は Pydantic validation を通す。provider-native structured output が成功しても、
  local validation gate を外さない。
- `action_candidate` は LLM から自動採用しない。
- Discord token は環境変数から読むだけで、docs / DB / logs / status に値を出さない。
- live provider / live Discord / current `.env` / current model quality は必ず現物確認する。

## Documentation And QA Culture

この repo は docs-driven である。Size >= M または Risk >= Medium の変更では、
Plan、Intent、QA test-plan、Verification を揃える。

実装判断の一次資料は `_docs/intent/**/decision.md`。
完了証跡は `_docs/qa/**/verification.md`。
運用・API は `_docs/guide/**` と `_docs/reference/**`。

`TODO.md` は未完了タスクの source of truth であり、完了タスクを Done として残さない。
完了履歴は verification / intent / reference / PR / commit 側に残す。

ドキュメント validator は frontmatter に厳しい。
特に QA test-plan に `qa_status: verified` を置かない。
PASS verification の `Residual Risks` は substantive risk を残さず、必要な caveat は
`Deferred / Not Covered` や本文へ分ける。

標準確認コマンド:

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest
./scripts/check-docs.sh
git diff --check
```

live provider や live Discord を使った検証は、credential と explicit env がある場合だけ行う。
credential がない場合は未実行を PASS 扱いせず、SKIPPED / Deferred として記録する。

## Suggested Reading Order For Next Agent

まずこの文書を読み、次に以下を読む。

1. `README.md`: 現在の使い方と CLI overview。
2. `_docs/intent/Core/memory-ecology-poc/decision.md`: 最初の設計意図。
3. `_docs/reference/Core/memory-ecology-poc/reference.md`: 実装構造と CLI / DB の詳細。
4. `_docs/qa/Core/memory-ecology-poc/verification.md`: deterministic closed loop の証拠。
5. `_docs/intent/Core/llm-assisted-readiness-gate/decision.md`: LLM assisted へ進む条件。
6. `_docs/qa/Core/llm-assisted-readiness-gate/verification.md`: qwen structured evidence。
7. `_docs/intent/Core/discord-integration/decision.md`: Discord を adapter として扱う理由。
8. `TODO.md`: 現在の未完了タスク。

コードを見るなら、最初は `app/runtime/wake_cycle.py`、`app/db/models.py`、
`app/cognition/digest_decider.py`、`app/adapters/local_files.py`、
`app/runtime/discord_controller.py` がよい。

## Likely Next Work

現状の自然な次ステップは、limited `llm_assisted` design である。
ただし、これは「LLM に判断を任せる」作業ではない。

設計するなら、少なくとも次を満たす必要がある。

- adoption scope は memory / discard など低リスク領域に限定する。
- deterministic decision と一致する、または保守的に説明できる場合だけ候補にする。
- `action_candidate`、core/self model、Discord mode、Web search、raw response persistence は対象外。
- `should_apply` は provider 出力ではなく local normalization 後の値を使う。
- production final path を変える前に、Plan / Intent / QA test-plan を作り、
  shadow evidence と regression tests を紐づける。

他の候補としては、Web search stub の実 provider 化、scheduler daemon、
dashboard、embedding-based concern identity、Discord attachment policy がある。
ただし、どれも trace-first contract と safety boundary を崩さない設計が先に必要である。

## Memory-Derived Notes

この文書は現行 repo の README、TODO、intent、reference、verification、reports、主要コードを
優先して作成した。過去チャット由来の memory は、主に「CURRENT_STATE_REPORT.md が
存在した時期がある」「docs validator の frontmatter 制約で詰まったことがある」
といった探索の補助として使った。

現 checkout では `CURRENT_STATE_REPORT.md` は存在しないため、この文書では source of truth
として扱っていない。live provider metrics、Discord の live guild 状態、`.env`、dirty tree は
時間で変わるため、作業直前に再確認すること。
