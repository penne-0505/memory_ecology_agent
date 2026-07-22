---
title: "Plan: Qwen Digest Shadow Evidence"
status: active
draft_status: n/a
created_at: 2026-06-03
updated_at: 2026-06-03
references:
  - "_docs/intent/Core/qwen-digest-shadow-evidence/decision.md"
  - "_docs/qa/Core/qwen-digest-shadow-evidence/test-plan.md"
  - "_docs/qa/Core/llm-digest-proposal-quality-evaluation/verification.md"
  - "_docs/qa/Core/llm-digest-observation-parallelism/verification.md"
  - "_docs/qa/Core/deepseek-digest-primary-candidate/verification.md"
related_issues: []
related_prs: []
---

## Overview

Use `qwen/qwen3.6-plus` as a verified fallback/baseline for live digest shadow evaluation after the DeepSeek primary-candidate switch. This is evaluation evidence, not an active adoption task.

## Scope

- Run qwen live `llm_shadow` evaluation in isolated temp roots when fallback/baseline comparison is needed.
- Keep `AGENT_MAX_WEB_QUERIES=0`, Discord disabled, and final digest decisions deterministic.
- Record run-to-run metrics for schema validity, fallback, malformed JSON, validation error, agreement/disagreement, `action_candidate`, and `should_apply`.
- Summarize qualitative disagreement examples where qwen appears better than deterministic, deterministic appears safer, or the case is unclear.

## Non-Goals

- Implementing or enabling `llm_assisted`.
- Changing production runtime defaults.
- Comparing every available model again.
- Persisting raw provider responses.

## Requirements

- **Functional**: The evaluation produces comparable JSON / Markdown artifacts across multiple qwen runs.
- **Functional**: Missing credential or explicit provider/model config is recorded as `SKIPPED_REAL_PROVIDER`, not as model failure.
- **Non-Functional**: Evaluation remains bounded, traceable, and secret-safe.

## Tasks

- Decide the run count and output naming convention.
- Run qwen fallback/baseline live evaluation with observation-level partial flush.
- Aggregate metrics and variance across runs.
- Update QA verification with recommendation: continue shadow, harden prompt/schema, or proceed to readiness-gate review.

## QA Plan

- QA document: `_docs/qa/Core/qwen-digest-shadow-evidence/test-plan.md`
- Risk level: Medium
- Test strategy:
  - Unit: reuse runner tests for qwen default and partial flush.
  - Integration: run or inspect qwen evaluation artifacts.
  - Manual QA: credentialed OpenRouter run only when explicitly configured.
  - Validator / static check: `./scripts/check-docs.sh`.

## Deployment / Rollout

No production rollout. The output is evaluation evidence under `_evals/reports/` and QA verification under `_docs/qa/Core/qwen-digest-shadow-evidence/verification.md`.
