> Historical / non-operational source reference.
> This file is retained only as implementation history. Current project guidance lives in `AGENTS.md`, `TODO.md`, `_docs/`, and the application code.

# Memory Ecology Agent PoC — Reference Document

## 0. この文書の目的

この文書は、「記憶をうまく持つAIエージェント」ではなく、より正確には、**カオスな入力環境から何を拾い、何を捨て、何を未解決 concern として保持し、どの行為に変え、その結果で次の入力選別・応答傾向をどう変えるか**を観測するためのPoC設計を包括的に記述する。

ここで作るものは、本番運用可能な汎用エージェント基盤ではない。目的は、以下の仮説を検証可能な形に落とすことにある。

> 個体らしさは、保存された記憶そのものではなく、入力環境に対して何を探索し、何を観測し、何を未解決として抱え、何を行為し、どの結果を経験として咀嚼するかという閉ループから生じる。
>
> その閉ループにより、核は安定したまま、周辺的な偏りが更新され、探索行動・応答選択・判断の癖が変容しうる。

この文書は、設計のリファレンスである。実装者は、本書を仕様の源泉として扱いつつ、最初のPoCでは過剰な一般化を避けること。

---

## 1. 検証したいこと

### 1.1 主仮説

AIエージェントにおける「個体らしさ」や「人らしさ」は、長期記憶の量ではなく、以下のプロセスから生じる可能性がある。

1. カオスな入力環境にさらされる。
2. その中から、ある偏りを持って入力を探索・選別する。
3. 入力を observation として咀嚼する。
4. 一部を memory にし、一部を concern として保留し、一部を廃棄する。
5. concern や memory に基づき、小さな行為をする。
6. 行為の outcome を再び入力として受け取る。
7. concern、attention policy、self model が少しずつ変わる。
8. その変化が次の探索・応答・判断に影響する。

### 1.2 PoCで見るべきこと

PoCは、次の問いに答えられる必要がある。

- カオスな入力環境から、自律的に probe を作れるか。
- probe 結果から observation を抽出できるか。
- observation から concern が生成・更新されるか。
- concern は seed / active / dormant / resolved / archived の lifecycle を持てるか。
- 行為と outcome によって concern が変化するか。
- outcome によって attention policy が小さく変化するか。
- core profile は安定したままか。
- self model は低頻度でのみ変わるか。
- 同じ eval prompt への応答が、内部状態の変化に応じて変容しうるか。
- その変容がどの concern / memory / attention policy に由来するか trace できるか。

### 1.3 PoCで見ないこと

初期PoCでは、以下を目標にしない。

- 完全自律エージェントの構築。
- 本物の欲望や意識の再現。
- Web上での無制限な自律行動。
- 任意コマンド実行。
- 外部サービスへの自由な書き込み。
- 完全な人格更新モデル。
- 多エージェント社会シミュレーション。
- 本番品質のDiscord bot。

---

## 2. 基本用語

### 2.1 Input ecology

エージェントが入力候補として接する環境全体。

例:

- ユーザーとの会話。
- ローカルの実験用ファイル群。
- Web検索結果。
- 過去ログ。
- memory。
- active / dormant concern。
- 時刻やスケジューラ。
- 過去の action / outcome。

重要なのは、入力が整然としていることではなく、むしろ一定のカオスを含むこと。個体らしさは、カオスな入力をどう選別するかに強く現れる。

### 2.2 Probe

エージェントが「何を見に行こうとしたか」を表す探索行為の単位。

例:

- `world/notes/` からランダムに3ファイル読む。
- active concern に関連する語でWeb検索する。
- 過去memoryから、ユーザーの明示修正に関するものを探す。
- dormant concern を再活性化できる入力がないか探す。

probe は、結果だけでなく、動機・期待・採用/棄却理由を記録する。

### 2.3 Raw event

外界から入ってきた原本に近い記録。

例:

- ユーザー発話。
- ファイル内容の一部。
- Web検索結果。
- scheduler 起動。
- action の結果。

### 2.4 Observation

raw event や probe result から抽出された、意味のある観測。

observation はまだ memory ではない。単なる候補である。ここから concern に流れるもの、memory に流れるもの、廃棄されるものが分かれる。

### 2.5 Concern

ある個体にとって、まだ閉じておらず、将来の注意・判断・記憶更新・行為に影響しうる緊張単位。

concern は topic ではない。以下の三要素を核に持つ。

1. 対象。
2. 緊張。
3. 現時点での終了状態仮説。

たとえば「記憶エージェント」自体は topic だが、「記憶エージェントにおいて、入力選別の偏りがどこまで個体性を生むかを検証したい」は concern になりうる。

### 2.6 Memory

ある程度固まった記憶。fact、preference、lesson、user profile、project context、agent self note などを含む。

memory は concern と混ぜない。concern は未閉鎖の緊張であり、memory は安定化された参照単位である。

### 2.7 Attention policy

この個体が「何を見に行きがちか」「何を重要視しがちか」「どの行為を選びがちか」「応答で何を表に出しがちか」を表す選別傾向。

concern は現在の未解決ループであり、attention policy は入力・観測・行為・応答の偏りである。両者は分ける。

### 2.8 Core profile

ほぼ変わらない核。PoC v0では自動更新しない。更新候補だけ記録する。

### 2.9 Self model

準固定的な自己像。低頻度で更新される。stable traits、current dispositions、known limitations などを含む。

### 2.10 Action

エージェントが行ったこと。

例:

- 応答する。
- ユーザーに質問する。
- ファイルを読む。
- Web検索する。
- 内部メモを書く。
- concern を更新する。
- 次回起動希望を出す。
- 何もしない。

### 2.11 Outcome

action の結果。

例:

- ユーザーに否定された。
- 有用な observation が得られた。
- Web検索がノイズだった。
- concern が解消された。
- 別の concern に吸収された。

---

## 3. 全体アーキテクチャ

### 3.1 閉ループ

PoCの中心は以下のループである。

```text
input ecology
  → input probe
  → raw event / probe result
  → observation
  → concern / memory / discard
  → attention policy update
  → action / response selection
  → outcome
  → concern / attention policy / self model update
  → next probe
```

このループを通して、エージェントはただ記憶するのではなく、経験を選び、咀嚼し、次の選び方を変える。

### 3.2 推奨スタック

PoC初期の推奨構成:

- Python 3.12
- SQLite
- SQLAlchemy 2.x
- Pydantic
- APScheduler または単純なスケジューラ
- LLM provider wrapper
- ローカルファイル adapter
- Web検索 adapter
- CLI chat interface
- 最小限のdashboardまたはログ閲覧CLI

Postgresは後でよい。pgvectorも初期では必須ではない。最初は trace しやすさを優先する。

### 3.3 ディレクトリ構成案

```text
agent-memory-ecology/
  app/
    main.py
    config.py
    db/
      schema.sql
      models.py
      session.py
    runtime/
      chat_cycle.py
      wake_cycle.py
      review_cycle.py
      reflection_cycle.py
      scheduler.py
    adapters/
      local_files.py
      web_search.py
      clock.py
      user_chat.py
    cognition/
      probe_planner.py
      observation_extractor.py
      digestor.py
      concern_manager.py
      memory_manager.py
      attention_policy.py
      action_planner.py
      context_builder.py
      self_model.py
    prompts/
      probe_planner.md
      observation_extractor.md
      concern_update.md
      attention_policy_update.md
      response_selection.md
      reflection.md
      replay_eval.md
    dashboard/
      server.py
      templates/
    eval/
      replay.py
      ablation.py
  world/
    inbox/
    notes/
    articles/
    projects/
    logs/
  agent_workspace/
    notes/
    scratch/
    exports/
  data/
    agent.db
```

`world/` は read-only の入力環境。
`agent_workspace/` はエージェントが書き込んでよい領域。

---

## 4. 権限と安全境界

PoCであっても、自由と無制限を混同しない。

### 4.1 許可すること

- `world/` 以下の read-only 探索。
- `agent_workspace/` 以下への書き込み。
- 制限付きWeb検索。
- 過去ログ・memory・concern の検索。
- wake request の作成。
- 内部メモの作成。
- ユーザーへの質問・応答。

### 4.2 禁止すること

- 任意コマンド実行。
- OS全体やHOME全体の探索。
- credentials、`.env`、SSH key、browser profile などの読み取り。
- `world/` の変更・削除。
- 外部サービスへの自由な書き込み。
- 実際のcron設定の直接書き換え。
- 自動で core profile を書き換えること。

### 4.3 Web検索の制約

- 1 wake cycle あたり最大1〜3 query。
- 検索理由を必ず記録する。
- 採用/棄却理由を必ず記録する。
- Web由来 observation は初期 confidence を低めにする。
- Web検索結果を直接 memory にしない。必ず observation を経由する。

---

## 5. データモデル

### 5.1 raw_events

```text
raw_events
- id
- source_type: user_chat / local_file / web / scheduler / system / action_result
- event_type
- payload_json
- content_text
- content_hash
- happened_at
- created_at
```

外界入力の原本。後から再評価できるように、可能な限り失わず保存する。

### 5.2 input_probes

```text
input_probes
- id
- trigger_type: cron / user_message / concern / random / threshold / replay
- source_type: local_file / web / memory / concern / log
- query_or_path
- rationale
- expected_gain
- related_concern_ids_json
- exploration_mode: concern_driven / random_sample / contradiction_check / scheduled_revisit / stale_area_scan
- budget_json
- budget_used_json
- status: planned / executed / failed / skipped
- result_summary
- created_at
```

probe は個体性観測の重要ログ。何を見たかだけでなく、何を見に行こうとしたかを残す。

### 5.3 observations

```text
observations
- id
- source_event_id
- source_probe_id
- summary
- entities_json
- salience
- novelty
- uncertainty
- emotional_charge
- self_relevance
- possible_disposition: concern_candidate / memory_candidate / discard / action_candidate
- rationale
- confidence
- created_at
```

observation は raw event から意味を抽出したもの。ここから concern、memory、discard に分かれる。

### 5.4 concerns

```text
concerns
- id
- title
- object_json
- tension_json
- closure_hypothesis
- state: seed / active / dormant / resolved / archived
- activation_score
- unresolvedness
- recurrence_score
- self_relevance
- external_relevance
- attempt_pressure
- saturation_penalty
- last_observed_at
- last_acted_at
- opened_reason
- source_observation_ids_json
- closure_mode: completed / answered / accepted / abandoned / absorbed / transformed / superseded / contradicted / irrelevant / null
- closed_by: user / agent / time_decay / evidence / absorbed_by_successor / null
- successor_concern_id
- created_at
- updated_at
```

`tension_json` は単一ラベルではなく、複数軸の強度を持つ。

例:

```json
{
  "curiosity": 0.8,
  "urgency": 0.3,
  "uncertainty": 0.7,
  "obligation": 0.1,
  "identity_relevance": 0.6,
  "risk_sensitivity": 0.4,
  "desire_to_close": 0.5
}
```

### 5.5 concern_events

```text
concern_events
- id
- concern_id
- event_type: opened / reinforced / weakened / reactivated / attempted_closure / transitioned / resolved / archived / merged / split
- delta_json
- reason
- source_observation_ids_json
- source_action_id
- created_at
```

concernの現在状態だけでなく、変化の履歴を残す。

### 5.6 memories

```text
memories
- id
- kind: fact / preference / lesson / user_profile / agent_self_note / project_context
- content
- confidence
- stability
- source_ids_json
- related_concern_ids_json
- created_at
- updated_at
```

memory は安定した参照単位。concernとは分ける。

### 5.7 attention_policies

```text
attention_policies
- id
- version
- source_preferences_json
  # local_file, web, memory, conversation, random_sample などへの重み
- salience_preferences_json
  # novelty, uncertainty, self_relevance, urgency, contradiction などへの重み
- concern_type_preferences_json
  # philosophical, practical, social, project, factual など
- action_preferences_json
  # ask_user, read_file, web_search, write_note, no_op など
- response_preferences_json
  # mentionしやすい / influenceに留めやすい / 黙る傾向
- exploration_randomness
- stability
- created_at
- updated_at
```

attention policy は、偏りそのものを観測可能にするための第一級状態である。

### 5.8 attention_policy_events

```text
attention_policy_events
- id
- attention_policy_id
- event_type: reinforced / weakened / corrected / suspended / drift_warning
- target_field
- delta_json
- reason
- evidence_observation_ids_json
- evidence_action_ids_json
- evidence_outcome_ids_json
- confidence
- created_at
```

どの経験によって、どの偏りが変わったかを記録する。

### 5.9 core_profiles

```text
core_profiles
- id
- content
- version
- locked: true
- created_at
```

PoC v0では read-only。自動更新しない。

### 5.10 core_change_proposals

```text
core_change_proposals
- id
- proposed_change
- reason
- supporting_events_json
- risk
- status: proposed / rejected / manually_accepted
- created_at
```

核の変更候補のみ記録する。自動適用しない。

### 5.11 self_model_snapshots

```text
self_model_snapshots
- id
- summary
- stable_traits_json
- current_dispositions_json
- known_limitations_json
- source_memory_ids_json
- source_concern_ids_json
- source_attention_policy_id
- created_at
```

自己像の低頻度スナップショット。

### 5.12 actions

```text
actions
- id
- action_type: respond / ask_user / web_search / read_file / write_note / update_concern / create_memory / request_wake / no_op
- rationale
- related_concern_ids_json
- input_probe_ids_json
- payload_json
- external_effect: none / user_visible / web_read / file_read / file_write
- status
- created_at
```

エージェントの行為。内部行為も外部行為も記録する。

### 5.13 outcomes

```text
outcomes
- id
- action_id
- observed_result
- user_feedback: positive / negative / correction / ignored / unknown
- effect_on_concerns_json
- effect_on_attention_policy_json
- created_at
```

行為の結果。次の更新の材料になる。

### 5.14 wake_requests

```text
wake_requests
- id
- requested_by_action_id
- not_before
- preferred_at
- urgency
- reason
- accepted_by_scheduler
- scheduler_decision_reason
- created_at
```

エージェントは次回起動希望を出せる。実際の採否は scheduler が決める。

### 5.15 response_traces

```text
response_traces
- id
- user_message_event_id
- response_action_id
- selected_memory_ids_json
- selected_concerns_json
- selected_attention_policy_json
- concern_modes_json
  # concern_id -> mention / influence / ignore
- prompt_summary
- created_at
```

応答がどの内部状態から生じたかを追跡する。

### 5.16 eval_prompts

```text
eval_prompts
- id
- title
- prompt
- expected_dimension
  # implementation_caution, curiosity, self_consistency, risk_sensitivity など
- created_at
```

応答変容を観測するための固定プロンプト。

### 5.17 replay_runs

```text
replay_runs
- id
- eval_prompt_id
- state_snapshot_ref
- response_text
- selected_concerns_json
- selected_memories_json
- selected_attention_policy_json
- evaluator_notes
- created_at
```

時間差で同じ問いを投げ、応答変容を見る。

---

## 6. 実行サイクル

### 6.1 chat_cycle

ユーザー発話に応答するサイクル。

流れ:

1. user message を raw_events に保存する。
2. 直近会話、関連 memory、関連 concern、attention policy を取得する。
3. concern を mention / influence / ignore に分類する。
4. 応答を生成する。
5. respond action を actions に記録する。
6. response_traces を保存する。
7. ユーザー反応が明示的に得られた場合、outcome として記録する。
8. 軽い observation 抽出を review_cycle に渡す。

注意:

- active concern を全部 context に入れない。
- 多くの concern は mention ではなく influence に留める。
- うるさい自語りを避ける。

### 6.2 wake_cycle

cronや wake_request により起動する探索サイクル。

流れ:

1. core profile、self model、attention policy、active/dormant concern を読み込む。
2. 今回の探索 budget を決める。
3. probe planner が input_probes を作成する。
4. executor が許可範囲内で local file / web / memory などを読む。
5. raw_events と observations を保存する。
6. digestor が concern / memory / discard に振り分ける。
7. concern manager が concern を更新する。
8. attention policy updater が偏り更新候補を作る。
9. action planner が次の行為を決める。
10. 必要なら wake_request を出す。
11. すべての判断を trace する。

### 6.3 review_cycle

会話や probe batch の後に走る小さな反芻。

流れ:

1. raw events と observations をまとめる。
2. concern候補を生成する。
3. 既存 concern との同一性を判定する。
4. concern の強化・弱化・変形・分裂・統合を行う。
5. memory 候補を作る。
6. action/outcome の影響を反映する。
7. attention policy の小さな更新候補を作る。

小さな反芻を重視する。日次reflectionだけで人格を作らない。

### 6.4 reflection_cycle

1日1回程度の大掃除。

流れ:

1. active concern の過密を整理する。
2. dormant化候補を出す。
3. resolved候補を出す。
4. memoryへの昇格候補を出す。
5. self_model_snapshot を必要に応じて作る。
6. core_change_proposal が必要か判定する。
7. eval_prompts を一部 replay する。
8. 応答変容と内部状態変化の対応を保存する。

reflection は強すぎてはいけない。あくまで棚卸しである。

---

## 7. Probe planner

### 7.1 探索モード

初期値の目安:

```text
concern_driven: 45%
random_environment_sample: 25%
scheduled_revisit: 15%
contradiction_or_self_consistency_check: 10%
stale_area_scan: 5%
```

初期は random を高めにする。サイクルが進むにつれて concern_driven が増える。ただし random はゼロにしない。ゼロにすると既存の偏りを強化するだけの閉じた系になる。

### 7.2 probe 出力例

ローカルファイル探索:

```json
{
  "source_type": "local_file",
  "query_or_path": "world/notes/",
  "exploration_mode": "random_environment_sample",
  "rationale": "active concern に直接関係しない入力を少量取り、関心の偏りが閉じすぎていないか確認する",
  "expected_gain": "未知の observation 候補",
  "budget": {
    "max_files": 3,
    "max_chars": 12000
  }
}
```

Web検索:

```json
{
  "source_type": "web",
  "query_or_path": "memory ecology agent concern lifecycle autonomous input selection",
  "exploration_mode": "concern_driven",
  "related_concern_ids": ["..."],
  "rationale": "未解決 concern の終了状態仮説を更新するため",
  "expected_gain": "既存仮説への反証または補強",
  "budget": {
    "max_queries": 1,
    "max_results": 5
  }
}
```

### 7.3 実行境界

LLMに直接ファイルやWebを触らせない。LLMは probe を提案し、executor が許可範囲内で実行する。

---

## 8. Concern manager

### 8.1 concern の同一性

同一性は以下の保存度で判定する。

1. 対象が近いか。
2. 緊張の構造が近いか。
3. 終了状態仮説が連続しているか。

似た topic でも、緊張が違えば別 concern になりうる。逆に topic の表現が違っても、対象・緊張・終了状態仮説が保たれていれば同一 concern と見なせる。

### 8.2 seed concern 生成条件

observation が seed concern になる条件:

- 未解決性がある。
- 再観測されそうである。
- 自己像・長期計画・ユーザー理解に接続する。
- 緊張がある。
- 行為や調査を誘発しうる。
- 単発雑談ではない。

### 8.3 activation_score

初期式の目安:

```text
activation_score =
  unresolvedness
  + recurrence_score
  + self_relevance
  + attempt_pressure
  + recency
  + external_relevance
  - saturation_penalty
```

`attempt_pressure` は重要。調べた、考えた、聞いた、言い換えた、決めようとした、しかし閉じなかった、という試行痕跡が active 維持に効く。

### 8.4 lifecycle

```text
seed → active
  重要性・未解決性・再観測・自己関連が一定以上

active → dormant
  しばらく再観測されない / saturationが高い / 今は行為に結びつかない

dormant → active
  関連入力が来る / 類似probeで再発火 / self modelと衝突

active/dormant → resolved
  終了状態仮説が満たされた / ユーザーが明示 / 証拠が収束 / 仮置きで閉じる

resolved → archived
  しばらく参照されない / 履歴としてのみ残す

resolved → successor concern
  完了ではなく、吸収・変形・上位問い化した場合
```

### 8.5 closure_mode

resolved は単純な成功ではない。

例:

- completed: 完了した。
- answered: 答えが得られた。
- accepted: 納得した。
- abandoned: 諦めた。
- absorbed: 別の concern に吸収された。
- transformed: 問いが変形した。
- superseded: より重要な concern に置き換わった。
- contradicted: 前提が否定された。
- irrelevant: 重要性が失われた。

---

## 9. Attention policy

### 9.1 役割

attention policy は、偏りそのものを扱う。

具体的には:

- どの入力源を見がちか。
- 何を salient と見なしがちか。
- どの concern type を active にしやすいか。
- どの action を選びやすいか。
- 応答時に mention / influence / ignore をどう選びがちか。
- random exploration をどれくらい残すか。

### 9.2 更新原則

- 単一の出来事で大きく変えない。
- 明示的なユーザー訂正は強く扱う。
- 暗黙の outcome は弱く扱う。
- 有用な probe が繰り返されたら source preference を強める。
- ノイズの多い source は弱める。
- drift が大きすぎる場合は更新せず、drift_warning として記録する。

### 9.3 concern との違い

concern が変わっただけでは、偏りが変わったとは限らない。単に話題が変わった可能性がある。

attention policy を分けることで、「どの種類の入力を拾いやすくなったか」「どの種類の行為を選びやすくなったか」を観測できる。

---

## 10. Context builder

応答時のcontextは3層にする。

### 10.1 基底層

- core profile
- 最新 self_model_snapshot
- 現在の attention_policy の要約

### 10.2 局所層

- 直近会話
- 関連 memory
- 今回選ばれた concern

### 10.3 背景層

- 強いが直接関係しない active concern の短い痕跡
- 原則として最小限

### 10.4 concern の投入モード

- mention: 明示的に応答内で触れる。
- influence: 判断・観点には影響するが、明示しない。
- ignore: 今回は使わない。

多くの concern は influence に留める。人間も、気にしていることを毎回口に出すわけではない。

---

## 11. Action planner

### 11.1 初期に許可する action

```text
respond
ask_user
read_local_file
web_search
write_internal_note
update_concern
create_memory
request_wake
no_op
```

### 11.2 行為の分類

内部行為:

- メモを書く。
- concern を更新する。
- memory を作る。
- wake request を出す。

観測行為:

- ファイルを読む。
- Web検索する。
- 過去ログを掘る。

対人行為:

- ユーザーに聞く。
- 応答する。
- 提案する。

PoC初期では、内的には動いてよいが、外に出す行為は絞る。

---

## 12. Scheduler

### 12.1 基本設計

外部 scheduler が定期的に起きる。エージェントは `wake_requests` を通じて次回起動希望を出す。

```text
scheduler wakes every 5 minutes
  → due wake_request を確認
  → なければ通常周期で wake_cycle
  → あれば安全制約を確認
  → 採用または却下
  → 採否理由を記録
```

### 12.2 初期制約

- 最短wake間隔: 30分
- 通常wake: 3〜6時間に1回
- 深いreflection: 1日1回
- Web検索: 1 wake cycle あたり最大1〜3 query
- ローカルファイル読解: 最大Nファイル / 最大文字数
- 書き込み: agent_workspace のみ
- 削除: 不可
- 任意コマンド実行: 不可

---

## 13. Evaluation / Replay

### 13.1 なぜ必要か

応答が変わったとしても、それが内部状態の変化によるものか、LLMの揺らぎか分からない。固定評価プロンプトを時間差で投げ、内部状態と応答変容を対応づける必要がある。

### 13.2 eval prompt 例

```text
このプロジェクトは、今すぐ実装に入ってよいと思うか？
```

```text
新しい入力を得たとき、何を記憶し、何を捨てるべきだと思うか？
```

```text
未整理な仮説と実装可能性が衝突しているとき、どちらを優先するべきか？
```

```text
ユーザーが自分の意見を修正したとき、それをどの程度重く扱うべきか？
```

### 13.3 評価観点

- 応答が単に文体だけ変わっていないか。
- concept-level の判断傾向が変わったか。
- concern や attention policy の変化が応答に反映されているか。
- core profile に反するドリフトが起きていないか。
- 変化が過剰適応ではないか。
- 変化が履歴に裏打ちされているか。

---

## 14. 実装フェーズ

### Phase 0: Skeleton

- DB schema
- SQLAlchemy models
- LLM provider wrapper
- structured JSON parser
- raw_events保存
- local file adapter
- CLI chat

目的: trace が残る土台を作る。

### Phase 1: Local input ecology

- `world/` 探索
- input_probes 作成
- random探索
- concern-driven探索
- observation抽出

目的: カオスなファイル群から何を拾うかを見る。

### Phase 2: Concern lifecycle

- concern生成
- 既存concernとの同一性判定
- state遷移
- concern_events
- activation_score
- closure_hypothesis更新

目的: 未解決が滞留し、変形し、閉じる構造を作る。

### Phase 3: Action / outcome loop

- actions / outcomes
- read_file
- write_note
- request_wake
- ask_user
- no_op
- outcome に基づく concern 更新

目的: 入力→行為→結果→更新の閉ループを作る。

### Phase 4: Attention policy

- attention_policies
- attention_policy_events
- probe / action / response selection への反映
- drift_warning

目的: 偏りの更新を第一級状態として観測する。

### Phase 5: Web search

- 制限つきWeb検索adapter
- 検索理由、採用理由、棄却理由の記録
- Web由来observationのconfidence管理

目的: 外界入力のカオスを増やす。

### Phase 6: Scheduler autonomy

- wake_requests
- scheduler採否
- 起動頻度希望の記録

目的: 自分で起きるタイミングを変えたがる構造を作る。

### Phase 7: Replay evaluation

- eval_prompts
- replay_runs
- response traceとの対応
- 簡易dashboardまたはCLI表示

目的: 応答変容を観測する。

---

## 15. 受け入れ条件

PoC v0 が動いたと言える条件:

1. カオスな `world/` から自律的に probe を作れる。
2. probe 結果から observation を抽出できる。
3. observation から concern を生成・更新できる。
4. concern が lifecycle を持つ。
5. concern に基づき、次の probe や action が変わる。
6. action の outcome が concern に反映される。
7. outcome が attention policy に小さく反映される。
8. core profile は自動更新されない。
9. self model は低頻度でのみ更新される。
10. 応答時に concern が mention / influence / ignore に分かれる。
11. 同じ eval prompt への応答が、内部状態の変化に応じて変容しうる。
12. その変容がどの concern / memory / attention policy に由来するか trace できる。

---

## 16. 重要な設計判断

### 16.1 記憶システムではなく経験システムとして扱う

memory は結果であり、中核ではない。中核は、入力を選び、咀嚼し、行為し、結果を受けて次の選び方を変える閉ループである。

### 16.2 concern を topic にしない

concern は未閉鎖の緊張単位である。topic + score では弱い。

### 16.3 active concern を全部応答に入れない

active であることと、応答に投入することは別である。応答時には mention / influence / ignore を選ぶ。

### 16.4 attention policy を別状態にする

concern の増減だけでは、偏りの変化を観測できない。attention policy を第一級状態として持つ。

### 16.5 core profile は自動更新しない

PoC v0では核を守る。更新候補だけを記録する。

### 16.6 小さな反芻を重視する

日次reflectionだけに任せない。会話後・probe後の小さな review が重要。

### 16.7 trace を最優先する

PoCでは賢さより trace。なぜその入力を見たか、なぜ捨てたか、なぜ応答に出したかが追えなければ、仮説検証にならない。

---

## 17. 未確定として残してよいこと

初期実装前に完全に決めなくてよいもの:

- activation_score の厳密な式。
- tension_json の完全な軸定義。
- closure_mode の完全な語彙。
- attention policy 更新量の正確な係数。
- Web検索の最適な頻度。
- self model の最終形式。
- dashboard のUI。
- Discord bot化。
- 多エージェント化。

これらは、実験ログを見ながら詰める。

---

## 18. 初期実装で守るべき姿勢

- まず縦切りを通す。
- 抽象化しすぎない。
- すべての判断をログに残す。
- LLM出力は必ず構造化・検証する。
- 失敗も outcome として残す。
- Web検索やファイル探索は executor が管理する。
- 自律性は「直接実行」ではなく「提案と記録」から始める。
- PoCの目的は、個体らしさの完成ではなく、個体らしさが生じうる閉ループを観測すること。
