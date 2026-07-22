---
title: Live Digest Model Comparison
status: active
draft_status: n/a
created_at: 2026-06-02
updated_at: 2026-06-02
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

## Summary

- status_counts: `{'completed': 1}`
- failure_cause_counts: `{}`
- validation_failure_aggregate: `[]`

## Results

| Model | Phase | Status | Valid | Fallback | Causes | Elapsed |
| --- | --- | --- | --- | --- | --- | --- |
| `qwen/qwen3.6-plus` | `safe_batch` | `completed` | `16` | `0` | `{}` | `121.5` |

## Validation Failure Aggregate

| Field / Loc | Type | Count |
| --- | --- | --- |

## Observation Partials

| Model | Observation | Status | Schema Valid | Fallback | Cause | Elapsed |
| --- | --- | --- | --- | --- | --- | --- |
| `qwen/qwen3.6-plus` | `3` | `completed` | `True` | `False` | `` | `24.1` |
| `qwen/qwen3.6-plus` | `4` | `completed` | `True` | `False` | `` | `30.4` |
| `qwen/qwen3.6-plus` | `2` | `completed` | `True` | `False` | `` | `31.2` |
| `qwen/qwen3.6-plus` | `1` | `completed` | `True` | `False` | `` | `33.5` |
| `qwen/qwen3.6-plus` | `5` | `completed` | `True` | `False` | `` | `23.6` |
| `qwen/qwen3.6-plus` | `7` | `completed` | `True` | `False` | `` | `20.2` |
| `qwen/qwen3.6-plus` | `6` | `completed` | `True` | `False` | `` | `26.6` |
| `qwen/qwen3.6-plus` | `8` | `completed` | `True` | `False` | `` | `26.4` |
| `qwen/qwen3.6-plus` | `10` | `completed` | `True` | `False` | `` | `18.3` |
| `qwen/qwen3.6-plus` | `9` | `completed` | `True` | `False` | `` | `29.8` |
| `qwen/qwen3.6-plus` | `11` | `completed` | `True` | `False` | `` | `26.0` |
| `qwen/qwen3.6-plus` | `12` | `completed` | `True` | `False` | `` | `30.9` |
| `qwen/qwen3.6-plus` | `15` | `completed` | `True` | `False` | `` | `14.9` |
| `qwen/qwen3.6-plus` | `13` | `completed` | `True` | `False` | `` | `29.1` |
| `qwen/qwen3.6-plus` | `14` | `completed` | `True` | `False` | `` | `26.6` |
| `qwen/qwen3.6-plus` | `16` | `completed` | `True` | `False` | `` | `30.6` |

## Safety

- Raw provider response text is not included.
- Credential values are not printed.
- Evaluation uses isolated temp roots and `llm_shadow` proposal records.
- Final digest decisions remain deterministic.
- Web search is disabled in evaluation settings.
- Discord settings remain disabled.
