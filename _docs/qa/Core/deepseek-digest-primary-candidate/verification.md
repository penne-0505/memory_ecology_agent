---
title: "QA Verification: DeepSeek Digest Primary Candidate"
status: active
draft_status: n/a
qa_status: verified
risk: Medium
created_at: 2026-06-03
updated_at: 2026-06-03
references:
  - "_docs/plan/Core/deepseek-digest-primary-candidate/plan.md"
  - "_docs/intent/Core/deepseek-digest-primary-candidate/decision.md"
  - "_docs/qa/Core/deepseek-digest-primary-candidate/test-plan.md"
  - "_evals/reports/openrouter_structured_deepseek_digest_shadow_2026-06-03_run1.md"
  - "_evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_none_2026-06-03_run1.md"
  - "_evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_none_2026-06-03_run2.md"
  - "_evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_none_2026-06-03_run3.md"
  - "_evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_exclude_only_2026-06-03_run1.md"
  - "_evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_minimal_exclude_2026-06-03_run1.md"
  - "_evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_low_exclude_2026-06-03_run1.md"
  - "_evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_high_3072_2026-06-03_run1.md"
  - "_evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_high_3072_2026-06-03_run2.md"
related_issues: []
related_prs: []
---

# QA Verification: `DeepSeek Digest Primary Candidate`

## Summary

`deepseek/deepseek-v4-pro` was evaluated as the replacement primary candidate for live digest proposal shadow evaluation. The first run used the qwen clean payload shape (`max_tokens`, `response_format=json_schema`, `structured_outputs=true`, `provider.require_parameters=true`) and was not clean: schema-valid `15/16`, malformed JSON `1`, fallback `1/16`, provider error `0`, validation error `0`, raw persisted `0`.

OpenRouter model metadata shows DeepSeek supports `reasoning` and `include_reasoning` in addition to `max_tokens`, `response_format`, and `structured_outputs`. OpenRouter reasoning docs state that `reasoning.effort="none"` disables reasoning, and `reasoning.exclude=true` excludes reasoning tokens from the response. A minimal opt-in evaluation payload was added behind `AGENT_OPENROUTER_REASONING_EFFORT` / `AGENT_OPENROUTER_REASONING_EXCLUDE`; defaults are unchanged.

With `reasoning.effort=none` and `reasoning.exclude=true`, DeepSeek produced three clean structured shadow runs. The live evaluation runner primary default was switched to `deepseek/deepseek-v4-pro`; qwen remains verified fallback/baseline.

A follow-up reasoning-mode split was run after the primary-candidate gate to test whether `reasoning.exclude=true` alone is sufficient and whether `minimal` or `low` reasoning can preserve structured stability. It did not identify a clean reasoning-enabled option: exclude-only had malformed JSON plus one validation error, `minimal` had one malformed JSON fallback, and `low` had three malformed JSON fallbacks. This keeps `reasoning.effort=none` plus `reasoning.exclude=true` as the recommended DeepSeek evaluation setting.

A later high-reasoning budget check tested the user's proposed practical DeepSeek reasoning setting: `reasoning.effort=high`, `reasoning.exclude=true`, and `AGENT_LLM_MAX_TOKENS=3072`. Run1 was clean, but the gated follow-up run2 was not clean: schema-valid `15/16`, fallback `1/16`, validation error `1`, validation aggregate `evidence_quote:string_too_long x1`, malformed JSON `0`, provider error `0`, and raw persisted `0`. The captured failure diagnostic reported `finish_reason=stop`, `reasoning_tokens=610`, and `total_tokens=3726`, so the earlier `finish_reason=length` problem was not reproduced at 3072, but high reasoning still did not meet the repeated-clean structured shadow gate.

## Verification Verdict

Verdict: PASS

Gate decision: `GO` for DeepSeek as the live evaluation primary candidate/default only. This does not implement or enable `llm_assisted`, and it does not change production final digest behavior.

High-reasoning setting decision: `NO_GO` for replacing the recommended DeepSeek evaluation setting with `reasoning.effort=high` + `max_tokens=3072`. Keep the current DeepSeek structured shadow evaluation recommendation at `AGENT_OPENROUTER_REASONING_EFFORT=none` and `AGENT_OPENROUTER_REASONING_EXCLUDE=true`.

## Commands Run

```bash
date +%F
```

Result:

```text
2026-06-03
```

```bash
python - <<'PY'
import os
print('OPENROUTER_API_KEY_PRESENT=' + str(bool(os.environ.get('OPENROUTER_API_KEY'))).lower())
PY
```

Result:

```text
OPENROUTER_API_KEY_PRESENT=true
```

```bash
python - <<'PY'
import json, urllib.request
url='https://openrouter.ai/api/v1/models'
with urllib.request.urlopen(url, timeout=30) as r:
    data=json.load(r)
for model_id in ['deepseek/deepseek-v4-pro','qwen/qwen3.6-plus']:
    match=next((m for m in data.get('data',[]) if m.get('id')==model_id), None)
    print('MODEL', model_id)
    print('supported_parameters=', json.dumps(match.get('supported_parameters'), ensure_ascii=False))
PY
```

Result:

```text
MODEL deepseek/deepseek-v4-pro
supported_parameters= ["frequency_penalty", "include_reasoning", "logit_bias", "logprobs", "max_tokens", "min_p", "presence_penalty", "reasoning", "repetition_penalty", "response_format", "seed", "stop", "structured_outputs", "temperature", "tool_choice", "tools", "top_k", "top_logprobs", "top_p"]
MODEL qwen/qwen3.6-plus
supported_parameters= ["include_reasoning", "max_tokens", "presence_penalty", "reasoning", "response_format", "seed", "structured_outputs", "temperature", "tool_choice", "tools", "top_p"]
```

```bash
AGENT_MAX_WEB_QUERIES=0 AGENT_LLM_PROVIDER=openrouter \
  uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/run_live_digest_model_comparison.py \
    --provider openrouter \
    --model deepseek/deepseek-v4-pro \
    --observation-concurrency 4 \
    --output-json _evals/reports/openrouter_structured_deepseek_digest_shadow_2026-06-03_run1.json \
    --output-md _evals/reports/openrouter_structured_deepseek_digest_shadow_2026-06-03_run1.md
```

Result:

```text
_evals/reports/openrouter_structured_deepseek_digest_shadow_2026-06-03_run1.json
_evals/reports/openrouter_structured_deepseek_digest_shadow_2026-06-03_run1.md
```

```bash
AGENT_MAX_WEB_QUERIES=0 AGENT_LLM_PROVIDER=openrouter \
  AGENT_OPENROUTER_REASONING_EFFORT=none \
  AGENT_OPENROUTER_REASONING_EXCLUDE=true \
  uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/run_live_digest_model_comparison.py \
    --provider openrouter \
    --model deepseek/deepseek-v4-pro \
    --observation-concurrency 4 \
    --output-json _evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_none_2026-06-03_run1.json \
    --output-md _evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_none_2026-06-03_run1.md
```

Result:

```text
_evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_none_2026-06-03_run1.json
_evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_none_2026-06-03_run1.md
```

```bash
AGENT_MAX_WEB_QUERIES=0 AGENT_LLM_PROVIDER=openrouter \
  AGENT_OPENROUTER_REASONING_EFFORT=none \
  AGENT_OPENROUTER_REASONING_EXCLUDE=true \
  uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/run_live_digest_model_comparison.py \
    --provider openrouter \
    --model deepseek/deepseek-v4-pro \
    --observation-concurrency 4 \
    --output-json _evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_none_2026-06-03_run2.json \
    --output-md _evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_none_2026-06-03_run2.md
```

Result:

```text
_evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_none_2026-06-03_run2.json
_evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_none_2026-06-03_run2.md
```

```bash
AGENT_MAX_WEB_QUERIES=0 AGENT_LLM_PROVIDER=openrouter \
  AGENT_OPENROUTER_REASONING_EFFORT=none \
  AGENT_OPENROUTER_REASONING_EXCLUDE=true \
  uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/run_live_digest_model_comparison.py \
    --provider openrouter \
    --model deepseek/deepseek-v4-pro \
    --observation-concurrency 4 \
    --output-json _evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_none_2026-06-03_run3.json \
    --output-md _evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_none_2026-06-03_run3.md
```

Result:

```text
_evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_none_2026-06-03_run3.json
_evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_none_2026-06-03_run3.md
```

```bash
env -u AGENT_OPENROUTER_REASONING_EFFORT \
  AGENT_OPENROUTER_REASONING_EXCLUDE=true \
  AGENT_MAX_WEB_QUERIES=0 AGENT_LLM_PROVIDER=openrouter \
  uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/run_live_digest_model_comparison.py \
    --provider openrouter \
    --model deepseek/deepseek-v4-pro \
    --observation-concurrency 4 \
    --output-json _evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_exclude_only_2026-06-03_run1.json \
    --output-md _evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_exclude_only_2026-06-03_run1.md
```

Result:

```text
_evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_exclude_only_2026-06-03_run1.json
_evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_exclude_only_2026-06-03_run1.md
```

```bash
AGENT_MAX_WEB_QUERIES=0 AGENT_LLM_PROVIDER=openrouter \
  AGENT_OPENROUTER_REASONING_EFFORT=minimal \
  AGENT_OPENROUTER_REASONING_EXCLUDE=true \
  uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/run_live_digest_model_comparison.py \
    --provider openrouter \
    --model deepseek/deepseek-v4-pro \
    --observation-concurrency 4 \
    --output-json _evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_minimal_exclude_2026-06-03_run1.json \
    --output-md _evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_minimal_exclude_2026-06-03_run1.md
```

Result:

```text
_evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_minimal_exclude_2026-06-03_run1.json
_evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_minimal_exclude_2026-06-03_run1.md
```

```bash
AGENT_MAX_WEB_QUERIES=0 AGENT_LLM_PROVIDER=openrouter \
  AGENT_OPENROUTER_REASONING_EFFORT=low \
  AGENT_OPENROUTER_REASONING_EXCLUDE=true \
  uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/run_live_digest_model_comparison.py \
    --provider openrouter \
    --model deepseek/deepseek-v4-pro \
    --observation-concurrency 4 \
    --output-json _evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_low_exclude_2026-06-03_run1.json \
    --output-md _evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_low_exclude_2026-06-03_run1.md
```

Result:

```text
_evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_low_exclude_2026-06-03_run1.json
_evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_low_exclude_2026-06-03_run1.md
```

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_digest_decider.py tests/test_live_digest_runner.py -q
```

Result:

```text
27 passed
```

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_live_digest_runner.py tests/test_digest_decider.py tests/test_llm.py tests/test_openrouter_structured_output_probe.py -q
```

Result:

```text
46 passed
```

```bash
./scripts/check-docs.sh
```

Result:

```text
PASS
```

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest
```

Result:

```text
99 passed, 1 warning
```

## Automated Test Results

| Command / Test | Result | Notes |
| --- | --- | --- |
| `tests/test_digest_decider.py tests/test_live_digest_runner.py -q` | PASS | Covers OpenRouter structured payload default, opt-in reasoning disable payload, runner primary metadata, partial artifacts, and validation aggregates. |
| `tests/test_live_digest_runner.py tests/test_digest_decider.py tests/test_llm.py tests/test_openrouter_structured_output_probe.py -q` | PASS | `46 passed`; focused regression across runner, digest decider, LLM payload, and structured probe helpers. |
| `./scripts/check-docs.sh` | PASS | TODO, QA, frontmatter, doc links, and validator fixtures passed. |
| Full pytest | PASS | `99 passed, 1 warning`; warning is the existing Discord `audioop` deprecation. |

## Manual QA Results

| Checklist Item | Result | Notes |
| --- | --- | --- |
| Credential gate | PASS | `OPENROUTER_API_KEY` was present; the secret value was not printed. |
| Supported parameter check | PASS | DeepSeek lists `max_tokens`, `response_format`, `structured_outputs`, `reasoning`, and `include_reasoning`. |
| qwen-equivalent payload first run | FAIL_FOR_CLEAN_GATE | Provider accepted the payload, but one observation produced malformed JSON. |
| reasoning-disabled staged runs | PASS | Three same-condition runs were clean. |
| reasoning-mode split | PASS | A/B/C/D were compared with one run each; B/C/D were not clean, so no extra repetitions were run. |
| Raw response / secret non-persistence | PASS | All artifacts report `raw_provider_response_persisted=false` / `raw_response_persisted_count=0`; raw model text is not stored. |
| Boundary review | PASS | Production final digest path, `AGENT_DIGEST_DECIDER` default, Discord/Web search behavior, Pydantic gate, raw response persistence, and `llm_assisted` implementation remain unchanged. |

## DeepSeek Evidence

| Run | Payload note | Schema-valid | Fallback | Malformed JSON | Validation errors | Provider errors | Raw persisted | Validation aggregate | model / normalized `should_apply=true` | Action candidates | Gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| initial run1 | qwen clean payload | `15/16` | `1/16` | `1` | `0` | `0` | `0` | `[]` | `0 / 0` | `1` | `RETURN_TO_HARDENING` |
| reasoning-none run1 | `reasoning.effort=none`, `exclude=true` | `16/16` | `0/16` | `0` | `0` | `0` | `0` | `[]` | `2 / 2` | `1` | `GO sample 1/3` |
| reasoning-none run2 | same | `16/16` | `0/16` | `0` | `0` | `0` | `0` | `[]` | `2 / 2` | `1` | `GO sample 2/3` |
| reasoning-none run3 | same | `16/16` | `0/16` | `0` | `0` | `0` | `0` | `[]` | `3 / 2` | `1` | `GO sample 3/3` |
| reasoning-high-3072 run1 | `reasoning.effort=high`, `exclude=true`, `AGENT_LLM_MAX_TOKENS=3072` | `16/16` | `0/16` | `0` | `0` | `0` | `0` | `[]` | `4 / 4` | `1` | `GO sample 1/2` |
| reasoning-high-3072 run2 | same | `15/16` | `1/16` | `0` | `1` | `0` | `0` | `evidence_quote:string_too_long x1` | `2 / 0` | `1` | `NO_GO setting replacement` |

All three `reasoning-none` runs recorded `structured_output_enabled=true`, `structured_outputs=true`, `provider_require_parameters=true`, token parameter `max_tokens`, `reasoning_effort=none`, `reasoning_exclude=true`, Web search disabled, Discord disabled, proposal-only shadow mode, and no raw provider response persistence.

The repeated `action_candidate_count=1` signal matches the qwen structured baseline pattern and is not auto-adopted. DeepSeek has higher normalized `should_apply=true` than qwen (`2`, `2`, `2` vs qwen `0`, `0`, `0`), so this verification authorizes only live evaluation primary-candidate/default switching. It does not broaden the assisted-readiness gate.

The high-3072 follow-up shows a narrower result: increasing `max_tokens` removes the observed length-truncation failure mode in the failed follow-up diagnostic, but it does not make the high-reasoning setting clean across repeated structured shadow runs. Run2 failed local Pydantic validation with `evidence_quote:string_too_long`; the opt-in diagnostic recorded `finish_reason=stop`, `reasoning_tokens=610`, `total_tokens=3726`, and cost `0.00755338` for that failed observation. Successful observation-level usage and cost are not available in the standard artifact.

## DeepSeek Reasoning Mode Split

| Candidate | Payload note | Artifact | Schema-valid | Fallback | Malformed JSON | Validation errors | Provider errors | Raw persisted | Validation aggregate | Agreement / disagreement | model / normalized `should_apply=true` | Action candidates | Runtime | Follow-up |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | reasoning unspecified | `_evals/reports/openrouter_structured_deepseek_digest_shadow_2026-06-03_run1.json` | `15/16` | `1/16` | `1` | `0` | `0` | `0` | `[]` | `8 / 7` | `0 / 0` | `1` | `75.6s` | No extra run; not clean. |
| B | reasoning unspecified, `exclude=true` | `_evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_exclude_only_2026-06-03_run1.json` | `14/16` | `2/16` | `1` | `1` | `0` | `0` | `evidence_quote:string_too_long x1` | `9 / 5` | `0 / 0` | `1` | `70.5s` | No extra run; not clean. |
| C | `reasoning.effort=minimal`, `exclude=true` | `_evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_minimal_exclude_2026-06-03_run1.json` | `15/16` | `1/16` | `1` | `0` | `0` | `0` | `[]` | `10 / 5` | `2 / 0` | `0` | `109.3s` | No extra run; not clean. |
| D | `reasoning.effort=low`, `exclude=true` | `_evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_low_exclude_2026-06-03_run1.json` | `13/16` | `3/16` | `3` | `0` | `0` | `0` | `[]` | `7 / 6` | `3 / 3` | `0` | `112.0s` | No extra run; not clean. |
| E | `reasoning.effort=none`, `exclude=true` | existing 3-run baseline | `16/16` x3 | `0/16` x3 | `0` x3 | `0` x3 | `0` x3 | `0` x3 | `[]` x3 | `9/7`, `8/8`, `8/8` | `2/2`, `2/2`, `3/2` | `1` each | `34.5s`, `16.2s`, `30.8s` | Keep as recommended setting. |
| F | `reasoning.effort=high`, `exclude=true`, `max_tokens=3072` | `_evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_high_3072_2026-06-03_run1.json` | `16/16` | `0/16` | `0` | `0` | `0` | `0` | `[]` | `11 / 5` | `4 / 4` | `1` | `136.2s` | Run2 because run1 was clean. |
| G | `reasoning.effort=high`, `exclude=true`, `max_tokens=3072` | `_evals/reports/openrouter_structured_deepseek_digest_shadow_reasoning_high_3072_2026-06-03_run2.json` | `15/16` | `1/16` | `0` | `1` | `0` | `0` | `evidence_quote:string_too_long x1` | `9 / 6` | `2 / 0` | `1` | `97.6s` | Do not replace recommended setting. |

Interpretation:

- `exclude=true` alone is not sufficient evidence for stability. It still produced both malformed JSON and a Pydantic validation failure.
- `minimal` and `low` reasoning did not preserve clean structured output in the first run. `low` was the weakest structured candidate and also slower than the clean `none` baseline.
- `high` reasoning with a larger `3072` output budget prevents the specific `finish_reason=length` failure in the captured failed follow-up, but it still failed the repeated-clean gate through a Pydantic validation error.
- The current evidence supports reasoning output as a plausible instability contributor, but not with perfect causal isolation: A/B/C/D are one run each, F/G are a gated two-run check, and raw response content is intentionally limited to explicit opt-in failure diagnostics. The practical conclusion is stronger than the causal claim: DeepSeek structured digest evaluation should continue to send `reasoning.effort=none` and `reasoning.exclude=true`.

## Payload / Supported Parameter Notes

- OpenRouter model metadata for DeepSeek lists `max_tokens`, `response_format`, `structured_outputs`, `reasoning`, and `include_reasoning`.
- The qwen-equivalent payload is accepted by the provider but was not clean for DeepSeek because one observation produced malformed JSON.
- The minimal adjustment is opt-in only: `AGENT_OPENROUTER_REASONING_EFFORT=none` and `AGENT_OPENROUTER_REASONING_EXCLUDE=true`.
- OpenRouter docs describe `reasoning.effort="none"` as disabling reasoning and `reasoning.exclude=true` as excluding reasoning tokens from the response.
- Follow-up split evidence rejects `exclude=true` alone and does not support `minimal` or `low` reasoning for this structured digest proposal runner.
- Follow-up high-budget evidence does not support changing the recommended DeepSeek structured shadow setting to `reasoning.effort=high` plus `AGENT_LLM_MAX_TOKENS=3072`.

## Acceptance Criteria Coverage

| ID | Status | Evidence |
| --- | --- | --- |
| AC-001 | PASS | OpenRouter model metadata checked; supported parameters recorded; no secret printed. |
| AC-002 | PASS | Initial DeepSeek run used qwen clean payload shape and recorded structured metadata. |
| AC-003 | PASS | Additional two runs were executed only after the reasoning-disabled run1 was clean. |
| AC-004 | PASS | After three clean reasoning-disabled runs, `PRIMARY_MODEL` changed to `deepseek/deepseek-v4-pro`; qwen docs now mark qwen as verified fallback/baseline. |
| AC-005 | PASS | Boundary diff review confirms no production final digest, default decider, Discord/Web search, Pydantic gate, raw persistence, or `llm_assisted` adoption change. |

## Invariant Coverage

| ID | Status | Evidence |
| --- | --- | --- |
| INV-001 | PASS | Final digest decisions remain deterministic by default. |
| INV-002 | PASS | `app/config.py` still defaults `digest_decider="deterministic"`. |
| INV-003 | PASS | `llm_assisted` was not implemented or enabled. |
| INV-004 | PASS | Raw provider responses and credential values were not persisted or printed. |
| INV-005 | PASS | DeepSeek first used qwen clean payload; reasoning adjustment was made only after malformed JSON evidence and supported-parameter confirmation. |
| INV-006 | PASS | `LLMDigestProposal.model_validate` remains the final gate. |
| INV-007 | PASS | Primary/default changed only after three clean DeepSeek runs under the documented payload. |
| INV-008 | PASS | qwen remains recorded as verified fallback/baseline. |
| INV-009 | PASS | The high-3072 check did not change production final digest behavior, `AGENT_DIGEST_DECIDER` default, Discord/Web search behavior, Pydantic gate, raw persistence, or `llm_assisted`. |

## Deferred / Not Covered

| ID | Reason | Follow-up |
| --- | --- | --- |
| Assisted readiness with DeepSeek | DeepSeek has normalized `should_apply=true` in every clean run, unlike qwen. | Keep `llm_assisted` out of scope; use separate readiness/design work if needed. |
| Raw malformed content from initial run | Raw responses are intentionally not persisted. | Continue using sanitized failure class / aggregate evidence only. |

## Residual Risks

None

## Follow-up TODOs

None.
