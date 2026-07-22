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
- recommendation: `NO_FULL_RUN_MINIMAL_ONLY_MODE_C`

## Matrix

| Mode | Schema | Status | HTTP | Parse | Require Parameters | Structured Outputs | Strict | Error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `A` | `minimal` | `provider_error` | `404` | `` | `True` | `None` | `True` | `code=404 message=No endpoints found that can handle the requested parameters. To learn more about provider routing, visit: https://openrouter.ai/docs/guides/routing/provider-selection` |
| `A-strict-false` | `minimal` | `provider_error` | `404` | `` | `True` | `None` | `False` | `code=404 message=No endpoints found that can handle the requested parameters. To learn more about provider routing, visit: https://openrouter.ai/docs/guides/routing/provider-selection` |
| `B` | `minimal` | `provider_error` | `404` | `` | `True` | `True` | `True` | `code=404 message=No endpoints found that can handle the requested parameters. To learn more about provider routing, visit: https://openrouter.ai/docs/guides/routing/provider-selection` |
| `B-strict-false` | `minimal` | `provider_error` | `404` | `` | `True` | `True` | `False` | `code=404 message=No endpoints found that can handle the requested parameters. To learn more about provider routing, visit: https://openrouter.ai/docs/guides/routing/provider-selection` |
| `C` | `minimal` | `success` | `200` | `valid_json_object` | `False` | `True` | `True` | `` |
| `C-strict-false` | `minimal` | `success` | `200` | `valid_json_object` | `False` | `True` | `False` | `` |
| `D` | `minimal` | `provider_error` | `404` | `` | `True` | `None` | `None` | `code=404 message=No endpoints found that can handle the requested parameters. To learn more about provider routing, visit: https://openrouter.ai/docs/guides/routing/provider-selection` |
| `E` | `minimal` | `provider_error` | `404` | `` | `True` | `True` | `None` | `code=404 message=No endpoints found that can handle the requested parameters. To learn more about provider routing, visit: https://openrouter.ai/docs/guides/routing/provider-selection` |
| `F` | `minimal` | `success` | `200` | `valid_json_object` | `None` | `None` | `True` | `` |
| `F-strict-false` | `minimal` | `success` | `200` | `valid_json_object` | `None` | `None` | `False` | `` |
| `C` | `llm_digest_proposal` | `success` | `200` | `missing_expected_keys` | `False` | `True` | `True` | `` |
| `C-strict-false` | `llm_digest_proposal` | `success` | `200` | `missing_expected_keys` | `False` | `True` | `False` | `` |
| `F` | `llm_digest_proposal` | `success` | `200` | `missing_expected_keys` | `None` | `None` | `True` | `` |
| `F-strict-false` | `llm_digest_proposal` | `success` | `200` | `missing_expected_keys` | `None` | `None` | `False` | `` |

## Safety

- Raw provider/model response text is not included.
- Credential values are not printed.
- DB and digest persistence are not used.
