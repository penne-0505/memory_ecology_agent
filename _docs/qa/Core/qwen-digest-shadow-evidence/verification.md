---
title: "QA Verification: Qwen Digest Shadow Evidence"
status: active
draft_status: n/a
qa_status: verified
risk: Medium
created_at: 2026-06-03
updated_at: 2026-06-03
references:
  - "_docs/intent/Core/qwen-digest-shadow-evidence/decision.md"
  - "_docs/plan/Core/qwen-digest-shadow-evidence/plan.md"
  - "_docs/qa/Core/qwen-digest-shadow-evidence/test-plan.md"
  - "_docs/qa/Core/deepseek-digest-primary-candidate/verification.md"
  - "_evals/reports/qwen_digest_shadow_evidence_2026-06-03_run1.md"
  - "_evals/reports/qwen_digest_shadow_evidence_2026-06-03_run2.md"
  - "_evals/reports/qwen_digest_shadow_evidence_2026-06-03_run3.md"
related_issues: []
related_prs: []
---

# QA Verification: `Qwen Digest Shadow Evidence`

## Summary

Three credentialed OpenRouter live qwen shadow evaluations were run with `qwen/qwen3.6-plus`, `AGENT_MAX_WEB_QUERIES=0`, isolated temp roots, and observation-level partial flush enabled. This older evidence showed stable malformed-JSON behavior but persistent schema validation failures. Later structured-output prompt hardening produced clean qwen runs, and DeepSeek has now replaced qwen as the primary live evaluation candidate. qwen remains verified fallback/baseline evidence, not active `llm_assisted` implementation evidence.

## Verification Verdict

Verdict: PASS

The evidence accumulation task is complete. It does not prove `llm_assisted` readiness.

## Commands Run

```bash
date +%F
```

Result:

```text
2026-06-03
```

```bash
for i in 1 2 3; do
  AGENT_MAX_WEB_QUERIES=0 AGENT_LLM_PROVIDER=openrouter \
    uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/run_live_digest_model_comparison.py \
      --provider openrouter \
      --model qwen/qwen3.6-plus \
      --observation-concurrency 4 \
      --output-json _evals/reports/qwen_digest_shadow_evidence_2026-06-03_run${i}.json \
      --output-md _evals/reports/qwen_digest_shadow_evidence_2026-06-03_run${i}.md
done
```

Result:

```text
_evals/reports/qwen_digest_shadow_evidence_2026-06-03_run1.json
_evals/reports/qwen_digest_shadow_evidence_2026-06-03_run1.md
_evals/reports/qwen_digest_shadow_evidence_2026-06-03_run2.json
_evals/reports/qwen_digest_shadow_evidence_2026-06-03_run2.md
_evals/reports/qwen_digest_shadow_evidence_2026-06-03_run3.json
_evals/reports/qwen_digest_shadow_evidence_2026-06-03_run3.md
```

```bash
./scripts/check-docs.sh
```

Result:

```text
PASS
```

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_live_digest_runner.py tests/test_digest_decider.py
```

Result:

```text
17 passed
```

## Automated Test Results

| Command / Test | Result | Notes |
| --- | --- | --- |
| `./scripts/check-docs.sh` | PASS | TODO, QA, frontmatter, doc links, and validator fixtures passed. |
| `tests/test_live_digest_runner.py tests/test_digest_decider.py` | PASS | Runner and digest decider regression checks passed. |

## Manual QA Results

| Checklist Item | Result | Notes |
| --- | --- | --- |
| Credential gate | PASS | `OPENROUTER_API_KEY` was present; the secret value was not printed. |
| Live qwen run 1 | PASS | Artifact created with partial flush and sanitized metrics. |
| Live qwen run 2 | PASS | Artifact created with partial flush and sanitized metrics. |
| Live qwen run 3 | PASS | Artifact created with partial flush and sanitized metrics. |
| Raw response / secret non-persistence | PASS | `raw_response_persisted_count=0` in all runs. |

## Evidence Summary

| Metric | Run 1 | Run 2 | Run 3 | Range / Mean |
| --- | --- | --- | --- | --- |
| total elapsed seconds | `126.6` | `113.4` | `129.1` | `113.4-129.1`, mean `123.03` |
| first partial seconds | `24.1` | `23.9` | `19.5` | `19.5-24.1`, mean `22.5` |
| observation partials | `16` | `16` | `16` | stable |
| schema-valid proposals | `12/16` | `10/16` | `11/16` | mean `11/16` |
| fallback proposals | `4/16` | `6/16` | `5/16` | mean `5/16` |
| malformed JSON | `0` | `0` | `0` | stable |
| validation errors | `4` | `6` | `5` | mean `5` |
| provider errors | `0` | `0` | `0` | stable |
| agreement count | `7` | `6` | `6` | mean `6.33` |
| disagreement count | `5` | `4` | `5` | mean `4.67` |
| action_candidate count | `1` | `1` | `1` | stable |
| model should_apply true | `0` | `0` | `0` | stable |
| normalized should_apply true | `1` | `1` | `0` | `0-1` |
| raw response persisted | `0` | `0` | `0` | stable |

## Recommendation

Recommendation: `VERIFIED_FALLBACK_BASELINE_AFTER_DEEPSEEK_SWITCH`.

Qwen is no longer the current primary live evaluation model after the DeepSeek primary-candidate gate. It remains operationally useful as a verified fallback/baseline: no provider errors, partial flush works, and raw provider output is not persisted. This older pre-hardening evidence is not sufficient evidence for active `llm_assisted` adoption.

## Acceptance Criteria Coverage

| ID | Status | Evidence |
| --- | --- | --- |
| AC-001 | PASS | Three qwen live artifacts were created under `_evals/reports/`. |
| AC-002 | PASS | Run-to-run variance table records schema-valid, fallback, malformed JSON, validation error, agreement/disagreement, `action_candidate`, and `should_apply`. |
| AC-003 | PASS | Recommendation is `PROMPT_SCHEMA_HARDENING_BEFORE_ASSISTED`; active adoption is not recommended. |

## Invariant Coverage

| ID | Status | Evidence |
| --- | --- | --- |
| INV-001 | PASS | Runner uses `llm_shadow`; final digest decisions remain deterministic. |
| INV-002 | PASS | `llm_assisted` was not implemented or enabled. |
| INV-003 | PASS | Live provider use was explicit and credential-gated. |
| INV-004 | PASS | Raw provider responses and secrets were not stored or printed. |
| INV-005 | PASS | Run-to-run variance is preserved in the evidence table. |

## Deferred / Not Covered

| ID | Reason | Follow-up |
| --- | --- | --- |
| Assisted readiness | Validation errors are still frequent. | Use `Core-Test-18` to define a conservative gate, likely routing to prompt/schema hardening before adoption. |

## Residual Risks

None

## Follow-up TODOs

- Core-Test-18 remains active in `TODO.md`.
