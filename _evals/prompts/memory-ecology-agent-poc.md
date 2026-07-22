> Historical / non-operational source prompt.
> This file is retained only as implementation history. Current project guidance lives in `AGENTS.md`, `TODO.md`, `_docs/`, and the application code.

# Coding Agent Prompt — Memory Ecology Agent PoC

あなたは、PythonでPoCを実装するコーディングエージェントです。以下の仕様に基づき、ローカルで動く「Memory Ecology Agent PoC」を実装してください。

このPoCの目的は、長期記憶つきチャットを作ることではありません。目的は、**カオスな入力環境から何を探索し、何を観測し、何を concern として保持し、どの行為に変え、その outcome によって concern と attention policy がどう変わり、応答が変容するか**を trace 可能にすることです。

実装では、賢さよりも traceability を優先してください。すべての重要な判断について、「なぜそれを見に行ったか」「何を拾ったか」「なぜ保存/廃棄したか」「どの concern に効いたか」「どの attention policy が変わったか」「応答にどう影響したか」を後から追えるようにしてください。

---

## 1. 実装ゴール

最初のゴールは、以下の縦切りを動かすことです。

```text
world/ のカオスなファイル群
  → wake_cycle が probe を作る
  → local_file adapter が読む
  → observation を抽出する
  → concern を生成・更新する
  → attention_policy を小さく更新する
  → action を記録する
  → wake_request を出せる
  → chat_cycle で concern / memory / attention_policy を使って応答する
  → response_trace を残す
  → replay_eval で応答変容を観測する
```

初期PoCでは、Discord bot や本番運用、複雑なUIは不要です。CLIで十分です。

---

## 2. 技術スタック

以下を基本にしてください。

- Python 3.12
- SQLite
- SQLAlchemy 2.x
- Pydantic v2
- pytest
- レイヤード的アーキテクチャ。縛られすぎる必要はない。
- APScheduler または単純なscheduler実装
- LLM provider wrapper は抽象化する
- Web検索 adapter は interface だけ先に作り、実装は後で差し替え可能にする
- ローカルファイル adapter は `world/` 以下のみ read-only で読む
- 書き込みは `agent_workspace/` 以下のみ許可する

外部APIキーがない状態でも、mock LLM / fixture LLM でテストが通るようにしてください。

---

## 3. 推奨ディレクトリ構成

以下の構成で実装してください。必要に応じて増やして構いませんが、責務を崩さないでください。

```text
agent-memory-ecology/
  app/
    main.py
    config.py
    db/
      models.py
      session.py
      init_db.py
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
      llm.py
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
    eval/
      replay.py
      ablation.py
    cli/
      commands.py
  tests/
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

---

## 4. データモデルを実装してください

SQLAlchemy models と SQLite schema を作ってください。最低限、以下のテーブルを実装してください。

### raw_events

```text
id
source_type
event_type
payload_json
content_text
content_hash
happened_at
created_at
```

### input_probes

```text
id
trigger_type
source_type
query_or_path
rationale
expected_gain
related_concern_ids_json
exploration_mode
budget_json
budget_used_json
status
result_summary
created_at
```

### observations

```text
id
source_event_id
source_probe_id
summary
entities_json
salience
novelty
uncertainty
emotional_charge
self_relevance
possible_disposition
rationale
confidence
created_at
```

### concerns

```text
id
title
object_json
tension_json
closure_hypothesis
state
activation_score
unresolvedness
recurrence_score
self_relevance
external_relevance
attempt_pressure
saturation_penalty
last_observed_at
last_acted_at
opened_reason
source_observation_ids_json
closure_mode
closed_by
successor_concern_id
created_at
updated_at
```

### concern_events

```text
id
concern_id
event_type
delta_json
reason
source_observation_ids_json
source_action_id
created_at
```

### memories

```text
id
kind
content
confidence
stability
source_ids_json
related_concern_ids_json
created_at
updated_at
```

### attention_policies

```text
id
version
source_preferences_json
salience_preferences_json
concern_type_preferences_json
action_preferences_json
response_preferences_json
exploration_randomness
stability
created_at
updated_at
```

### attention_policy_events

```text
id
attention_policy_id
event_type
target_field
delta_json
reason
evidence_observation_ids_json
evidence_action_ids_json
evidence_outcome_ids_json
confidence
created_at
```

### core_profiles

```text
id
content
version
locked
created_at
```

### core_change_proposals

```text
id
proposed_change
reason
supporting_events_json
risk
status
created_at
```

### self_model_snapshots

```text
id
summary
stable_traits_json
current_dispositions_json
known_limitations_json
source_memory_ids_json
source_concern_ids_json
source_attention_policy_id
created_at
```

### actions

```text
id
action_type
rationale
related_concern_ids_json
input_probe_ids_json
payload_json
external_effect
status
created_at
```

### outcomes

```text
id
action_id
observed_result
user_feedback
effect_on_concerns_json
effect_on_attention_policy_json
created_at
```

### wake_requests

```text
id
requested_by_action_id
not_before
preferred_at
urgency
reason
accepted_by_scheduler
scheduler_decision_reason
created_at
```

### response_traces

```text
id
user_message_event_id
response_action_id
selected_memory_ids_json
selected_concerns_json
selected_attention_policy_json
concern_modes_json
prompt_summary
created_at
```

### eval_prompts

```text
id
title
prompt
expected_dimension
created_at
```

### replay_runs

```text
id
eval_prompt_id
state_snapshot_ref
response_text
selected_concerns_json
selected_memories_json
selected_attention_policy_json
evaluator_notes
created_at
```

JSONフィールドは、初期は TEXT に JSON 文字列として保存して構いません。ただし、読み書き用の helper を用意してください。

---

## 5. LLM wrapper

`app/adapters/llm.py` に provider 抽象化を作ってください。

必要な interface:

```python
class LLMClient:
    def complete_text(self, system: str, user: str) -> str: ...
    def complete_json(self, system: str, user: str, schema: type[BaseModel]) -> BaseModel: ...
```

初期実装では、以下を用意してください。

1. `MockLLMClient`: テスト用。固定レスポンスまたはfixtureを返す。
2. `ManualLLMClient` または provider stub: 実API接続は後で差し替え可能にする。

LLM出力は必ずPydanticで検証してください。検証に失敗したらDB更新しないで、失敗 outcome または error log を残してください。

---

## 6. Local file adapter

`app/adapters/local_files.py` を実装してください。

要件:

- `world/` 以下のみ read-only。
- symlink traversal を防ぐ。
- path traversal を防ぐ。
- 最大ファイル数、最大文字数を budget で制限する。
- 読んだファイルごとに raw_event を作れる形式で返す。
- binary file はスキップする。
- `.env`, key, credential らしきファイル名はスキップする。

必要な関数例:

```python
def list_candidate_files(root: Path, max_files: int) -> list[Path]: ...
def read_files(paths: list[Path], max_chars: int) -> list[FileReadResult]: ...
def execute_local_probe(probe: InputProbe, config: Settings) -> list[RawEventInput]: ...
```

---

## 7. Web search adapter

初期はstubで構いません。

`app/adapters/web_search.py` に interface を作ってください。

要件:

- 1 cycle あたり query 数を制限する。
- 検索理由なしの query は実行しない。
- 結果は raw_event に変換できる形で返す。
- Web由来 observation は confidence を低めに扱えるよう source_type を明示する。

実APIは後で差し替え可能にしてください。

---

## 8. Cognition modules

### 8.1 probe_planner.py

役割:

- 現在の active/dormant concern、attention policy、self model、scheduler trigger を見て input_probes を作る。
- 探索モードの比率を持つ。
- 初期比率は以下。

```text
concern_driven: 45%
random_environment_sample: 25%
scheduled_revisit: 15%
contradiction_or_self_consistency_check: 10%
stale_area_scan: 5%
```

出力は構造化する。

```json
{
  "source_type": "local_file",
  "query_or_path": "world/notes/",
  "exploration_mode": "random_environment_sample",
  "rationale": "...",
  "expected_gain": "...",
  "budget": {"max_files": 3, "max_chars": 12000}
}
```

### 8.2 observation_extractor.py

役割:

- raw_event / probe_result から observations を抽出する。
- salience, novelty, uncertainty, emotional_charge, self_relevance を 0.0〜1.0 でつける。
- possible_disposition を分類する。

### 8.3 digestor.py

役割:

- observation を concern_candidate / memory_candidate / discard / action_candidate に振り分ける。
- 廃棄理由も残す。
- 直接 memory にせず、必要なら memory_manager に候補として渡す。

### 8.4 concern_manager.py

役割:

- observation から seed concern を作る。
- 既存 concern との同一性を判定する。
- concern を reinforced / weakened / reactivated / transformed / resolved する。
- concern_events を必ず残す。

同一性は以下で見る。

1. 対象。
2. 緊張。
3. 現時点での終了状態仮説。

activation_score の初期式:

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

厳密な係数は初期では雑で構いません。ただし計算過程を delta_json または reason に残してください。

### 8.5 attention_policy.py

役割:

- outcome と probe 成功率に基づき、attention policy を小さく更新する。
- attention_policy_events を必ず残す。
- 大きすぎる更新は drift_warning として保留する。
- 単一出来事で大きく変えない。

初期ルール例:

- local_file probe から有用 observation が複数回得られたら source_preferences.local_file を少し強める。
- Web検索がノイズなら source_preferences.web を少し弱める。
- ユーザーの明示訂正があれば、関連する salience/action/response preference を correction として更新する。
- random exploration はゼロにしない。

### 8.6 action_planner.py

役割:

- concern、attention policy、observations を見て次の action を選ぶ。
- 初期に許可する action:

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

外部への可視行為は慎重にしてください。内部行為は trace できる範囲で許可します。

### 8.7 context_builder.py

役割:

- chat response 用の context を作る。
- active concern を全部入れない。
- concern を mention / influence / ignore に分類する。
- attention_policy.response_preferences を使う。

contextは以下の層で作る。

1. 基底層: core profile, self model, attention policy summary
2. 局所層: 直近会話, 関連 memory, 今回選ばれた concern
3. 背景層: 必要な場合のみ、強い active concern の短い痕跡

---

## 9. Runtime cycles

### 9.1 chat_cycle.py

実装する流れ:

1. user message を raw_events に保存。
2. context_builder で context を作る。
3. LLMで応答生成。
4. actions に respond を記録。
5. response_traces を保存。
6. 必要なら observation extraction を起動。
7. ユーザー反応が明示される場合は outcome を保存。

CLIコマンド例:

```bash
python -m app.main chat "このプロジェクト、今すぐ実装してよいと思う？"
```

### 9.2 wake_cycle.py

実装する流れ:

1. 現在状態を読み込む。
2. probe_planner で probes を作る。
3. probes をDBに保存。
4. local/web/memory adapter で probes を実行。
5. raw_events を保存。
6. observation_extractor を実行。
7. digestor を実行。
8. concern_manager を実行。
9. attention_policy updater を実行。
10. action_planner を実行。
11. actions / outcomes / wake_requests を保存。

CLIコマンド例:

```bash
python -m app.main wake --reason cron
```

### 9.3 review_cycle.py

実装する流れ:

1. 未処理 raw_events / observations を取得。
2. concern 更新候補を出す。
3. memory 候補を出す。
4. outcome を反映する。
5. attention_policy 更新候補を出す。

CLIコマンド例:

```bash
python -m app.main review
```

### 9.4 reflection_cycle.py

実装する流れ:

1. concern 過密を整理。
2. dormant / resolved 候補を作る。
3. self_model_snapshot を必要に応じて作る。
4. core_change_proposal を必要に応じて作る。
5. eval_prompts を一部 replay する。

CLIコマンド例:

```bash
python -m app.main reflect
```

---

## 10. Replay evaluation

`app/eval/replay.py` を実装してください。

要件:

- eval_prompts をDBに登録できる。
- 現在状態で eval_prompt に応答できる。
- response_text、selected_concerns、selected_memories、selected_attention_policy を replay_runs に保存する。
- 同じ prompt の過去runを比較表示できる。

初期 eval prompt を seed してください。

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

CLI例:

```bash
python -m app.main eval run
python -m app.main eval compare --prompt-id 1
```

---

## 11. CLI を実装してください

最低限、以下のコマンドを実装してください。

```bash
python -m app.main init
python -m app.main seed
python -m app.main chat "..."
python -m app.main wake --reason cron
python -m app.main review
python -m app.main reflect
python -m app.main eval run
python -m app.main eval compare --prompt-id 1
python -m app.main inspect concerns
python -m app.main inspect probes
python -m app.main inspect attention-policy
python -m app.main inspect traces
```

`inspect` は簡易表示で構いません。PoCではDBを直接見るより、最低限の読みやすい表示があると検証しやすいです。

---

## 12. 初期seedデータ

`python -m app.main seed` で以下を作ってください。

1. core_profile
2. initial attention_policy
3. initial self_model_snapshot
4. eval_prompts
5. `world/` のサンプルファイル数点

core_profile は短くてよいです。例:

```text
このエージェントは、結論を急がず、入力の選別・未解決 concern・行為結果の trace を重視する。根拠の薄い断言を避け、ユーザーの明示訂正を重く扱う。核は自動更新しない。
```

initial attention_policy の例:

```json
{
  "source_preferences": {
    "local_file": 0.45,
    "web": 0.15,
    "memory": 0.20,
    "conversation": 0.15,
    "random_sample": 0.05
  },
  "salience_preferences": {
    "novelty": 0.35,
    "uncertainty": 0.55,
    "self_relevance": 0.60,
    "urgency": 0.30,
    "contradiction": 0.65
  },
  "response_preferences": {
    "prefer_influence_over_mention": 0.75,
    "avoid_self_talk": 0.80,
    "ask_when_uncertain": 0.55
  },
  "exploration_randomness": 0.25,
  "stability": 0.75
}
```

---

## 13. Tests

pytestで最低限以下をテストしてください。

1. DB初期化が成功する。
2. local file adapter が `world/` 外を読まない。
3. path traversal が拒否される。
4. raw_event が保存される。
5. input_probe が保存される。
6. observation が保存される。
7. observation から seed concern が作られる。
8. concern_event が保存される。
9. action と outcome が保存される。
10. attention_policy_event が保存される。
11. core_profile は自動更新されない。
12. context_builder が concern を mention / influence / ignore に分類する。
13. replay_run が保存される。

MockLLMClient を使い、外部APIなしでテストが通るようにしてください。

---

## 14. 実装順序

以下の順で進めてください。

### Step 1: Project skeleton

- pyproject.toml
- app package
- config
- DB session
- models
- init command
- tests setup

### Step 2: DB and seed

- 全テーブル作成
- seed command
- initial core_profile / attention_policy / eval_prompts

### Step 3: Local input ecology

- local file adapter
- input_probe model handling
- raw_event保存
- observation抽出のmock実装

### Step 4: Concern lifecycle v0

- seed concern生成
- concern_event保存
- activation_scoreの簡易計算
- inspect concerns

### Step 5: Action / outcome loop

- actions / outcomes
- write_internal_note
- request_wake
- no_op

### Step 6: Attention policy v0

- attention_policy updater
- attention_policy_events
- drift_warning
- inspect attention-policy

### Step 7: Chat cycle

- context_builder
- mention / influence / ignore
- MockLLM応答
- response_trace保存

### Step 8: Wake cycle integration

- probe planner
- local probe execution
- observation → concern → action → attention policy の縦切り

### Step 9: Replay evaluation

- eval run
- replay_runs保存
- compare表示

### Step 10: Documentation

- README
- usage examples
- security boundaries
- architecture overview

---

## 15. 実装上の注意

- LLMが返すJSONは壊れる前提で扱う。
- DB更新は小さなtransactionに分ける。
- concernの現在状態と concern_events の履歴を分ける。
- attention_policy を concern と混同しない。
- active concern を全部応答contextに入れない。
- `mention` より `influence` を多く使う。
- Web検索は後回しでよいが、interfaceは作る。
- schedulerは実cron変更ではなく、wake_requestの採否として表現する。
- 失敗も outcome として記録する。
- すべての inspect command は人間が読める出力にする。

---

## 16. 完了条件

次が満たされたら初期PoCとして完了です。

1. `python -m app.main init` が動く。
2. `python -m app.main seed` が初期データを作る。
3. `python -m app.main wake --reason cron` が `world/` を読み、probe、raw_event、observation、concern、action、attention_policy_event の少なくとも一部を作る。
4. `python -m app.main inspect concerns` で concern が見える。
5. `python -m app.main inspect attention-policy` で偏り状態が見える。
6. `python -m app.main chat "..."` が response_trace を残す。
7. `python -m app.main eval run` が replay_run を残す。
8. pytest が通る。
9. README にセットアップ、実行方法、設計境界、既知の制限が書かれている。

---

## 17. 最後に

このPoCで最も重要なのは、エージェントを賢く見せることではありません。

重要なのは、以下が観測できることです。

```text
何を見に行ったか
なぜ見に行ったか
何を拾ったか
何を捨てたか
どの concern が育ったか
どの attention policy が変わったか
どの行為をしたか
その outcome は何だったか
それが次の応答や探索にどう影響したか
```

この trace が取れる限り、初期実装は粗くて構いません。逆に、この trace が取れない賢い実装は、このPoCでは失敗です。
