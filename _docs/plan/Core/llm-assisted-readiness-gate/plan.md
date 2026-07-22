---
title: "Plan: LLM Assisted Readiness Gate"
status: active
draft_status: n/a
created_at: 2026-06-03
updated_at: 2026-06-03
references:
  - "_docs/intent/Core/llm-assisted-readiness-gate/decision.md"
  - "_docs/qa/Core/llm-assisted-readiness-gate/test-plan.md"
related_issues: []
related_prs: []
---

## Overview

Define a readiness gate for limited `llm_assisted` consideration using qwen shadow evidence, including the structured-output / `related_concern_ids` prompt-hardening evidence from 2026-06-03.

The gate is intentionally a design-readiness gate, not an implementation gate. Passing it may authorize a future limited assisted-mode design task; it does not authorize changing production final digest decisions in this task. As of the follow-up evidence collection, three same-condition prompt-hardened qwen structured runs are clean.

## Scope

- Review repeated qwen shadow evidence from `Core-Test-17`.
- Review OpenRouter structured-output evidence from `_docs/qa/Core/openrouter-structured-digest-proposals/verification.md`.
- Collect and evaluate two additional same-condition qwen structured shadow runs when the gate is `RETURN_TO_EVIDENCE` due only to sample size.
- Define go / no-go / return-to-evidence criteria for limited assisted-mode design.
- Identify when to return to prompt/schema hardening versus additional shadow evidence.

## Non-Goals

- Implementing `llm_assisted`.
- Changing production final digest decision behavior.
- Changing `AGENT_DIGEST_DECIDER` default.
- Changing Discord or Web search behavior.
- Relaxing the Pydantic validation gate.
- Persisting raw provider responses.
- Treating one live run as sufficient evidence.
- Implementing or enabling `llm_assisted` based on the evidence collection itself.

## Requirements

- **Functional**: The gate covers schema adherence, fallback frequency, action-candidate behavior, `should_apply` conservatism, safety boundaries, and run-to-run variance.
- **Non-Functional**: The gate must be conservative, evidence-backed, and explicit about structured-output evidence being a readiness prerequisite rather than adoption proof.

## Tasks

- Read `Core-Test-17` verification and qwen artifacts.
- Read OpenRouter structured-output verification and the current prompt-hardened qwen artifact.
- Run two additional qwen structured shadow evaluations under the same OpenRouter conditions.
- Draft readiness and non-readiness criteria.
- Decide whether the current state permits limited assisted design, prompt/schema hardening, or more shadow collection.
- Record the decision in intent and verification.

## QA Plan

- QA document: `_docs/qa/Core/llm-assisted-readiness-gate/test-plan.md`
- Risk level: Medium
- Test strategy:
  - Document review: confirm go / no-go / return-to-evidence criteria cover all required axes.
  - Diff review: confirm no active adoption, runtime default, provider safety, Discord, Web search, Pydantic, or raw-response boundary changes.
  - Validator / static check: `./scripts/check-docs.sh`

## Deployment / Rollout

No production rollout. This is a decision gate only.
