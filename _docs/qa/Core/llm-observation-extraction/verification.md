---
title: "QA Verification: LLM Observation Extraction"
status: active
draft_status: n/a
qa_status: verified
risk: Medium
created_at: 2026-06-02
updated_at: 2026-06-02
references:
  - "_docs/intent/Core/llm-observation-extraction/decision.md"
  - "_docs/plan/Core/llm-observation-extraction/plan.md"
  - "_docs/qa/Core/llm-observation-extraction/test-plan.md"
related_issues: []
related_prs: []
---

# QA Verification: `LLM Observation Extraction`

## Summary

LLM-backed observation extraction を feature flag の背後に追加し、default deterministic path、opt-in LLM proposal path、validation/fallback、safe trace metadata、docs 手順を検証した。今回の focused re-verification では、任意 manual QA として OpenRouter / `deepseek/deepseek-v4-pro` の isolated project root smoke も実行した。

## Verification Verdict

Verdict: PASS

## Commands Run

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_observation_extractor.py tests/test_wake_cycle.py tests/test_llm.py
uv run --python /home/penne/.local/bin/python3.12 pytest
./scripts/check-docs.sh
uv run python -m app.main --project-root "$tmpdir" init
uv run python -m app.main --project-root "$tmpdir" seed
AGENT_LLM_PROVIDER=openrouter AGENT_LLM_MODEL=deepseek/deepseek-v4-pro AGENT_OBSERVATION_EXTRACTOR=llm uv run python -m app.main --project-root "$tmpdir" wake --reason llm-observation-v4pro-smoke
uv run python -m app.main --project-root "$tmpdir" inspect observations
uv run python -m app.main --project-root "$tmpdir" inspect digest-decisions
uv run python -m app.main --project-root "$tmpdir" inspect actions
uv run python -m app.main --project-root "$tmpdir" inspect outcomes
```

## Automated Test Results

| Command / Test | Result | Notes |
| --- | --- | --- |
| `uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_observation_extractor.py tests/test_wake_cycle.py tests/test_llm.py` | PASS | 22 passed. |
| `uv run python -m pytest` | PASS | 66 passed, 1 warning from `discord/player.py` using deprecated `audioop`. |
| `./scripts/check-docs.sh` | PASS | Frontmatter, TODO, doc links, QA, and validator fixture checks passed. |

## Manual QA Results

| Checklist Item | Result | Notes |
| --- | --- | --- |
| README opt-in steps | PASS | `AGENT_OBSERVATION_EXTRACTOR=llm` and OpenRouter / `deepseek/deepseek-v4-pro` are explicit manual steps. |
| Default behavior | PASS | README and reference state deterministic default and no real provider requirement. |
| Raw provider response persistence | PASS | Code review and tests confirm fallback stores failure class only, not raw provider text. |
| Live OpenRouter provider call | PARTIAL | Isolated OpenRouter / `deepseek/deepseek-v4-pro` smoke ran. Two raw events produced schema-valid LLM observations; one raw event returned invalid JSON and safely used deterministic fallback. Digest decisions, actions, and outcomes still followed. |

## Acceptance Criteria Coverage

| ID | Result | Evidence |
| --- | --- | --- |
| AC-001 | PASS | `Settings` defaults to `observation_extractor="deterministic"`; tests confirm default extraction metadata. |
| AC-002 | PASS | LLM path is selected only when `observation_extractor="llm"` in settings; multiple proposals are persisted and routed separately. |
| AC-003 | PASS | LLM extractor returns `ObservationExtractionResult` / `ObservationDraft`; downstream persistence remains in wake cycle. |
| AC-004 | PASS | `LLMObservationProposal` validates JSON schema, clamps scores, rejects unsupported dispositions, and bounds text fields. |
| AC-005 | PASS | fallback tests cover validation and provider errors without raw response persistence. |
| AC-006 | PASS | wake integration test checks observation rationale and `digest_decisions.metadata_json` extractor/provider/fallback metadata. |
| AC-007 | PASS | README/reference document OpenRouter / `deepseek/deepseek-v4-pro` as manual opt-in only; focused re-verification executed it outside CI/default path. |

## Invariant Coverage

| ID | Result | Evidence |
| --- | --- | --- |
| INV-001 | PASS | Default settings use deterministic extraction and no provider client. |
| INV-002 | PASS | LLM extractor has no `Session` dependency and does not write downstream DB rows. |
| INV-003 | PASS | invalid output and provider error tests fall back or strict-raise without raw response persistence. |
| INV-004 | PASS | unit test confirms score clamp and bounded normalized text. |
| INV-005 | PASS | digest metadata stores extractor/provider/fallback status only. |
| INV-006 | PASS | docs keep OpenRouter live usage manual and do not enable CI / Discord / Web search. |

## Deferred / Not Covered

| ID | Reason | Follow-up |
| --- | --- | --- |
| Provider JSON reliability | OpenRouter / `deepseek/deepseek-v4-pro` produced schema-valid output for two raw events and invalid JSON for one raw event in the manual smoke. Safe fallback worked, but provider adherence is not perfect. | Consider provider-specific structured output or stricter prompt/response-format work before relying on LLM-only extraction quality. |

## Residual Risks

- None

## Follow-up TODOs

- None required before default/offline operation or the current proposal-only extractor remains safe. Future work can separately cover provider-specific structured output, multiple proposals per raw event, or LLM-backed digest proposals.
