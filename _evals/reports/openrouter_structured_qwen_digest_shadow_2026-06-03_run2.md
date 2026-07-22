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
- provider_require_parameters: `True`

## Summary

- status_counts: `{'completed': 1}`
- failure_cause_counts: `{'provider_error': 16}`

## Results

| Model | Phase | Status | Valid | Fallback | Causes | Elapsed |
| --- | --- | --- | --- | --- | --- | --- |
| `qwen/qwen3.6-plus` | `safe_batch` | `completed` | `0` | `16` | `{'provider_error': 16}` | `1.6` |

## Observation Partials

| Model | Observation | Status | Schema Valid | Fallback | Cause | Elapsed |
| --- | --- | --- | --- | --- | --- | --- |
| `qwen/qwen3.6-plus` | `2` | `failed` | `False` | `True` | `provider_error` | `0.4` |
| `qwen/qwen3.6-plus` | `3` | `failed` | `False` | `True` | `provider_error` | `0.4` |
| `qwen/qwen3.6-plus` | `4` | `failed` | `False` | `True` | `provider_error` | `0.5` |
| `qwen/qwen3.6-plus` | `5` | `failed` | `False` | `True` | `provider_error` | `0.2` |
| `qwen/qwen3.6-plus` | `6` | `failed` | `False` | `True` | `provider_error` | `0.2` |
| `qwen/qwen3.6-plus` | `7` | `failed` | `False` | `True` | `provider_error` | `0.3` |
| `qwen/qwen3.6-plus` | `1` | `failed` | `False` | `True` | `provider_error` | `0.8` |
| `qwen/qwen3.6-plus` | `8` | `failed` | `False` | `True` | `provider_error` | `0.3` |
| `qwen/qwen3.6-plus` | `9` | `failed` | `False` | `True` | `provider_error` | `0.3` |
| `qwen/qwen3.6-plus` | `10` | `failed` | `False` | `True` | `provider_error` | `0.3` |
| `qwen/qwen3.6-plus` | `11` | `failed` | `False` | `True` | `provider_error` | `0.3` |
| `qwen/qwen3.6-plus` | `12` | `failed` | `False` | `True` | `provider_error` | `0.4` |
| `qwen/qwen3.6-plus` | `13` | `failed` | `False` | `True` | `provider_error` | `0.4` |
| `qwen/qwen3.6-plus` | `14` | `failed` | `False` | `True` | `provider_error` | `0.3` |
| `qwen/qwen3.6-plus` | `15` | `failed` | `False` | `True` | `provider_error` | `0.3` |
| `qwen/qwen3.6-plus` | `16` | `failed` | `False` | `True` | `provider_error` | `0.3` |

## Safety

- Raw provider response text is not included.
- Credential values are not printed.
- Evaluation uses isolated temp roots and `llm_shadow` proposal records.
- Final digest decisions remain deterministic.
- Web search is disabled in evaluation settings.
- Discord settings remain disabled.
