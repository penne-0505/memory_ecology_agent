---
title: "QA Verification: LLM Digest Decision Proposals"
status: active
draft_status: n/a
qa_status: verified
risk: High
created_at: 2026-06-02
updated_at: 2026-06-02
references:
  - "_docs/intent/Core/llm-digest-decision-proposals/decision.md"
  - "_docs/plan/Core/llm-digest-decision-proposals/plan.md"
  - "_docs/qa/Core/llm-digest-decision-proposals/test-plan.md"
related_issues: []
related_prs: []
---

# QA Verification: `LLM Digest Decision Proposals`

## Summary

LLM-backed digest decision proposals を feature flag 配下に追加し、default deterministic、llm_shadow persistence、agreement / disagreement trace、fallback、secret 非保存、downstream deterministic mutation 境界を offline tests で検証した。

## Verification Verdict

Verdict: PASS

Offline tests、docs check、existing PoC verification script、temp-root deterministic smoke、mock-provider llm_shadow fallback smoke は PASS。OpenRouter / `deepseek/deepseek-v4-pro` live smoke は real credentials を明示していないため SKIPPED。

## Commands Run

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_digest_decider.py
```

Result:

```text
5 passed in 0.22s
```

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_observation_extractor.py tests/test_wake_cycle.py tests/test_closed_loop_hardening.py
```

Result:

```text
15 passed in 0.37s
```

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest
```

Result:

```text
71 passed, 1 warning in 1.26s
```

```bash
./scripts/check-docs.sh
```

Result:

```text
PASS todo and QA validators.
```

```bash
uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/verify_memory_ecology_poc.py --output /tmp/memory_ecology_llm_digest_check.json
```

Result:

```text
PASS: command exited 0. Report confirmed core_profile content unchanged, digest_decisions=44, core_profiles=1.
```

```bash
tmpdir="$(mktemp -d)"
uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root "$tmpdir" init
uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root "$tmpdir" seed
uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root "$tmpdir" wake --reason deterministic-digest-check
uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root "$tmpdir" inspect digest-decisions
```

Result:

```text
PASS: 3 digest decisions printed. Each metadata block had digest_decider=deterministic and no proposal id.
```

```bash
tmpdir="$(mktemp -d)"
uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root "$tmpdir" init
uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root "$tmpdir" seed
AGENT_DIGEST_DECIDER=llm_shadow AGENT_LLM_PROVIDER=mock uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root "$tmpdir" wake --reason llm-shadow-mock-fallback-check
uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root "$tmpdir" inspect digest-decisions
uv run --python /home/penne/.local/bin/python3.12 python -m app.main --project-root "$tmpdir" inspect digest-proposals
```

Result:

```text
PASS: 3 final digest decisions printed and 3 rejected digest proposals printed. Mock provider fallback used JSONDecodeError while final decisions remained deterministic.
```

## Automated Test Results

| Command / Test | Result | Notes |
| --- | --- | --- |
| `pytest tests/test_digest_decider.py` | PASS | New digest proposal behavior passed. |
| `pytest tests/test_observation_extractor.py tests/test_wake_cycle.py tests/test_closed_loop_hardening.py` | PASS | Neighboring cognition paths passed. |
| `pytest` | PASS | Full offline pytest passed with one third-party deprecation warning. |
| `./scripts/check-docs.sh` | PASS | TODO and QA validators passed after verification file was added. |
| `_evals/scripts/verify_memory_ecology_poc.py` | PASS | Existing PoC verification completed and core profile stayed unchanged. |
| Temp-root deterministic smoke | PASS | Digest decisions inspected with deterministic decider metadata. |
| Mock-provider llm_shadow smoke | PASS | Rejected proposal fallback trace inspected; final decisions continued. |

## Manual QA Results

| Checklist Item | Result | Notes |
| --- | --- | --- |
| Temp-root deterministic wake and inspect | PASS | `digest_decider=deterministic` and no proposal rows implied by absent proposal metadata. |
| Fake-provider llm_shadow wake and inspect | PASS | CLI mock provider produced rejected proposals and deterministic final decisions. Valid fake proposal is covered by pytest. |
| Optional OpenRouter v4pro smoke | SKIPPED | No explicit live credential request in this task. |

## Acceptance Criteria Coverage

| ID | Result | Evidence |
| --- | --- | --- |
| AC-001 | PASS | Default wake creates no proposal rows and provider factory is not called. |
| AC-002 | PASS | `llm_shadow` stores proposal row and final metadata references it. |
| AC-003 | PASS | Disagreement test keeps final deterministic decision and downstream concern / memory creation follows final decision. |
| AC-004 | PASS | Invalid JSON, schema-invalid decision, provider error, unknown concern id, and secret-like output are covered. |
| AC-005 | PASS | `inspect digest-decisions` and `inspect digest-proposals` smoke output showed comparison and fallback metadata. |
| AC-006 | PASS | Tests assert raw response is not persisted and secret-like text is absent from persisted safe fields. |
| AC-007 | PASS | README, QUICKSTART, reference, provider docs, Plan / Intent / QA updated; docs check passed. |

## Invariant Coverage

| ID | Result | Evidence |
| --- | --- | --- |
| INV-001 | PASS | Default mode test verifies no provider construction and no proposal rows. |
| INV-002 | PASS | Shadow disagreement test verifies final decision remains deterministic. |
| INV-003 | PASS | Downstream counts and core profile count verify proposal does not directly mutate state. |
| INV-004 | PASS | Rejected proposal rows persist sanitized error class and no raw response. |
| INV-005 | PASS | Metadata and CLI output show proposal id, agreement/fallback, provider/model, and final decision link. |
| INV-006 | PASS | Tests use fake provider only; docs mark live provider as optional manual smoke. |

## Deferred / Not Covered

| ID | Reason | Follow-up |
| --- | --- | --- |
| OpenRouter v4pro live smoke | Real credentials were not explicitly configured for this task. | Run optional manual smoke when credentials are intentionally exported. |

## Residual Risks

None

## Follow-up TODOs

- Evaluate LLM proposal quality over the sample world before implementing active `llm_assisted` adoption.
- Existing SQLite DBs need recreation or manual schema update before using `digest_decision_proposals`; this PoC still uses `create_all` rather than migrations.
