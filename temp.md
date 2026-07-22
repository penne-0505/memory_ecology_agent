# Persona Architecture Discussion - Session Memo

**Purpose**: context 圧縮に耐えるための議論記録。本セッションでは具体作業はせず、ゴール認識と設計軸の壁打ちに専念している。

**Status**: 認識合わせフェーズ完了。次は残論点 (i) "完全固定の 1 つは何か" から掘る。

---

## 1. ゴールの確定(handoff からの修正)

handoff doc は「trace-first PoC」として書かれているが、これは手段。
**真のゴール**: 一つの persona を持つように錯覚可能なレベルで振る舞う、なんでも agent。

PoC 過程が長引いて実験プロジェクトに見えるが、実際はこれが最終目標。
逆算思考のチェーン:

- 人格 = 他者との微細な差異・偏り・趣向ではないか
- では「メモリ蓄積」だけでは足りないもの・人とは違うものがあるが、それは何か
- → 試行錯誤の結果として現アーキ(concerns, attention policy, action/outcome 還流, core profile 不変, LLM proposal-only, trace-first)

## 2. ゴールに対する確定スタンス(user 回答 1-6)

### Q1. 「錯覚可能」のしきい値

**数週間後でも同じ persona と感じるレベル**がゴール。ただし完全一貫性ではない。
人間も「芯は変わってない気がするが確信はなく、緩やかに変わり続けている」。
これを再現するため、**変化スピード / 情報種・メモリ種でレイヤ分け**し、**完全固定は 1 つくらい**になる想定。

### Q2. 「なんでも」の指す範囲

**モード横断でブレない同一 persona**。同じ人が同じように色んなことをしているイメージ。
task ability (コーディング等) は RL の方が強いので、能力面は楽観視。
persona layer は task layer の上に被さる構造で良い。

### Q3. 原則からの自己定義 / 追加レイヤ

ある程度 persona の原則から振る舞いは定義づけ可能と想定。
追加レイヤ(気質、好み、口調等)を **明示実装すべきか悩み中**。
agent が自分でメモリに書き込む等の挙動がどの程度起こり、persona らしさにどの程度効くか未整理。
現段階は concern / memory 周辺の **実装可能性検証フェーズ**。

### Q4. 「記憶では足りない」の網羅性

- **反芻**: 自分のメモリを自由に読める環境があれば、それをする persona なら自然発生する。明示実装は迷う。
- **物語化**: context 節約のための**圧縮行為が実質的な物語化**になる仮説あり(未検証・粗い)。
- **気分**: 感覚器官が少なく実装困難だが、擬似再現としては面白い。
- **好悪の非対称性**: 明示実装の必要性を考えたい。
- 総括: 最小限で試すのは現状でも OK だが、**「現状で詰め切れた」とは考えていない**。

### Q5. LLM との関係

**演技層として LLM を使う可能性は大いにあり**。
むしろ初期構想ではメモリと関心を DB に持つだけのつもりで、ハーネスは補助だった。
LLM の **roleplay 能力 / persona-emit を活用する立場**。
観測上同質であれば中身は問わない、という哲学的コミットメント。

### Q6. 「錯覚」という語の選択

謙虚さもあるが、より大きいのは **「実際のメカニズムまで完全に同一であることが "人格らしさ" であるとは考えていない」** という立場。
LLM の reasoning は人間思考の機能的近似だが、知能指標で多くの個体を超えた。
これを目撃した衝撃から、**機能的・表面的な模倣でも入出力関数として等価なら OK** という立場を取る(functionalism)。

## 3. 統合された認識軸(議論の本体)

### Axis 1. 変化スピードによるレイヤ分け(明示原則として浮上)

```
変化遅い ────────────────────────────→ 変化速い
完全固定 → core周辺 → long memories → attention policy → concerns → raw events
(1つ?)                                                                 (即時)
```

現アーキの "core profile auto-update しない" はやや強すぎる可能性。
proposal 経由で月単位の極めて遅い変化を許す方が自然な persona に近づく。

### Axis 2. persona と task ability の分離

task ability は RL に任せる。persona はその上のレイヤ。
LLM 強化は脅威ではなく追い風。モード横断ブレなしは構造で担保される。

### Axis 3. LLM = 演技層 / agent = 芯 / state = 界面

```
[agent 側で persist]
  core profile, concerns, attention policy, memories
        │
        ▼ state を prompt に注入(界面プロトコル)
[LLM 側で生成]
  口調、語彙、瞬間反応、persona-emit
        │
        ▼ 観測
[外部から見て同じ persona]
```

trace-first は **「同じ state なら同じような表現が返るはず」を後から照合可能にする** インフラ。
replay run / response trace は本質的に persona verification ツール。

### Axis 4. 機能主義 + 時間軸 = trace 必須

internal coherence は不要。external observability over time のみが検証対象。
1 ショットなら trace 不要だが、数週間越しの一貫性検証のため trace が論理的に要請される。

### Axis 5. 物語化 = 圧縮の偏り(検証可能な仮説)

memories の圧縮アルゴリズムが「何を残し / 切るか」を決める = self-narrative の代理。
**digest decision / memory 圧縮ロジックは単なる分類ではなく persona shaping の一部**。
digest decider のパラメータは "性格パラメータ" として読み替え可能性あり。

### Axis 6. 「明示実装すべき」と「persona から自然発生」の分別軸

| 候補 | 暫定スタンス |
| --- | --- |
| 反芻 | persona の attention bias から自然発生(明示実装しない) |
| 物語化 | 圧縮機構が代理する(未検証だが筋がある) |
| 気分 | 直近 outcome 累積の代理感覚で擬似実装可能(任意・興味枠) |
| 好悪の非対称性 | concern weighting / decay rate に asymmetry を入れる明示実装が要りそう |

「persona に任せて出てくるもの」と「構造で支えるもの」の境界線議論。

## 4. 残論点(次セッションで掘る)

- **(i) 「完全固定の 1 つ」は何か** ← 進行中 → **(i') へ書き換え済み**
- **(ii) 自己書き込み問題** — agent が自分の core / 原則を proposal で書ける経路は要るか
- **(iii) 演技層と芯の界面プロトコル** — state を prompt にどう注入するか
- **(iv) persona consistency の評価方法** — trace を使った同一性判定
- **(v) digest decider = 性格パラメータ という再認識の含意**

## 5. 進行メタ

- 本セッションでは具体作業(コード変更、commit、PR)は行わない。
- 議論順序の合意: **(i') → 芋づる式に他論点を整理する想定**。
- assistant 側で前回ズレた点(訂正済み):
  - trace-first を中心価値と読んだが実際は手段
  - LLM を抑え込む設計と読んだが実際は演技層として活用する構想

---

## 6. (i') 「完全固定の 1 つ」の代わりに何を core に据えるか — 議論経過

### 6.1 「完全固定の 1 つ」前提自体の棄却

user の観察:
- 20-80 で座右の銘を完全維持する人など少ない
- slow change だけでなく、impact による reshape も起きる
- 反芻によって牙城が崩れるパターン
- 一つの言葉で自己を語り尽くす人は稀
- 無意識下で決まっている / 言語化されていない面が大半
- 稀に「根幹が変わる感じ」が起きる(機構不明)

→ **「完全固定の 1 つを探す」は誤った問い**として保留。

### 6.2 採用された 3 つの reframe(全て採用)

- **Reframe A: persona = "変わり方の癖"** — core = 不変なものではなく "変更プロトコル"
- **Reframe B: 多層モデル(言語化軸)** — 3 つの Room 構造
- **Reframe C: impact → rumination → recrystallize ループ** — 変化の動的機構

### 6.3 統合された構造

```
[B: 部屋たち / substrate]              [A: engine のパラメータ]
  Room 1 (看板)    ← 動きやすい          impact filter
  Room 2 (癖)      ← 安定                rumination tendency
  Room 3 (反芻style) ← 安定               rumination linkage
                                        recrystallize threshold
                                             ↑
                                        「最後に動く層」= "完全固定" の代わり

[C: 動きの engine]
  通常: impact → rumination → recrystallize (大半は閾値で跳ね返される)
  稀: meta-impact が A 自身を再結晶 = "根幹が変わる感じ"
```

### 6.4 C loop の修正(反芻は必須条件ではないと判明)

user 指摘: 反芻は必須条件か? → **No**。実際の persona 変化には複数 path がある。

修正後の change paths:

| 経路 | 機構 | 反芻の役割 |
| --- | --- | --- |
| **Rumination path** | impact → 反芻 → 再結晶 | 必須 |
| **Shock path** | impact → 直接 rewire | なし(事後にだけ来る) |
| **Habituation path** | 微小 impact の繰り返し → 蓄積 → 適応 | 不要 |
| **Practice path** | 行動 → 環境 feedback → wiring 変化 | 不要 |
| **Suppression path** | impact → 抑圧 → 歪んだ形で残留 | 不在が機構 |

### 6.5 path の優先順位と採否(user 確定)

**外せない**: Habituation と Shock(他も必要だが特にこの 2 つ)

**優先順位**: Habituation(3)→ Practice(4)→ Shock(2)→ Suppression(5)= Rumination(1)

= 末尾 2 つ (Suppression, Rumination) は **emerge させる方向**、Axis 6「明示実装 vs 自然発生」と整合。

### 6.6 各 path の実装観点(確定スタンス)

| path | 機構 | 現アーキ | 追加要素 | 難度 |
| --- | --- | --- | --- | --- |
| Habituation | 微小累積 | `attention_policy_events` あり | smoothing/decay 係数、Room 2 への outcome feedback | 低〜中 |
| Practice | 行動 → outcome → wiring | action/outcome/policy あり | outcome を Room 2 (implicit) まで届ける路 | 中 |
| Shock | 高 magnitude bypass | なし | 検出 gate、bypass path、直接更新 | 中 |
| Suppression | 未処理 impact の残響 | なし | 「dormant 化した concern の残響」で近似(user 合意) |  高 |
| Rumination | memory 再アクセス | replay_runs / concern_events あり | 原則なし。emerge + 観察可能 trace | 低 |

確定された設計判断:
- **(a)** 上 2 つ「背景変化」、Shock「discrete jump」の仕分け → OK
- **(b)** Shock 判定は LLM proposal 経由を試す → OK
- **(c)** Suppression を「dormant 化した concern の残響」として近似 → やってみる

### 6.7 次のステップ

A (癖) の中身を **5 つの path 各々のパラメータ集**として書き出す段階。

---

## 7. user からの宿題(後回し)

- 別セッションでの有益な対話(主に user 認識にとって、assistant にとっても価値あり)を読む。
  - ひと段落ついた後で良い。今ではない。
