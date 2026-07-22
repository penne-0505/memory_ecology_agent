---
title: LLM Digest Observation Parallelism Plan
status: active
draft_status: n/a
created_at: 2026-06-03
updated_at: 2026-06-03
references:
  - "_docs/intent/Core/llm-digest-observation-parallelism/decision.md"
  - "_docs/qa/Core/llm-digest-observation-parallelism/test-plan.md"
  - "_docs/intent/Core/llm-digest-live-runner-hardening/decision.md"
  - "_docs/qa/Core/deepseek-digest-primary-candidate/verification.md"
  - "_evals/reports/live_digest_model_comparison_qwen_kimi_2026-06-02.md"
related_issues: []
related_prs: []
---

# LLM Digest Observation Parallelism Plan

## Overview

`_evals/scripts/run_live_digest_model_comparison.py` に、1モデル内の observation-level bounded concurrency と observation partial flush を追加する。current primary live evaluation model は `deepseek/deepseek-v4-pro` とし、`qwen/qwen3.6-plus` は verified fallback/baseline として扱う。

## Scope

- runner の default model または documented command を DeepSeek primary run に寄せる。
- isolated temp root preparation、deterministic baseline / observation collection、observation ごとの LLM proposal generation、proposal rows / metrics aggregation、partial JSON / Markdown flush を分離する。
- `--observation-concurrency` を追加する。
- observation completion ごとに sanitized partial result を output JSON / Markdown に flush する。
- observation-level failure cause を JSON decode / schema validation / provider / timeout / orchestration / safety boundary に分類する。
- runner tests、TODO、QA verification を更新する。

## Non-Goals

- `llm_assisted` を実装しない。
- production runtime、`AGENT_DIGEST_DECIDER` default、final digest decision path を変更しない。
- Discord mode、Web search、provider credential handling を変更しない。
- raw provider response text や secrets を保存・表示しない。
- 新たな3モデル比較を必須にしない。

## Requirements

- `--observation-concurrency 4` のように 1モデル内の bounded parallelism を指定できる。
- observation partial output は raw response text を含めず、model、provider、observation id、elapsed、schema-valid、fallback、failure cause だけを残す。
- aggregate metrics は既存の model-level report と同じ `_metrics()` shape を使い、過去 artifact と比較できる。
- live run は明示 credential がある場合だけ行い、credential がない場合は `SKIPPED_REAL_PROVIDER` として verification に残す。

## Tasks

- Runner の evaluation flow を baseline / proposals / aggregation / partial flush に分ける。
- Observation-level proposal worker を bounded executor で実行する。
- Thread 間で SQLAlchemy session を共有しない。
- Result writer に observation partial list と Markdown section を追加する。
- Tests に observation partial flush、qwen default、failure classification を追加する。
- QA verification に必須検証と live run status を記録する。

## QA Plan

- QA document: `_docs/qa/Core/llm-digest-observation-parallelism/test-plan.md`
- Risk level: Medium
- Required commands:
  - `./scripts/check-docs.sh`
  - `uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_live_digest_runner.py tests/test_digest_decider.py`
  - `uv run --python /home/penne/.local/bin/python3.12 pytest` when feasible
- Manual live command, only when credential is explicitly available:
  - `AGENT_MAX_WEB_QUERIES=0 AGENT_LLM_PROVIDER=openrouter AGENT_OPENROUTER_REASONING_EFFORT=none AGENT_OPENROUTER_REASONING_EXCLUDE=true uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/run_live_digest_model_comparison.py --provider openrouter --model deepseek/deepseek-v4-pro --observation-concurrency 4 --output-json <path> --output-md <path>`

## Deployment / Rollout

Production rollout はない。runner は evaluation-only artifact として使い、DeepSeek primary の single-model live run を標準経路にする。qwen は verified fallback/baseline として明示 model 指定で再実行できる。
