---
title: Live Digest Model Comparison
status: active
draft_status: n/a
created_at: 2026-06-02
updated_at: 2026-06-02
references:
  - "_docs/intent/Core/llm-digest-live-runner-hardening/decision.md"
  - "_docs/qa/Core/llm-digest-live-runner-hardening/test-plan.md"
related_issues: []
related_prs: []
---

# Live Digest Model Comparison

## Runner

- provider: `openrouter`
- safe_batch_size: `1`
- concurrency: `2`
- fail_fast_on_safe_batch: `True`
- prompt_version: `digest_decision_llm.v3`
- raw_provider_response_persisted: `False`

## Summary

- status_counts: `{'completed': 1, 'skipped': 2}`
- failure_cause_counts: `{'malformed_json': 4, 'safe_batch_gate': 2, 'schema_validation': 1}`

## Results

| Model | Phase | Status | Valid | Fallback | Causes | Elapsed |
| --- | --- | --- | --- | --- | --- | --- |
| `deepseek/deepseek-v4-pro` | `safe_batch` | `completed` | `11` | `5` | `{'malformed_json': 4, 'schema_validation': 1}` | `327.4` |
| `qwen/qwen3.6-plus` | `bounded` | `skipped` | `` | `` | `{'safe_batch_gate': 1}` | `0.0` |
| `moonshotai/kimi-k2.6` | `bounded` | `skipped` | `` | `` | `{'safe_batch_gate': 1}` | `0.0` |

## Safety

- Raw provider response text is not included.
- Credential values are not printed.
- Evaluation uses isolated temp roots and `llm_shadow` proposal records.
- Final digest decisions remain deterministic.
- Web search is disabled in evaluation settings.
- Discord settings remain disabled.
