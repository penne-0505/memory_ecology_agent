---
title: OpenRouter Structured Output Probe
status: active
draft_status: n/a
created_at: 2026-06-02
updated_at: 2026-06-02
references:
  - "_docs/qa/Core/openrouter-structured-digest-proposals/verification.md"
related_issues: []
related_prs: []
---

# OpenRouter Structured Output Probe

## Summary

- model: `qwen/qwen3.6-plus`
- raw_response_persisted: `False`
- recommendation: `TARGETED_DIGEST_SCHEMA_DIAGNOSTIC`

## Matrix

| Mode | Schema | Status | HTTP | Parse | Require Parameters | Structured Outputs | Strict | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `A` | `llm_digest_proposal` | `success` | `200` | `missing_expected_keys` | `True` | `None` | `True` | `` |

## Safety

- Raw provider/model response text is not included.
- Credential values are not printed.
- DB and digest persistence are not used.
