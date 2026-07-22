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
- safe_batch_size: `1`
- concurrency: `1`
- observation_concurrency: `4`
- max_observations: `16`
- fail_fast_on_safe_batch: `True`
- prompt_version: `digest_decision_llm.v3`
- raw_provider_response_persisted: `False`
- structured_output_enabled: `True`
- structured_outputs: `True`
- provider_require_parameters: `True`
- token_parameter: `max_tokens`
- reasoning_effort: `minimal`
- reasoning_exclude: `True`

## Summary

- status_counts: `{'completed': 1}`
- failure_cause_counts: `{}`
- validation_failure_aggregate: `[]`

## Results

| Model | Phase | Status | Valid | Fallback | Causes | Elapsed |
| --- | --- | --- | --- | --- | --- | --- |
| `deepseek/deepseek-v4-pro` | `safe_batch` | `completed` | `16` | `0` | `{}` | `105.8` |

## Validation Failure Aggregate

| Field / Loc | Type | Count |
| --- | --- | --- |

## Observation Partials

| Model | Observation | Status | Schema Valid | Fallback | Cause | Elapsed |
| --- | --- | --- | --- | --- | --- | --- |
| `deepseek/deepseek-v4-pro` | `1` | `completed` | `True` | `False` | `` | `8.7` |
| `deepseek/deepseek-v4-pro` | `3` | `completed` | `True` | `False` | `` | `16.4` |
| `deepseek/deepseek-v4-pro` | `4` | `completed` | `True` | `False` | `` | `17.8` |
| `deepseek/deepseek-v4-pro` | `5` | `completed` | `True` | `False` | `` | `13.5` |
| `deepseek/deepseek-v4-pro` | `2` | `completed` | `True` | `False` | `` | `30.9` |
| `deepseek/deepseek-v4-pro` | `8` | `completed` | `True` | `False` | `` | `12.5` |
| `deepseek/deepseek-v4-pro` | `6` | `completed` | `True` | `False` | `` | `25.7` |
| `deepseek/deepseek-v4-pro` | `7` | `completed` | `True` | `False` | `` | `24.9` |
| `deepseek/deepseek-v4-pro` | `9` | `completed` | `True` | `False` | `` | `17.2` |
| `deepseek/deepseek-v4-pro` | `10` | `completed` | `True` | `False` | `` | `14.1` |
| `deepseek/deepseek-v4-pro` | `12` | `completed` | `True` | `False` | `` | `10.2` |
| `deepseek/deepseek-v4-pro` | `13` | `completed` | `True` | `False` | `` | `9.1` |
| `deepseek/deepseek-v4-pro` | `11` | `completed` | `True` | `False` | `` | `26.2` |
| `deepseek/deepseek-v4-pro` | `16` | `completed` | `True` | `False` | `` | `14.9` |
| `deepseek/deepseek-v4-pro` | `14` | `completed` | `True` | `False` | `` | `33.3` |
| `deepseek/deepseek-v4-pro` | `15` | `completed` | `True` | `False` | `` | `52.8` |

## Safety

- Raw provider response text is not included.
- Credential values are not printed.
- Evaluation uses isolated temp roots and `llm_shadow` proposal records.
- Final digest decisions remain deterministic.
- Web search is disabled in evaluation settings.
- Discord settings remain disabled.
