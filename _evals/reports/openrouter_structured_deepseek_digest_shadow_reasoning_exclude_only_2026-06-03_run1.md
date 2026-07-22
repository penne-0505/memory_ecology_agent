---
title: Live Digest Model Comparison
status: active
draft_status: n/a
created_at: 2026-06-03
updated_at: 2026-06-03
references:
  - "_docs/intent/Core/llm-digest-live-runner-hardening/decision.md"
  - "_docs/qa/Core/llm-digest-live-runner-hardening/test-plan.md"
  - "_docs/intent/Core/llm-digest-observation-parallelism/decision.md"
  - "_docs/qa/Core/llm-digest-observation-parallelism/test-plan.md"
related_issues: []
related_prs: []
---

# Live Digest Model Comparison

## Runner

- provider: `openrouter`
- safe_batch_size: `3`
- concurrency: `3`
- observation_concurrency: `4`
- fail_fast_on_safe_batch: `False`
- prompt_version: `digest_decision_llm.v3`
- raw_provider_response_persisted: `False`
- structured_output_enabled: `True`
- structured_outputs: `True`
- provider_require_parameters: `True`
- token_parameter: `max_tokens`
- reasoning_effort: ``
- reasoning_exclude: `True`

## Summary

- status_counts: `{'completed': 1}`
- failure_cause_counts: `{'malformed_json': 1, 'schema_validation': 1}`
- validation_failure_aggregate: `[{'loc': 'evidence_quote', 'type': 'string_too_long', 'count': 1}]`

## Results

| Model | Phase | Status | Valid | Fallback | Causes | Elapsed |
| --- | --- | --- | --- | --- | --- | --- |
| `deepseek/deepseek-v4-pro` | `safe_batch` | `completed` | `14` | `2` | `{'malformed_json': 1, 'schema_validation': 1}` | `70.5` |

## Validation Failure Aggregate

| Field / Loc | Type | Count |
| --- | --- | --- |
| `evidence_quote` | `string_too_long` | `1` |

## Observation Partials

| Model | Observation | Status | Schema Valid | Fallback | Cause | Elapsed |
| --- | --- | --- | --- | --- | --- | --- |
| `deepseek/deepseek-v4-pro` | `1` | `completed` | `True` | `False` | `` | `11.4` |
| `deepseek/deepseek-v4-pro` | `5` | `completed` | `True` | `False` | `` | `3.3` |
| `deepseek/deepseek-v4-pro` | `3` | `completed` | `True` | `False` | `` | `17.1` |
| `deepseek/deepseek-v4-pro` | `2` | `completed` | `True` | `False` | `` | `17.3` |
| `deepseek/deepseek-v4-pro` | `8` | `completed` | `True` | `False` | `` | `2.2` |
| `deepseek/deepseek-v4-pro` | `4` | `completed` | `True` | `False` | `` | `20.7` |
| `deepseek/deepseek-v4-pro` | `10` | `completed` | `True` | `False` | `` | `1.8` |
| `deepseek/deepseek-v4-pro` | `11` | `completed` | `True` | `False` | `` | `1.9` |
| `deepseek/deepseek-v4-pro` | `12` | `completed` | `True` | `False` | `` | `1.8` |
| `deepseek/deepseek-v4-pro` | `6` | `completed` | `True` | `False` | `` | `17.9` |
| `deepseek/deepseek-v4-pro` | `7` | `completed` | `True` | `False` | `` | `15.6` |
| `deepseek/deepseek-v4-pro` | `9` | `completed` | `True` | `False` | `` | `16.6` |
| `deepseek/deepseek-v4-pro` | `14` | `completed` | `True` | `False` | `` | `15.7` |
| `deepseek/deepseek-v4-pro` | `13` | `completed` | `True` | `False` | `` | `28.0` |
| `deepseek/deepseek-v4-pro` | `16` | `failed` | `False` | `True` | `schema_validation` | `19.6` |
| `deepseek/deepseek-v4-pro` | `15` | `failed` | `False` | `True` | `malformed_json` | `37.7` |

## Safety

- Raw provider response text is not included.
- Credential values are not printed.
- Evaluation uses isolated temp roots and `llm_shadow` proposal records.
- Final digest decisions remain deterministic.
- Web search is disabled in evaluation settings.
- Discord settings remain disabled.
