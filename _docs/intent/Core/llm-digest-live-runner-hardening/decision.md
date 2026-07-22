---
title: LLM Digest Live Runner Hardening Decision
status: active
draft_status: n/a
created_at: 2026-06-02
updated_at: 2026-06-03
references:
  - "_docs/plan/Core/llm-digest-live-runner-hardening/plan.md"
  - "_docs/qa/Core/llm-digest-live-runner-hardening/test-plan.md"
  - "_docs/intent/Core/llm-digest-proposal-quality-evaluation/decision.md"
related_issues: []
related_prs: []
---

## Context

2026-06-02 の live model comparison では、`qwen/qwen3.6-plus` と `moonshotai/kimi-k2.6` を直列に回したため、OpenRouter Logs 以外では進捗が見えにくかった。また、validation failure は集計上 `ValidationError` として見えるものの、runner レベルでは provider 問題、schema 問題、timeout、orchestration 問題を即座に分けにくかった。

## Decision

Live digest proposal evaluation は、安全な小さい initial batch を先に走らせる。重大な provider / schema / timeout 問題が出なければ、残りを bounded concurrency で実行する。結果はモデル完了ごとに flush し、失敗原因は runner の JSON / Markdown report に分類して残す。

Default posture は conservative にする。CI や通常開発では offline fake / mock で検証し、real provider は operator が明示的に provider、model、credential を設定した場合だけ使う。

2026-06-03 の DeepSeek reasoning-mode 切り分けでは、通常 artifact / DB / stdout の raw response 非保存は維持しつつ、`--capture-raw-diagnostics` を明示した場合だけ失敗ケースの raw response content を dedicated diagnostic JSON に分離して保存することにした。これは production persistence ではなく eval/probe artifact であり、失敗原因が reasoning content 混入なのか、token budget / schema / format 問題なのかを切るための診断用例外である。

## Alternatives

- **完全直列のままにする**: provider への負荷は低いが、長時間不可視になり、途中失敗の原因把握が遅れるため不採用。
- **最初から全並列にする**: 短時間で終わる可能性はあるが、prompt / schema / provider 設定の系統的な失敗を一気に発生させるため不採用。
- **モデルごとに手元 script を書く**: その場では早いが、比較可能性と原因分類が残らないため不採用。

## Rationale

今回見えた制約は、モデル性能だけでなく evaluation operation の問題でもある。safe batch は provider / schema の大きな崩れを早期に止める役割を持ち、bounded concurrency は問題がない場合の待ち時間を抑える。原因分類は「モデルの性能限界」なのか「runner / provider / schema の問題」なのかを切り分けるために必要である。

## Consequences / Impact

- live evaluation の再現性と可観測性が上がる。
- OpenRouter の rate / latency には引き続き依存する。
- report artifact は増える。通常 artifact と DB には raw response を保存しない。明示 opt-in diagnostic mode の dedicated artifact だけは、失敗ケースの redacted raw content を保存できる。
- active adoption の安全境界は変わらない。

## Quality Implications

- safe batch gate が誤って緩いと、失敗を bounded concurrency へ拡散する。
- gate が誤って厳しいと、性能比較が途中で止まりすぎる。
- failure cause を分類しないと、model quality と infrastructure failure を混同する。

## Intent-derived Invariants

- INV-001: Runner は final digest decision を deterministic のまま維持し、`llm_assisted` adoption を実装しない。
- INV-002: Runner は通常 report / JSON / stdout / DB に raw provider response と secrets を出力しない。明示 opt-in diagnostic artifact は dedicated JSON に分離し、失敗ケースだけの redacted raw content に限定する。
- INV-003: Runner は safe batch を先に完了させてから bounded concurrency へ進む。
- INV-004: Runner はモデル単位の結果を逐次 flush する。
- INV-005: Runner は failure cause を provider / JSON / schema / timeout / orchestration / safety boundary に分類する。
- INV-006: Real provider run は optional であり、CI の必須条件にしない。

## Rollback / Follow-ups

Runner は evaluation artifact であり production runtime を変更しない。問題があれば runner の使用を止め、既存 `_evals/scripts/evaluate_llm_digest_proposals.py` に戻れる。
