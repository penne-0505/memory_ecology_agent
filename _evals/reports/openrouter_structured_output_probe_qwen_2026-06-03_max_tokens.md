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
- recommendation: `NO_FULL_RUN_MINIMAL_ONLY_MODE_A`

## Matrix

| Mode | Schema | Status | HTTP | Parse | Require Parameters | Structured Outputs | Strict | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `A` | `minimal` | `success` | `200` | `valid_json_object` | `True` | `None` | `True` | `` |
| `A-strict-false` | `minimal` | `success` | `200` | `valid_json_object` | `True` | `None` | `False` | `` |
| `B` | `minimal` | `success` | `200` | `valid_json_object` | `True` | `True` | `True` | `` |
| `B-strict-false` | `minimal` | `success` | `200` | `valid_json_object` | `True` | `True` | `False` | `` |
| `C` | `minimal` | `success` | `200` | `valid_json_object` | `False` | `True` | `True` | `` |
| `C-strict-false` | `minimal` | `success` | `200` | `valid_json_object` | `False` | `True` | `False` | `` |
| `D` | `minimal` | `success` | `200` | `valid_json_object` | `True` | `None` | `None` | `` |
| `E` | `minimal` | `success` | `200` | `valid_json_object` | `True` | `True` | `None` | `` |
| `F` | `minimal` | `success` | `200` | `valid_json_object` | `None` | `None` | `True` | `` |
| `F-strict-false` | `minimal` | `success` | `200` | `valid_json_object` | `None` | `None` | `False` | `` |
| `A` | `llm_digest_proposal` | `success` | `200` | `missing_expected_keys` | `True` | `None` | `True` | `` |
| `A-strict-false` | `llm_digest_proposal` | `success` | `200` | `missing_expected_keys` | `True` | `None` | `False` | `` |
| `B` | `llm_digest_proposal` | `success` | `200` | `missing_expected_keys` | `True` | `True` | `True` | `` |
| `B-strict-false` | `llm_digest_proposal` | `success` | `200` | `missing_expected_keys` | `True` | `True` | `False` | `` |
| `C` | `llm_digest_proposal` | `success` | `200` | `missing_expected_keys` | `False` | `True` | `True` | `` |
| `C-strict-false` | `llm_digest_proposal` | `success` | `200` | `missing_expected_keys` | `False` | `True` | `False` | `` |
| `D` | `llm_digest_proposal` | `success` | `200` | `missing_expected_keys` | `True` | `None` | `None` | `` |
| `E` | `llm_digest_proposal` | `success` | `200` | `missing_expected_keys` | `True` | `True` | `None` | `` |
| `F` | `llm_digest_proposal` | `success` | `200` | `missing_expected_keys` | `None` | `None` | `True` | `` |
| `F-strict-false` | `llm_digest_proposal` | `success` | `200` | `missing_expected_keys` | `None` | `None` | `False` | `` |

## Safety

- Raw provider/model response text is not included.
- Credential values are not printed.
- DB and digest persistence are not used.
