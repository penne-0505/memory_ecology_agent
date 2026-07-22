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

## Summary

- status_counts: `{'completed': 1}`
- failure_cause_counts: `{'schema_validation': 5}`

## Results

| Model | Phase | Status | Valid | Fallback | Causes | Elapsed |
| --- | --- | --- | --- | --- | --- | --- |
| `qwen/qwen3.6-plus` | `safe_batch` | `completed` | `11` | `5` | `{'schema_validation': 5}` | `129.1` |

## Observation Partials

| Model | Observation | Status | Schema Valid | Fallback | Cause | Elapsed |
| --- | --- | --- | --- | --- | --- | --- |
| `qwen/qwen3.6-plus` | `3` | `completed` | `True` | `False` | `` | `19.5` |
| `qwen/qwen3.6-plus` | `1` | `failed` | `False` | `True` | `schema_validation` | `27.8` |
| `qwen/qwen3.6-plus` | `2` | `completed` | `True` | `False` | `` | `29.9` |
| `qwen/qwen3.6-plus` | `4` | `completed` | `True` | `False` | `` | `31.3` |
| `qwen/qwen3.6-plus` | `5` | `completed` | `True` | `False` | `` | `22.6` |
| `qwen/qwen3.6-plus` | `6` | `completed` | `True` | `False` | `` | `25.3` |
| `qwen/qwen3.6-plus` | `7` | `completed` | `True` | `False` | `` | `27.5` |
| `qwen/qwen3.6-plus` | `8` | `failed` | `False` | `True` | `schema_validation` | `30.3` |
| `qwen/qwen3.6-plus` | `9` | `completed` | `True` | `False` | `` | `23.8` |
| `qwen/qwen3.6-plus` | `10` | `completed` | `True` | `False` | `` | `23.2` |
| `qwen/qwen3.6-plus` | `11` | `completed` | `True` | `False` | `` | `20.5` |
| `qwen/qwen3.6-plus` | `12` | `failed` | `False` | `True` | `schema_validation` | `23.6` |
| `qwen/qwen3.6-plus` | `15` | `failed` | `False` | `True` | `schema_validation` | `15.1` |
| `qwen/qwen3.6-plus` | `13` | `failed` | `False` | `True` | `schema_validation` | `29.2` |
| `qwen/qwen3.6-plus` | `14` | `completed` | `True` | `False` | `` | `28.6` |
| `qwen/qwen3.6-plus` | `16` | `completed` | `True` | `False` | `` | `43.8` |

## Safety

- Raw provider response text is not included.
- Credential values are not printed.
- Evaluation uses isolated temp roots and `llm_shadow` proposal records.
- Final digest decisions remain deterministic.
- Web search is disabled in evaluation settings.
- Discord settings remain disabled.
