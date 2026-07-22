---
title: "Plan: DeepSeek Digest Primary Candidate"
status: active
draft_status: n/a
created_at: 2026-06-03
updated_at: 2026-06-03
references:
  - "_docs/intent/Core/deepseek-digest-primary-candidate/decision.md"
  - "_docs/qa/Core/deepseek-digest-primary-candidate/test-plan.md"
  - "_docs/qa/Core/deepseek-digest-primary-candidate/verification.md"
  - "_docs/intent/Core/openrouter-structured-digest-proposals/decision.md"
  - "_docs/qa/Core/openrouter-structured-digest-proposals/verification.md"
  - "_docs/intent/Core/qwen-digest-shadow-evidence/decision.md"
related_issues: []
related_prs: []
---

## Overview

Evaluate `deepseek/deepseek-v4-pro` as the digest proposal primary candidate for live shadow evaluation. The evaluation reuses the same OpenRouter structured-output gate that produced clean qwen evidence.

## Scope

- Check OpenRouter model metadata for DeepSeek supported parameters.
- Run one DeepSeek OpenRouter structured digest shadow evaluation with the qwen clean-run payload shape.
- If the first run is clean, run two additional same-condition DeepSeek shadow evaluations.
- If all three runs are clean, switch the live evaluation runner primary candidate/default to DeepSeek.
- Record qwen as verified fallback/baseline if DeepSeek becomes primary.

## Non-Goals

- Do not implement or enable `llm_assisted`.
- Do not change production final digest decisions.
- Do not change the `AGENT_DIGEST_DECIDER` default.
- Do not change Discord, Web search, Pydantic validation, or raw response persistence behavior.
- Do not store raw model responses.

## Requirements

- **Functional**: DeepSeek run artifacts use `max_tokens`, `response_format=json_schema`, `structured_outputs=true`, and `provider.require_parameters=true` unless supported-parameter evidence requires a narrower adjustment.
- **Functional**: Additional two runs are executed only when run1 is clean.
- **Functional**: Primary candidate/default is switched only after three clean runs.
- **Safety**: Raw provider response text and credential values are not persisted or printed.
- **Safety**: Pydantic validation remains the final proposal acceptance gate.

## Tasks

- Create TODO / plan / intent / QA records for the evaluation.
- Inspect OpenRouter model metadata for DeepSeek and qwen comparison.
- Run DeepSeek structured shadow artifacts under isolated temp roots with Web search disabled.
- Update runner/docs only if the 3-run gate passes.
- Run focused tests and docs validation.
- Create verification with GO / RETURN_TO_EVIDENCE / RETURN_TO_HARDENING / NO_GO gate result.

## QA Plan

- QA document: `_docs/qa/Core/deepseek-digest-primary-candidate/test-plan.md`
- Risk level: Medium
- Test strategy:
  - Live QA: one to three OpenRouter structured shadow runs.
  - Artifact review: metrics, payload metadata, validation aggregate, raw-response persistence flag.
  - Diff review: production/default/assisted path boundaries.
  - Automated tests: focused runner/digest tests and docs validator.

## Deployment / Rollout

There is no production rollout. If the gate passes, the evaluation runner default model changes to DeepSeek for future live evaluation only. Production final digest behavior remains deterministic by default.
