---
title: LLM Digest Live Runner Hardening Plan
status: active
draft_status: n/a
created_at: 2026-06-02
updated_at: 2026-06-03
references:
  - "_docs/intent/Core/llm-digest-live-runner-hardening/decision.md"
  - "_docs/qa/Core/llm-digest-live-runner-hardening/test-plan.md"
  - "_docs/intent/Core/llm-digest-proposal-quality-evaluation/decision.md"
  - "_evals/scripts/evaluate_llm_digest_proposals.py"
related_issues: []
related_prs: []
---

## Overview

Live OpenRouter digest proposal evaluation を、単発の手元 script から再利用可能な runner にする。runner は複数モデルを扱い、最初は小さい safe batch で provider / schema の異常を確認し、問題がなければ bounded concurrency で残りを回す。

## Scope

- 複数モデル指定の live `llm_shadow` evaluation runner を `_evals/scripts/` に追加する。
- sample world fixture、isolated temp root、deterministic final decision、no Web search を維持する。
- モデル単位で結果を逐次 JSON / Markdown に flush する。
- provider / JSON decode / schema validation / timeout / orchestration failure を原因分類する。
- 明示 opt-in の `--capture-raw-diagnostics` では、失敗ケースの redacted raw response content だけを dedicated diagnostic JSON に分離して保存する。
- CI では fake client / dry planning を使い、real provider を必須にしない。

## Non-Goals

- `llm_assisted` adoption を実装しない。
- production / DB / 通常 evidence artifact に raw provider response を保存しない。
- diagnostic opt-in なしで raw provider response を保存しない。
- provider credential を docs、report、stdout に出力しない。
- full benchmark infrastructure や scheduler integration は作らない。

## Requirements

- **Functional**: `--models` で複数モデルを受け取り、各モデルの evaluation metrics を出力できる。
- **Functional**: `--safe-batch-size` 件を先に実行し、失敗がなければ `--concurrency` の bounded concurrency へ進む。
- **Functional**: `--fail-fast-on-safe-batch` を有効にすると、safe batch で重大失敗が出た場合に残りを skipped として記録する。
- **Functional**: 結果はモデル完了ごとに output JSON / report Markdown へ flush される。
- **Functional**: failure causes は provider_error / malformed_json / schema_validation / timeout / orchestration_error / safety_boundary のように分類される。
- **Functional**: `--capture-raw-diagnostics` を明示した場合だけ、失敗 raw response content を通常 artifact とは別の `.raw-diagnostic.json` に flush する。
- **Non-Functional**: 通常 artifact / stdout / DB には raw provider response と secrets を出力・保存しない。
- **Non-Functional**: raw diagnostic artifact は production persistence ではなく eval/probe 用であり、DB raw persistence を有効化しない。
- **Non-Functional**: evaluation runner は runtime default と final digest decision を変更しない。

## Tasks

- Runner の orchestration API を設計する。
- 既存 `_metrics()` と sample world preparation を再利用する。
- threaded bounded concurrency を実装する。
- safe batch gate と skipped result を実装する。
- failure cause summary を追加する。
- unit / integration style tests を追加する。
- verification と report を更新する。

## QA Plan

- QA document: `_docs/qa/Core/llm-digest-live-runner-hardening/test-plan.md`
- Risk level: Medium
- Test strategy:
  - Unit: failure cause classification and safe batch planning.
  - Integration/offline: fake client による multi-model runner smoke。
  - Validator: `./scripts/check-docs.sh`。
  - Diff review: raw provider response、secret、runtime adoption がないことを確認する。

## Deployment / Rollout

Production rollout はない。live provider run は operator が明示 credential と model list を与えたときのみ実行する。新 runner の初期推奨は `--safe-batch-size 3 --concurrency 3 --fail-fast-on-safe-batch` とする。
