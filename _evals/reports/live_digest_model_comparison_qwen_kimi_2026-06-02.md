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
- safe_batch_size: `0`
- concurrency: `2`
- fail_fast_on_safe_batch: `False`
- prompt_version: `digest_decision_llm.v3`
- raw_provider_response_persisted: `False`

## Summary

- status_counts: `{'completed': 2}`
- failure_cause_counts: `{'malformed_json': 14, 'schema_validation': 2}`

## Results

| Model | Phase | Status | Valid | Fallback | Causes | Elapsed |
| --- | --- | --- | --- | --- | --- | --- |
| `qwen/qwen3.6-plus` | `bounded` | `completed` | `14` | `2` | `{'schema_validation': 2}` | `397.3` |
| `moonshotai/kimi-k2.6` | `bounded` | `completed` | `2` | `14` | `{'malformed_json': 14}` | `652.8` |

## Safety

- Raw provider response text is not included.
- Credential values are not printed.
- Evaluation uses isolated temp roots and `llm_shadow` proposal records.
- Final digest decisions remain deterministic.
- Web search is disabled in evaluation settings.
- Discord settings remain disabled.
