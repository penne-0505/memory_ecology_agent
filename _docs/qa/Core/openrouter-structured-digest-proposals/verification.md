---
title: "QA Verification: OpenRouter Structured Digest Proposals"
status: active
draft_status: n/a
qa_status: verified
risk: Medium
created_at: 2026-06-03
updated_at: 2026-06-03
references:
  - "_docs/plan/Core/openrouter-structured-digest-proposals/plan.md"
  - "_docs/intent/Core/openrouter-structured-digest-proposals/decision.md"
  - "_docs/qa/Core/openrouter-structured-digest-proposals/test-plan.md"
  - "_evals/reports/openrouter_structured_qwen_digest_shadow_2026-06-03_run1.md"
  - "_evals/reports/openrouter_structured_qwen_digest_shadow_2026-06-03_run2.md"
  - "_evals/reports/openrouter_structured_output_probe_qwen_2026-06-03_max_tokens.md"
  - "_evals/reports/openrouter_structured_output_probe_qwen_2026-06-03_digest_A_keys.md"
  - "_evals/reports/openrouter_structured_qwen_digest_shadow_max_tokens_2026-06-03_run1.md"
  - "_evals/reports/openrouter_structured_qwen_digest_shadow_validation_aggregate_2026-06-03_run1.md"
  - "_evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run1.md"
  - "_evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run2.md"
  - "_evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run3.md"
related_issues: []
related_prs: []
---

# QA Verification: `OpenRouter Structured Digest Proposals`

## Summary

OpenRouter structured-output payload support is active for digest proposal generation on OpenRouter only. The enforced qwen payload now uses `max_tokens`, `response_format.type=json_schema`, `structured_outputs=true`, and `provider.require_parameters=true`; non-OpenRouter paths keep the prompt-only fallback behavior.

Current targeted prompt-hardening evidence is `PASS`: the earlier provider error was caused by the `max_completion_tokens` confound, and the enforced `max_tokens` route now runs with provider error `0`. The previous diagnostic full run produced schema-valid `12/16`, validation error `4/16`, malformed JSON `0`, provider error `0`, and sanitized validation aggregate `related_concern_ids.0 | int_parsing | 4`. After minimal `related_concern_ids` prompt hardening, three qwen structured full runs produced schema-valid `16/16`, validation error `0/16`, malformed JSON `0`, provider error `0`, raw response persisted `0`, and sanitized validation aggregate `[]`.

This is validation evidence only. It supports the `llm_assisted` readiness gate moving to `GO` for future limited design consideration, but it does not implement or enable `llm_assisted`.

## Verification Verdict

Verdict: PASS

The implementation and safety checks pass, qwen accepts the enforced structured-output parameter set when `max_tokens` is used, and the targeted `related_concern_ids.0 | int_parsing` failure disappeared in the one requested full run. Readiness/adoption remains out of scope.

## Commands Run

```bash
date +%F
```

Result:

```text
2026-06-03
```

```bash
AGENT_MAX_WEB_QUERIES=0 AGENT_LLM_PROVIDER=openrouter \
  uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/run_live_digest_model_comparison.py \
    --provider openrouter \
    --model qwen/qwen3.6-plus \
    --observation-concurrency 4 \
    --output-json _evals/reports/openrouter_structured_qwen_digest_shadow_validation_aggregate_2026-06-03_run1.json \
    --output-md _evals/reports/openrouter_structured_qwen_digest_shadow_validation_aggregate_2026-06-03_run1.md
```

Result:

```text
_evals/reports/openrouter_structured_qwen_digest_shadow_validation_aggregate_2026-06-03_run1.json
_evals/reports/openrouter_structured_qwen_digest_shadow_validation_aggregate_2026-06-03_run1.md
```

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_digest_decider.py -q
```

Result:

```text
14 passed
```

```bash
AGENT_MAX_WEB_QUERIES=0 AGENT_LLM_PROVIDER=openrouter \
  uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/run_live_digest_model_comparison.py \
    --provider openrouter \
    --model qwen/qwen3.6-plus \
    --observation-concurrency 4 \
    --output-json _evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run1.json \
    --output-md _evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run1.md
```

Result:

```text
_evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run1.json
_evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run1.md
```

```bash
AGENT_MAX_WEB_QUERIES=0 AGENT_LLM_PROVIDER=openrouter \
  uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/run_live_digest_model_comparison.py \
    --provider openrouter \
    --model qwen/qwen3.6-plus \
    --observation-concurrency 4 \
    --output-json _evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run2.json \
    --output-md _evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run2.md
```

Result:

```text
_evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run2.json
_evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run2.md
```

```bash
AGENT_MAX_WEB_QUERIES=0 AGENT_LLM_PROVIDER=openrouter \
  uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/run_live_digest_model_comparison.py \
    --provider openrouter \
    --model qwen/qwen3.6-plus \
    --observation-concurrency 4 \
    --output-json _evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run3.json \
    --output-md _evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run3.md
```

Result:

```text
_evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run3.json
_evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run3.md
```

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_live_digest_runner.py
```

Result:

```text
11 passed
```

```bash
./scripts/check-docs.sh
```

Result:

```text
PASS
```

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest tests/test_llm.py tests/test_digest_decider.py tests/test_live_digest_runner.py tests/test_openrouter_structured_output_probe.py
```

Result:

```text
43 passed
```

```bash
uv run --python /home/penne/.local/bin/python3.12 pytest
```

Result:

```text
96 passed, 1 warning
```

## Automated Test Results

| Command / Test | Result | Notes |
| --- | --- | --- |
| `tests/test_digest_decider.py -q` | PASS | `14 passed`; added focused prompt-contract regression coverage. |
| `tests/test_live_digest_runner.py` | PASS | Validation aggregate and artifact raw-text exclusion covered. |
| `tests/test_llm.py tests/test_digest_decider.py tests/test_live_digest_runner.py tests/test_openrouter_structured_output_probe.py` | PASS | Payload shape, OpenRouter-only routing, prompt-only fallback, Pydantic final gate, probe helpers, and artifact metadata covered. |
| `./scripts/check-docs.sh` | PASS | TODO, QA, frontmatter, links, and validator fixtures passed. |
| Full pytest | PASS | `96 passed, 1 warning`; warning is existing Discord `audioop` deprecation. |

## Manual QA Results

| Checklist Item | Result | Notes |
| --- | --- | --- |
| Credential gate | PASS | `OPENROUTER_API_KEY` was present; the secret value was not printed. |
| Live qwen structured runs | PASS | Three prompt-hardened artifacts were created with structured metadata and provider error `0`; strict schema validation accepted `16/16` in each run. |
| Raw response / secret non-persistence | PASS | `raw_response_persisted_count=0`; artifact contains no raw model text. |
| Validation failure aggregate | PASS | Artifact records sanitized aggregate only; current value is `[]`. |
| Additional run decision | PASS | Follow-up readiness evidence collection added two same-condition qwen runs; both were clean. |

## Live Evidence

| Metric | Previous structured run | Previous aggregate diagnostic run | Prompt-hardened run1 | Prompt-hardened run2 | Prompt-hardened run3 |
| --- | --- | --- | --- | --- | --- |
| token parameter | `max_tokens` | `max_tokens` | `max_tokens` | `max_tokens` | `max_tokens` |
| structured outputs | `true` | `true` | `true` | `true` | `true` |
| provider require parameters | `true` | `true` | `true` | `true` | `true` |
| total observations | `16` | `16` | `16` | `16` | `16` |
| schema-valid proposals | `10/16` | `12/16` | `16/16` | `16/16` | `16/16` |
| fallback proposals | `6/16` | `4/16` | `0/16` | `0/16` | `0/16` |
| malformed JSON | `0` | `0` | `0` | `0` | `0` |
| validation errors | `6/16` | `4/16` | `0/16` | `0/16` | `0/16` |
| provider errors | `0` | `0` | `0` | `0` | `0` |
| raw response persisted | `0` | `0` | `0` | `0` | `0` |
| validation failure aggregate | not available | `related_concern_ids.0 | int_parsing | 4` | `[]` | `[]` | `[]` |

## Diagnostic Note

The structured-output payload was confirmed locally before network execution:

- `response_format.type=json_schema`
- `provider.require_parameters=true`
- all `LLMDigestProposal` fields listed in `required`
- `additionalProperties=false`
- no schema `default` entries

A single non-persisted diagnostic OpenRouter request returned:

```text
status=404
No endpoints found that can handle the requested parameters.
```

This was a historical diagnostic from the `max_completion_tokens` run. It is now understood as a token-parameter confound, not as evidence that the qwen route cannot accept structured-output parameters.

## Acceptance Criteria Coverage

| ID | Status | Evidence |
| --- | --- | --- |
| AC-001 | PASS | Unit tests confirm OpenRouter payload includes `response_format.type=json_schema` and `LLMDigestProposal` schema fields. |
| AC-002 | PASS | Unit tests and live artifact confirm `provider_require_parameters=true`. |
| AC-003 | PASS | Mock digest proposal path receives `extra_payload=None`. |
| AC-004 | PASS | Invalid enum output is still rejected as `ValidationError`; Pydantic remains final gate. |
| AC-005 | PASS | Live artifact records `structured_output_enabled=true`, `provider_require_parameters=true`, and `raw_provider_response_persisted=false`. |
| AC-006 | PASS | Metrics were recorded and compared: previous aggregate diagnostic `12/16` valid and `4/16` validation errors vs current prompt-hardened `16/16` valid and `0/16` validation errors. |
| AC-007 | PASS | Artifact records sanitized `validation_failure_aggregate` only; current value is `[]`. |
| AC-008 | PASS | Prompt now requires numeric concern IDs only, forbids labels/titles/objects/string sentinels, and requires `[]` when absent or uncertain; focused test covers this contract. |

## Invariant Coverage

| ID | Status | Evidence |
| --- | --- | --- |
| INV-001 | PASS | `llm_shadow` proposal path still leaves final decisions deterministic. |
| INV-002 | PASS | Default decider was not changed. |
| INV-003 | PASS | `llm_assisted` was not implemented or enabled. |
| INV-004 | PASS | Live artifacts report raw response persisted as false; raw model text is not stored. |
| INV-005 | PASS | OpenRouter-only payload is covered; mock/non-OpenRouter fallback remains prompt-only. |
| INV-006 | PASS | This evidence is recorded as readiness prerequisite only, not readiness PASS. |
| INV-007 | PASS | Pydantic validation remains final gate in tests and implementation; diagnostics did not relax `LLMDigestProposal` validation. |

## Deferred / Not Covered

| ID | Reason | Follow-up |
| --- | --- | --- |
| qwen validation cause beyond field/type | Raw response was intentionally not persisted, so the exact previous offending value remains unknown. | No raw-response replay; continue using aggregate-only diagnostics if failures recur. |
| Assisted-mode implementation | Out of scope for structured-output evidence collection. | Create a separate limited assisted design / implementation task if proceeding. |

## Residual Risks

None

## Follow-up TODOs

- None. The structured-output evidence now supports the readiness gate's `GO` route for future limited design consideration only.

## Addendum: Payload Dialect Probe

Date: 2026-06-03

The first `PARTIAL` result used `max_completion_tokens`. OpenRouter's model metadata for `qwen/qwen3.6-plus` reports `supported_parameters` including `max_tokens`, `response_format`, and `structured_outputs`, but not `max_completion_tokens`. Because `provider.require_parameters=true` requires routed endpoints to support requested parameters, `max_completion_tokens` confounded the earlier provider error.

### OpenRouter Docs Checked

| Topic | URL | Finding |
| --- | --- | --- |
| Structured outputs | `https://openrouter.ai/docs/features/structured-outputs` | `response_format.type=json_schema` can request structured outputs with JSON Schema. |
| API parameters | `https://openrouter.ai/docs/api/reference/parameters` | `response_format` supports `json_object`; `structured_outputs` is an optional boolean; token parameters include `max_tokens` and `max_completion_tokens`. |
| Provider routing | `https://openrouter.ai/docs/features/provider-routing` | `provider.require_parameters=true` requires providers to support requested parameters rather than silently dropping them. |
| Models metadata | `https://openrouter.ai/api/v1/models` | qwen metadata listed `max_tokens`, `response_format`, and `structured_outputs`; it did not list `max_completion_tokens`. |

### Minimal Matrix

Command:

```bash
uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/openrouter_structured_output_probe.py \
  --model qwen/qwen3.6-plus \
  --strict-variants \
  --token-parameter max_tokens \
  --output-json _evals/reports/openrouter_structured_output_probe_qwen_2026-06-03_max_tokens.json \
  --output-md _evals/reports/openrouter_structured_output_probe_qwen_2026-06-03_max_tokens.md
```

Result:

| Mode | Payload | Minimal schema result | Notes |
| --- | --- | --- | --- |
| A | `response_format=json_schema`, `provider.require_parameters=true` | PASS | `valid_json_object` |
| A strict=false | same, `strict=false` | PASS | `valid_json_object` |
| B | `response_format=json_schema`, `structured_outputs=true`, `provider.require_parameters=true` | PASS | `valid_json_object` |
| B strict=false | same, `strict=false` | PASS | `valid_json_object` |
| C | `response_format=json_schema`, `structured_outputs=true`, `provider.require_parameters=false` | PASS | Non-enforcing diagnostic only. |
| C strict=false | same, `strict=false` | PASS | Non-enforcing diagnostic only. |
| D | `response_format=json_object`, `provider.require_parameters=true` | PASS | `valid_json_object`; not schema-constrained. |
| E | `response_format=json_object`, `structured_outputs=true`, `provider.require_parameters=true` | PASS | `valid_json_object`; not schema-constrained. |
| F | `response_format=json_schema`, no provider object | PASS | Non-enforcing diagnostic only. |
| F strict=false | same, `strict=false` | PASS | Non-enforcing diagnostic only. |

### Digest Schema Probe

All minimal-success modes were tried once with the `LLMDigestProposal` strict schema. They returned HTTP `200` and JSON object content, but each was classified as `missing_expected_keys`. A targeted A-mode key-only diagnostic recorded:

- parsed keys: `confidence`, `decision`, `related_concern_ids`, `risk_flags`, `should_apply`
- missing keys: `alternative_decision`, `evidence_quote`, `evidence_summary`, `reason`
- raw response persisted: `false`

This is not a model/route non-support result. It is a schema/prompt/schema-enforcement problem after the minimal object dialect succeeds.

### Minimal Schema vs Digest Schema Difference

| Aspect | Minimal schema | `LLMDigestProposal` strict schema |
| --- | --- | --- |
| Field count | 1 field: `answer` | 9 required fields |
| Scalars | string only | string, number, boolean |
| Enums | none | two enum fields |
| Arrays | none | `related_concern_ids`, `risk_flags` |
| Length constraints | none | `maxLength`, `maxItems` |
| Defaults | none | removed from strict request schema, present in Pydantic model |
| Required fields | all fields required | all fields required in request schema |
| Additional properties | false | false |
| `$defs` / refs | none | none in current emitted strict schema |

The suspicious elements are not `$defs`, nullable fields, or nested objects. The likely issue is that qwen/OpenRouter accepts the payload dialect but does not reliably enforce the larger schema, especially multi-field required object generation with enums/arrays/length constraints. The missing key pattern shows optional-looking text fields and `alternative_decision` were omitted even though the request schema marked them required.

### Full Runner Recommendation

Do not run the 16-observation full digest runner yet.

The next full-run candidate payload, if a smaller digest schema probe passes first, is:

```json
{
  "token_parameter": "max_tokens",
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "llm_digest_proposal",
      "strict": true,
      "schema": "LLMDigestProposal strict schema"
    }
  },
  "provider": { "require_parameters": true }
}
```

Before full eval, run one or two targeted probes that reduce schema complexity while staying close to digest requirements:

- required all fields but remove `maxLength` / `maxItems`
- keep enums and arrays, but use stronger tiny prompt listing every required key
- optionally compare `json_schema strict=false` only as a diagnostic, not as final enforced evidence

`require_parameters=false` and no-provider-object successes remain diagnostic only. They must not be treated as enforced structured-output evidence.

## Addendum: max_tokens Full Shadow Run

Date: 2026-06-03

The OpenRouter runtime path was updated so OpenRouter chat completions use `max_tokens` while OpenAI keeps `max_completion_tokens`. The structured digest proposal payload now includes:

- `response_format.type=json_schema`
- `structured_outputs=true`
- `provider.require_parameters=true`
- token parameter `max_tokens`

Command:

```bash
AGENT_MAX_WEB_QUERIES=0 AGENT_LLM_PROVIDER=openrouter \
  uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/run_live_digest_model_comparison.py \
    --provider openrouter \
    --model qwen/qwen3.6-plus \
    --observation-concurrency 4 \
    --output-json _evals/reports/openrouter_structured_qwen_digest_shadow_max_tokens_2026-06-03_run1.json \
    --output-md _evals/reports/openrouter_structured_qwen_digest_shadow_max_tokens_2026-06-03_run1.md
```

Result:

```text
_evals/reports/openrouter_structured_qwen_digest_shadow_max_tokens_2026-06-03_run1.json
_evals/reports/openrouter_structured_qwen_digest_shadow_max_tokens_2026-06-03_run1.md
```

### Full Run Metrics

| Metric | Prompt-only qwen evidence | Previous structured attempt | max_tokens structured run |
| --- | --- | --- | --- |
| token parameter | n/a | `max_completion_tokens` | `max_tokens` |
| structured outputs | n/a | not explicit | `true` |
| provider require parameters | n/a | `true` | `true` |
| total observations | `16` | `16` | `16` |
| schema-valid proposals | mean `11/16` | `0/16` | `10/16` |
| fallback proposals | mean `5/16` | `16/16` | `6/16` |
| malformed JSON | `0` | `0` | `0` |
| validation errors | range `4-6/16`, mean `5/16` | `0/16` | `6/16` |
| provider errors | `0` | `16/16` | `0` |
| raw response persisted | `0` | `0` | `0` |

### Verdict Update

The max-token run is `PARTIAL`.

- PASS portion: provider error confound is resolved; enforced OpenRouter structured-output routing works with `max_tokens`.
- Remaining gap: digest schema required-field failures remain at `6/16`, slightly worse than the previous prompt-only mean and at the upper end of its `4-6/16` range.
- Safety: raw response persisted count remains `0`; final decisions remain deterministic; `llm_assisted` remains unimplemented and disabled.

## Addendum: Validation Failure Aggregate Diagnostic

Date: 2026-06-03

The full qwen run was repeated once with the same enforced payload:

- `token_parameter=max_tokens`
- `response_format.type=json_schema`
- `structured_outputs=true`
- `provider.require_parameters=true`
- `AGENT_MAX_WEB_QUERIES=0`
- `AGENT_LLM_PROVIDER=openrouter`
- `--observation-concurrency 4`

Command:

```bash
AGENT_MAX_WEB_QUERIES=0 AGENT_LLM_PROVIDER=openrouter \
  uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/run_live_digest_model_comparison.py \
    --provider openrouter \
    --model qwen/qwen3.6-plus \
    --observation-concurrency 4 \
    --output-json _evals/reports/openrouter_structured_qwen_digest_shadow_validation_aggregate_2026-06-03_run1.json \
    --output-md _evals/reports/openrouter_structured_qwen_digest_shadow_validation_aggregate_2026-06-03_run1.md
```

Result:

```text
_evals/reports/openrouter_structured_qwen_digest_shadow_validation_aggregate_2026-06-03_run1.json
_evals/reports/openrouter_structured_qwen_digest_shadow_validation_aggregate_2026-06-03_run1.md
```

### Current Full Run Metrics

| Metric | Value |
| --- | --- |
| total observations | `16` |
| schema-valid proposals | `12/16` |
| fallback proposals | `4/16` |
| malformed JSON | `0` |
| validation errors | `4/16` |
| provider errors | `0` |
| raw response persisted | `0` |
| validation aggregate | `related_concern_ids.0 | int_parsing | 4` |

### Difference From Previous `10/16` Structured Run

| Metric | Previous | Current | Delta |
| --- | --- | --- | --- |
| schema-valid proposals | `10/16` | `12/16` | `+2` |
| validation errors | `6/16` | `4/16` | `-2` |
| provider errors | `0` | `0` | no change |
| malformed JSON | `0` | `0` | no change |

### Interpretation

The remaining failure is concentrated in one schema condition: `related_concern_ids` contains at least one item that Pydantic cannot parse as `int`. Because raw model response text is not persisted, the artifact does not identify whether the item was an object, string label, empty string, or other value. The important conclusion is narrower: qwen is generating valid JSON objects with the required top-level fields more often than the previous run, but it still violates the typed array item contract.

### Next Step

Schema/prompt hardening is still needed before another full eval. Do not relax Pydantic validation. The likely next small probe should keep `max_tokens`, `response_format=json_schema`, `structured_outputs=true`, and `provider.require_parameters=true`, then test one of:

- remove `maxLength` / `maxItems` from request schema only
- keep schema unchanged but strengthen the prompt to explicitly enumerate all required keys
- compare a smaller digest-like schema that preserves enums and arrays but reduces optional-looking text fields

## Addendum: `related_concern_ids` Prompt Hardening Probe

Date: 2026-06-03

The prompt was minimally hardened for the observed aggregate failure:

- `related_concern_ids` must always be an array for every decision.
- Only numeric concern IDs from `active_or_dormant_concerns` are allowed.
- `concern#1` means output `1`, not `"concern#1"`.
- Example: `[1, 3]`.
- Concern titles, objects, string labels, `"none"`, and `"unknown"` are forbidden.
- No related concern or uncertainty must be represented as `[]`.

No schema, Pydantic gate, coercion, sanitizer, repair path, production final digest path, `AGENT_DIGEST_DECIDER` default, or `llm_assisted` behavior was changed.

Command:

```bash
AGENT_MAX_WEB_QUERIES=0 AGENT_LLM_PROVIDER=openrouter \
  uv run --python /home/penne/.local/bin/python3.12 python _evals/scripts/run_live_digest_model_comparison.py \
    --provider openrouter \
    --model qwen/qwen3.6-plus \
    --observation-concurrency 4 \
    --output-json _evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run1.json \
    --output-md _evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run1.md
```

Result:

```text
_evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run1.json
_evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run1.md
```

### Prompt-Hardened Full Run Metrics

| Metric | Previous aggregate diagnostic | Current prompt-hardened run | Delta |
| --- | --- | --- | --- |
| schema-valid proposals | `12/16` | `16/16` | `+4` |
| fallback proposals | `4/16` | `0/16` | `-4` |
| malformed JSON | `0` | `0` | no change |
| validation errors | `4/16` | `0/16` | `-4` |
| provider errors | `0` | `0` | no change |
| raw response persisted | `0` | `0` | no change |
| validation aggregate | `related_concern_ids.0 | int_parsing | 4` | `[]` | fixed in this run |

### Interpretation

The targeted prompt hardening removed the observed `related_concern_ids.0 | int_parsing` failure in this one full qwen run while preserving provider error `0`, malformed JSON `0`, raw response persisted `0`, and the validation aggregate artifact. This is `PASS` for the prompt-hardening probe.

This was still not `llm_assisted` readiness at the time of the single-run probe. It was prerequisite evidence for the readiness gate only; run-to-run stability and adoption criteria remained under `Core-Test-18`.

## Addendum: Prompt-Hardened Variance Evidence

Date: 2026-06-03

Two additional full qwen runs were executed under the same conditions as the clean prompt-hardened run:

- `AGENT_MAX_WEB_QUERIES=0`
- `AGENT_LLM_PROVIDER=openrouter`
- model `qwen/qwen3.6-plus`
- `--observation-concurrency 4`
- `token_parameter=max_tokens`
- `response_format.type=json_schema`
- `structured_outputs=true`
- `provider.require_parameters=true`

Artifacts:

```text
_evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run2.json
_evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run2.md
_evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run3.json
_evals/reports/openrouter_structured_qwen_digest_shadow_related_concern_ids_prompt_hardening_2026-06-03_run3.md
```

### Three-Run Metrics

| Metric | run1 | run2 | run3 |
| --- | --- | --- | --- |
| schema-valid proposals | `16/16` | `16/16` | `16/16` |
| fallback proposals | `0/16` | `0/16` | `0/16` |
| malformed JSON | `0` | `0` | `0` |
| validation errors | `0` | `0` | `0` |
| provider errors | `0` | `0` | `0` |
| raw response persisted | `0` | `0` | `0` |
| validation aggregate | `[]` | `[]` | `[]` |
| model / normalized `should_apply=true` | `0 / 0` | `0 / 0` | `0 / 0` |
| action candidates | `1` | `1` | `1` |
| elapsed | `121.5s` | `115.8s` | `124.1s` |

### Current Interpretation

The three prompt-hardened qwen structured runs satisfy the `llm_assisted` readiness gate's repeated clean structured-output evidence requirement. This moves the readiness gate to `GO` for a future limited assisted-mode design task.

This does not implement or enable `llm_assisted`, does not change production final digest decision behavior, does not change `AGENT_DIGEST_DECIDER` default, does not change Discord/Web search behavior, does not relax the Pydantic gate, and does not persist raw provider responses. The repeated `action_candidate_count=1` remains outside assisted auto-adoption because model and normalized `should_apply=true` are both `0` in all three runs.
