---
title: "QA Verification: LLM Digest Proposal Quality Evaluation"
status: active
draft_status: n/a
qa_status: partial
risk: Medium
created_at: 2026-06-02
updated_at: 2026-06-02
references:
  - "_docs/intent/Core/llm-digest-proposal-quality-evaluation/decision.md"
  - "_docs/plan/Core/llm-digest-proposal-quality-evaluation/plan.md"
  - "_docs/qa/Core/llm-digest-proposal-quality-evaluation/test-plan.md"
  - "_evals/reports/llm_digest_proposal_quality_2026-06-02.md"
related_issues: []
related_prs: []
---

# QA Verification: `LLM Digest Proposal Quality Evaluation`

## Summary

Sample world 上で deterministic baseline と `llm_shadow` offline mock proposal を比較し、agreement / disagreement / fallback / safety boundary を `_evals/reports/llm_digest_proposal_quality_2026-06-02.md` に記録した。その後、明示 credential が利用可能な状態で live OpenRouter / `deepseek/deepseek-v4-pro` の shadow evaluation を isolated temp root で実行した。初回 live run は schema-valid `9/16` だったが、prompt v3 + deterministic `should_apply` normalization 後の addendum では schema-valid `15/16` へ改善した。

## Verification Verdict

Verdict: PARTIAL

Offline evaluation scaffolding、mock proposal comparison、live v4pro shadow evaluation、report generation、runtime non-adoption boundary は確認済み。prompt v3 + deterministic normalization 後の addendum では schema-valid `15/16`、rejected/fallback `1/16`、malformed JSON `0`、validation error `1`、model `should_apply=true` `3`、normalized `should_apply=true` `3` まで改善した。ただし 1 件の schema validation failure が残り、live sample は 16 件に限られる。`llm_assisted` readiness は未証明のため、recommendation は `KEEP_SHADOW_AND_COLLECT_MORE`、verdict は PARTIAL のままとする。

## Commands Run

```bash
date +%F
```

Result:

```text
2026-06-02
```

```bash
uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/evaluate_llm_digest_proposals.py
```

Result:

```text
/home/penne/dev/active/memory_ecology_agent/_evals/reports/llm_digest_proposal_quality_2026-06-02.md
```

```bash
AGENT_LLM_PROVIDER=openrouter AGENT_LLM_MODEL=deepseek/deepseek-v4-pro AGENT_DIGEST_DECIDER=llm_shadow AGENT_MAX_WEB_QUERIES=0 uv run --python /home/penne/.local/bin/python3.12 python - <<'PY'
# isolated temp-root live evaluation harness; persisted sanitized metrics only
PY
```

Result:

```text
/tmp/live_v4pro_digest_shadow_eval_summary.json
live_execution=RAN_INITIAL
temp_root=/tmp/live-v4pro-digest-shadow-bjdbgkti
total_observations=16
total_proposals=16
schema_valid_count=9
fallback_rejected_malformed_count=7
agreement_count=5
disagreement_count=4
action_candidate_count=0
should_apply_true_count=9
raw_response_persisted_count=0
core_profile_unchanged=True
discord_enabled=False
```

```bash
AGENT_LLM_PROVIDER=openrouter AGENT_LLM_MODEL=deepseek/deepseek-v4-pro AGENT_DIGEST_DECIDER=llm_shadow AGENT_MAX_WEB_QUERIES=0 uv run --python /home/penne/.local/bin/python3.12 python - <<'PY'
# isolated temp-root live evaluation harness after prompt v3 + deterministic should_apply normalization; persisted sanitized metrics only
PY
```

Result:

```text
live_execution=RAN_ADDENDUM
temp_root=/tmp/digest-proposal-live-v4pro-gj_wbpbm
total_observations=16
total_proposals=16
schema_valid_count=15
rejected_fallback_count=1
malformed_json_count=0
validation_error_count=1
agreement_count=10
disagreement_count=5
action_candidate_count=0
model_should_apply_true_count=3
normalized_should_apply_true_count=3
raw_response_persisted_count=0
core_profile_unchanged=True
discord_enabled=False
recommendation=KEEP_SHADOW_AND_COLLECT_MORE
```

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_live_digest_runner.py tests/test_digest_decider.py
```

Result:

```text
14 passed in 0.26s
```

```bash
./scripts/check-docs.sh
```

Result:

```text
Checked 5 files
PASS todo _evals/validator-fixtures/todo/valid/basic.md
PASS todo _evals/validator-fixtures/todo/invalid/missing-title.md failed as expected
PASS todo _evals/validator-fixtures/todo/invalid/malformed-heading.md failed as expected
PASS todo _evals/validator-fixtures/todo/invalid/missing-qa-for-medium.md failed as expected
PASS todo _evals/validator-fixtures/todo/invalid/mismatched-heading-id.md failed as expected
PASS qa _evals/validator-fixtures/qa/valid
PASS qa _evals/validator-fixtures/qa/invalid/missing-invariant.md failed as expected
PASS qa _evals/validator-fixtures/qa/invalid/status-verdict-mismatch.md failed as expected
PASS qa _evals/validator-fixtures/qa/invalid/verification-in-progress-status.md failed as expected
PASS qa _evals/validator-fixtures/qa/invalid/verification-missing-test-plan-reference.md failed as expected
PASS qa _evals/validator-fixtures/qa/invalid/qa-archive-path.md failed as expected
```

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest
```

Result:

```text
80 passed, 1 warning in 1.31s
```

## Automated Test Results

| Command / Test | Result | Notes |
| --- | --- | --- |
| `uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/evaluate_llm_digest_proposals.py` | PASS | Generated `_evals/reports/llm_digest_proposal_quality_2026-06-02.md`. |
| Initial live OpenRouter / `deepseek/deepseek-v4-pro` temp-root harness | PARTIAL | Live execution ran; schema-valid `9/16` and `should_apply=true` `9/9` showed prompt/normalization problems. |
| Prompt v3 + deterministic normalization live addendum | PARTIAL | Live execution improved to schema-valid `15/16`, rejected/fallback `1/16`, malformed JSON `0`, validation error `1`, and normalized `should_apply=true` `3`; still insufficient for assisted adoption. |
| `uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_live_digest_runner.py tests/test_digest_decider.py` | PASS | Live runner hardening and existing digest proposal behavior still pass. |
| `./scripts/check-docs.sh` | PASS | Frontmatter, TODO, doc links, QA, and validator fixtures passed. |
| `uv run --python /home/penne/.local/bin/python3.12 pytest` | PASS | Full test suite passed with one upstream deprecation warning from `discord/player.py`. |

## Manual QA Results

| Checklist Item | Result | Notes |
| --- | --- | --- |
| Review qualitative samples | PASS | Agreement, disagreement, LLM-better, deterministic-safer, unclear, and fallback/rejected sections are present. |
| Confirm no raw response text in report | PASS | Report includes metrics and short persisted reasons only; raw provider response text was not persisted. |
| Confirm live provider gating | PASS | Earlier report marked live v4pro as skipped when explicit provider/model were absent; live addendum ran only after explicit env config was supplied. |

## Evidence Summary

- Offline mock report generated 16 observations, 16 deterministic decisions, and 16 schema-valid proposals.
- Agreement count was 10; disagreement count was 6; agreement rate was 0.625.
- LLM proposed distribution: concern_candidate 4, memory_candidate 7, discard 4, action_candidate 1, no_op 0.
- Final deterministic distribution: concern_candidate 8, memory_candidate 5, discard 3, action_candidate 0, no_op 0.
- Rejected/fallback proposal count was 0 in the offline fake run.
- Raw response persisted count was 0.
- Recommendation recorded: `PROMPT_HARDENING_FIRST`.
- Initial live OpenRouter / `deepseek/deepseek-v4-pro` run generated 16 observations, 16 proposals, 9 schema-valid proposals, and 7 fallback/rejected proposals.
- Initial live malformed / validation breakdown: JSONDecodeError 4, ValidationError 3, provider error 0.
- Initial live `should_apply=true` count was 9/9 among valid proposals, which was not conservative enough.
- Prompt v3 + deterministic normalization addendum generated 16 observations, 16 proposals, 15 schema-valid proposals, and 1 rejected/fallback proposal.
- Addendum malformed / validation breakdown: malformed JSON 0, validation error 1, provider error 0.
- Addendum proposed distribution among valid proposals: concern_candidate 5, memory_candidate 6, discard 4, action_candidate 0, no_op 0.
- Addendum deterministic final distribution: concern_candidate 8, memory_candidate 5, discard 3, action_candidate 0, no_op 0.
- Addendum agreement count was 10; disagreement count was 5 among schema-valid proposals.
- Addendum model `should_apply=true` count was 3, and normalized `should_apply=true` count was 3.
- Addendum raw response persisted count was 0.
- Live recommendation remains `KEEP_SHADOW_AND_COLLECT_MORE`.

## Acceptance Criteria Coverage

| ID | Status | Evidence |
| --- | --- | --- |
| AC-001 | PASS | `_evals/reports/llm_digest_proposal_quality_2026-06-02.md` compares deterministic final decisions and proposals. |
| AC-002 | PASS | Report includes offline and live agreement, disagreement, LLM-better, deterministic-safer, unclear, and fallback/rejected sections. |
| AC-003 | PASS | Report records `KEEP_SHADOW_AND_COLLECT_MORE` and no active adoption. |

## Invariant Coverage

| ID | Status | Evidence |
| --- | --- | --- |
| INV-001 | PASS | Only evaluation script, fixture, report, and docs changed; final digest updater remains deterministic. |
| INV-002 | PASS | Report includes disagreement and fallback/rejected sections. |
| INV-003 | PASS | Live provider remains optional; earlier run was skipped when config was absent, and live run required explicit provider/model/credential. |
| INV-004 | PASS | Report recommendation forbids automatic `action_candidate` adoption. |
| INV-005 | PASS | No runtime path was changed to mutate `core_profile`, `self_model`, Discord mode, Web search, or final digest decisions. |

## Deferred / Not Covered

| ID | Reason | Follow-up |
| --- | --- | --- |
| Broader live quality | The addendum improved schema validity from `9/16` to `15/16`, but the live sample is still only 16 observations and one validation failure remains. | Keep collecting shadow data before any assisted adoption. |
| `llm_assisted` readiness | The report intentionally evaluates `llm_shadow` only; no active adoption path was implemented or proven. | Keep `AGENT_DIGEST_DECIDER` default / final digest decision path unchanged until a separate readiness task exists. |

## Residual Risks

- Live `deepseek/deepseek-v4-pro` digest proposal quality is tested only on small 16-observation samples.
- Schema validity improved from 9 valid / 7 rejected-fallback to 15 valid / 1 rejected-fallback, but one validation failure remains.
- `should_apply` behavior improved from 9/9 true among valid proposals to model true 3 and normalized true 3, but this is not sufficient evidence for `llm_assisted` readiness.
- Unknown related concern id count is reported as 0 from persisted proposal fields; the current schema filters unknown IDs and does not retain rejected related IDs for retrospective counting.

## Follow-up TODOs

- Keep collecting `llm_shadow` data against live v4pro before assisted adoption.
- Investigate the remaining schema validation failure from the prompt v3 + normalization addendum.
- Treat any `llm_assisted` adoption rule as a separate task requiring broader live evidence and explicit safety gates.

## Verification Verdict Detail

Verdict: PARTIAL

Completion can be treated as a live shadow evaluation pass plus prompt v3 / normalization improvement evidence. It should not be used as evidence that `deepseek/deepseek-v4-pro` proposals are ready for assisted adoption.
