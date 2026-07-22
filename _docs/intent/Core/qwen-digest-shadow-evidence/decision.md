---
title: "Qwen Digest Shadow Evidence Decision"
status: active
draft_status: n/a
created_at: 2026-06-03
updated_at: 2026-06-03
references:
  - "_docs/plan/Core/qwen-digest-shadow-evidence/plan.md"
  - "_docs/qa/Core/qwen-digest-shadow-evidence/test-plan.md"
  - "_docs/qa/Core/deepseek-digest-primary-candidate/verification.md"
  - "_evals/reports/live_digest_model_comparison_qwen_kimi_2026-06-02.md"
  - "_evals/reports/live_digest_model_comparison_qwen_observation_parallel_2026-06-03.md"
related_issues: []
related_prs: []
---

## Context

The initial digest proposal quality evaluation completed with a `PARTIAL` verdict: shadow evaluation is implemented and useful, but `llm_assisted` readiness is unproven. Later live comparison showed qwen as the best available model among qwen, v4pro, and kimi at that point, and later structured-output prompt hardening produced three clean qwen runs. DeepSeek has since passed the primary-candidate gate with reasoning disabled, so qwen's current role is verified fallback/baseline.

## Decision

Treat `qwen/qwen3.6-plus` as the verified fallback/baseline live digest shadow evaluation model. Future default live evaluation uses DeepSeek, while qwen remains the comparison target when checking regressions or provider-specific drift.

## Alternatives

- **Move directly to `llm_assisted`**: rejected because schema validity and run-to-run stability are not proven.
- **Keep qwen as primary after DeepSeek gate**: rejected because DeepSeek produced three clean structured shadow runs under a documented reasoning-disabled payload.
- **Only harden prompts immediately**: deferred until repeated qwen evidence clarifies whether failures are stable enough to target.

## Rationale

qwen can run cleanly under the structured-output gate and remains valuable as a verified comparison baseline. Its role changes because DeepSeek now has current primary-candidate evidence under the same schema/fallback/provider gate.

## Consequences / Impact

- Fallback/baseline live evaluation cost remains explicit and optional.
- The evidence base stays comparable after the primary-candidate switch.
- Production runtime remains unchanged.

## Quality Implications

- The evaluation must not confuse shadow proposals with applied decisions.
- Reported model failures must distinguish provider/config absence from model quality.
- Raw provider responses and secrets must not be persisted.

## Intent-derived Invariants

- INV-001: Final digest decisions remain deterministic.
- INV-002: `llm_assisted` is not implemented or enabled.
- INV-003: Live provider use is optional and explicitly configured.
- INV-004: Raw provider responses and secrets are not stored or printed.
- INV-005: Run-to-run variance is treated as evidence, not noise to smooth away.

## Rollback / Follow-ups

If qwen fallback/baseline evidence regresses, follow up with prompt/schema hardening rather than assisted adoption. If DeepSeek primary evidence regresses, compare against this qwen baseline before changing production behavior.
