---
title: LLM Digest Proposal Quality Evaluation 2026-06-02
status: active
draft_status: n/a
created_at: 2026-06-02
updated_at: 2026-06-02
references:
  - "_docs/intent/Core/llm-digest-proposal-quality-evaluation/decision.md"
  - "_docs/qa/Core/llm-digest-proposal-quality-evaluation/test-plan.md"
related_issues: []
related_prs: []
---

# LLM Digest Proposal Quality Evaluation

## Verdict

Recommendation: `KEEP_SHADOW_AND_COLLECT_MORE`.

This report contains an offline rubric-control rerun and a fresh live OpenRouter / `deepseek/deepseek-v4-pro` shadow evaluation. The live run improved JSON adherence and kept proposal safety boundaries intact, but it is still not sufficient evidence to implement active `llm_assisted` adoption.

Safe future direction: keep `llm_shadow`; allow no automatic `action_candidate`; never allow core/self_model updates from a digest proposal; collect more live runs before considering any assisted-mode design.

## Run Configuration

- deterministic temp root: `/tmp/digest-proposal-eval-8ov55b1k`
- shadow temp root: `/tmp/digest-proposal-eval-cbsv1j_l`
- fixture world: `/home/penne/dev/active/memory_ecology_agent/_evals/fixtures/memory_ecology_sample_world/world`
- digest proposal prompt version: `digest_decision_llm.v3`
- deterministic command equivalent: `AGENT_DIGEST_DECIDER=deterministic python -m app.main --project-root <tmp> wake --reason digest-quality-deterministic-baseline`
- shadow command equivalent: `AGENT_DIGEST_DECIDER=llm_shadow AGENT_LLM_PROVIDER=mock python -m app.main --project-root <tmp> wake --reason digest-quality-llm-shadow-mock`
- live v4pro status: `COMPLETED_openrouter_deepseek-v4-pro`

## Pre/Post Context

Previous offline evaluation recommended `PROMPT_HARDENING_FIRST`. This report is the post-hardening offline mock rerun. The comparison is qualitative because the offline fake client is a rubric control, not a live model.

## Metrics

| Metric | Value |
| --- | --- |
| `total_observations` | `16` |
| `total_deterministic_decisions` | `16` |
| `total_llm_proposals` | `16` |
| `schema_valid_proposals` | `16` |
| `rejected_or_fallback_proposals` | `0` |
| `malformed_json_count` | `0` |
| `validation_error_count` | `0` |
| `provider_error_count` | `0` |
| `agreement_count` | `10` |
| `disagreement_count` | `6` |
| `agreement_rate` | `0.625` |
| `llm_proposed_distribution` | `{'concern_candidate': 4, 'memory_candidate': 7, 'discard': 4, 'action_candidate': 1, 'no_op': 0}` |
| `final_decision_distribution` | `{'concern_candidate': 8, 'memory_candidate': 5, 'discard': 3, 'action_candidate': 0, 'no_op': 0}` |
| `action_candidate_count` | `1` |
| `memory_vs_concern_disagreement_count` | `3` |
| `discard_vs_memory_disagreement_count` | `1` |
| `llm_concern_final_discard` | `0` |
| `llm_discard_final_concern_or_memory` | `2` |
| `average_confidence_by_decision` | `{'action_candidate': 0.62, 'concern_candidate': 0.8, 'discard': 0.86, 'memory_candidate': 0.767}` |
| `confidence_distribution` | `{'0.55-0.74': 3, '0.75-0.89': 13}` |
| `risk_flags_distribution` | `{'core_profile_boundary': 1, 'low_signal': 4, 'manual_follow_up': 1, 'possible_over_action': 1, 'repetition': 4, 'safety_boundary': 1, 'stable_fact': 4, 'traceability': 1, 'unresolved_tension': 2, 'user_feedback': 2}` |
| `model_should_apply_true_count` | `4` |
| `normalized_should_apply_true_count` | `0` |
| `normalization_reason_distribution` | `{'confidence_below_threshold': 11, 'decision_not_auto_applicable': 5}` |
| `unknown_concern_id_count` | `0` |
| `raw_response_persisted_count` | `0` |

## Baseline Counts

- deterministic observations: `16`
- deterministic digest decisions: `16`
- deterministic concerns: `6`
- deterministic memories: `13`
- shadow wake result: `{'probes': 1, 'raw_events': 16, 'observations': 16, 'concerns': 6, 'memories': 13, 'actions': 2, 'outcomes': 2, 'attention_policy_version': 3, 'wake_requests': 1}`

## Qualitative Samples

### Agreement Examples

- observation#3: User feedback samples The user disliked shallow agreement, thin assertions, and self-centered explanations that were not grounded in evidence. Future response selection should trea
  - deterministic final: `memory_candidate`
  - LLM proposed: `memory_candidate`
  - reason: This is reusable user-feedback evidence, not necessarily an open concern.
  - confidence: 0.78
  - risk_flags: `['user_feedback']`
  - model_should_apply: `True`
  - normalized_should_apply: `False`
  - normalization_reason: `confidence_below_threshold`
  - agreement: `True`
  - evaluator note: 一致例。offline fake では deterministic の判断を崩す必要が薄いケースとして扱った。
- observation#5: blue chair receipt window a small ambient note with no active tension
  - deterministic final: `discard`
  - LLM proposed: `discard`
  - reason: The observation is repetitive or low-value ambient material.
  - confidence: 0.86
  - risk_flags: `['low_signal', 'repetition']`
  - model_should_apply: `False`
  - normalized_should_apply: `False`
  - normalization_reason: `confidence_below_threshold`
  - agreement: `True`
  - evaluator note: 一致例。offline fake では deterministic の判断を崩す必要が薄いケースとして扱った。
- observation#6: blue chair receipt window a small ambient note with no active tension
  - deterministic final: `discard`
  - LLM proposed: `discard`
  - reason: The observation is repetitive or low-value ambient material.
  - confidence: 0.86
  - risk_flags: `['low_signal', 'repetition']`
  - model_should_apply: `False`
  - normalized_should_apply: `False`
  - normalization_reason: `confidence_below_threshold`
  - agreement: `True`
  - evaluator note: 一致例。offline fake では deterministic の判断を崩す必要が薄いケースとして扱った。

### Disagreement Examples

- observation#1: Memory and identity Identity in this PoC is treated as an ecological loop: attention selects inputs, observations become memories or concerns, actions produce outcomes, and outcome
  - deterministic final: `concern_candidate`
  - LLM proposed: `memory_candidate`
  - reason: This is a stable explanatory fact about the PoC frame.
  - confidence: 0.77
  - risk_flags: `['stable_fact']`
  - model_should_apply: `False`
  - normalized_should_apply: `False`
  - normalization_reason: `confidence_below_threshold`
  - agreement: `False`
  - evaluator note: LLM の方が安定事実として切り出しており、deterministic の過 concern 傾向を示す候補。
- observation#2: User correction example When the user corrects the agent, future response selection should treat the correction as strong evidence for risk review.
  - deterministic final: `concern_candidate`
  - LLM proposed: `memory_candidate`
  - reason: This is reusable user-feedback evidence, not necessarily an open concern.
  - confidence: 0.78
  - risk_flags: `['user_feedback']`
  - model_should_apply: `True`
  - normalized_should_apply: `False`
  - normalization_reason: `confidence_below_threshold`
  - agreement: `False`
  - evaluator note: LLM の方が安定事実として切り出しており、deterministic の過 concern 傾向を示す候補。
- observation#4: Action follow-up The digest quality evaluation still needs a short written recommendation after agreement and disagreement examples are reviewed. The next concrete action is to upd
  - deterministic final: `discard`
  - LLM proposed: `action_candidate`
  - reason: The text names a concrete bounded follow-up, but action proposals are weak suggestions only.
  - confidence: 0.62
  - risk_flags: `['manual_follow_up', 'possible_over_action']`
  - model_should_apply: `False`
  - normalized_should_apply: `False`
  - normalization_reason: `decision_not_auto_applicable`
  - agreement: `False`
  - evaluator note: 具体的 follow-up は拾えているが、LLM 単独で action adoption するには危険。

### Fallback / Rejected Examples

該当例なし。

### LLM Seems Better Than Deterministic

- observation#1: Memory and identity Identity in this PoC is treated as an ecological loop: attention selects inputs, observations become memories or concerns, actions produce outcomes, and outcome
  - deterministic final: `concern_candidate`
  - LLM proposed: `memory_candidate`
  - reason: This is a stable explanatory fact about the PoC frame.
  - confidence: 0.77
  - risk_flags: `['stable_fact']`
  - model_should_apply: `False`
  - normalized_should_apply: `False`
  - normalization_reason: `confidence_below_threshold`
  - agreement: `False`
  - evaluator note: LLM の方が安定事実として切り出しており、deterministic の過 concern 傾向を示す候補。
- observation#2: User correction example When the user corrects the agent, future response selection should treat the correction as strong evidence for risk review.
  - deterministic final: `concern_candidate`
  - LLM proposed: `memory_candidate`
  - reason: This is reusable user-feedback evidence, not necessarily an open concern.
  - confidence: 0.78
  - risk_flags: `['user_feedback']`
  - model_should_apply: `True`
  - normalized_should_apply: `False`
  - normalization_reason: `confidence_below_threshold`
  - agreement: `False`
  - evaluator note: LLM の方が安定事実として切り出しており、deterministic の過 concern 傾向を示す候補。

### Deterministic Seems Safer Than LLM

- observation#4: Action follow-up The digest quality evaluation still needs a short written recommendation after agreement and disagreement examples are reviewed. The next concrete action is to upd
  - deterministic final: `discard`
  - LLM proposed: `action_candidate`
  - reason: The text names a concrete bounded follow-up, but action proposals are weak suggestions only.
  - confidence: 0.62
  - risk_flags: `['manual_follow_up', 'possible_over_action']`
  - model_should_apply: `False`
  - normalized_should_apply: `False`
  - normalization_reason: `decision_not_auto_applicable`
  - agreement: `False`
  - evaluator note: 具体的 follow-up は拾えているが、LLM 単独で action adoption するには危険。
- observation#10: Random daily log Bought coffee, cleaned a keyboard, and noticed the train schedule changed. This note is ordinary background noise. It should probably become a weak memory at most,
  - deterministic final: `concern_candidate`
  - LLM proposed: `discard`
  - reason: The observation is repetitive or low-value ambient material.
  - confidence: 0.86
  - risk_flags: `['low_signal', 'repetition']`
  - model_should_apply: `False`
  - normalized_should_apply: `False`
  - normalization_reason: `confidence_below_threshold`
  - agreement: `False`
  - evaluator note: 判断境界が曖昧な例。追加の live proposal と人手評価が必要。

### Unclear Examples

- observation#11: Repeated low-value observations Coffee receipt, keyboard cleaning, window chair note. Coffee receipt, keyboard cleaning, window chair note. Coffee receipt, keyboard cleaning, windo
  - deterministic final: `memory_candidate`
  - LLM proposed: `discard`
  - reason: The observation is repetitive or low-value ambient material.
  - confidence: 0.86
  - risk_flags: `['low_signal', 'repetition']`
  - model_should_apply: `False`
  - normalized_should_apply: `False`
  - normalization_reason: `confidence_below_threshold`
  - agreement: `False`
  - evaluator note: LLM 側が低信号性をより強く見た可能性があるが、記憶として残す価値との境界は未確定。
- observation#16: PoC requirements The PoC must trace raw_events, input_probes, observations, concerns, concern_events, memories, actions, outcomes, attention_policies, attention_policy_events, core
  - deterministic final: `concern_candidate`
  - LLM proposed: `memory_candidate`
  - reason: The requirements are stable project facts, though they affect future checks.
  - confidence: 0.76
  - risk_flags: `['stable_fact', 'traceability']`
  - model_should_apply: `False`
  - normalized_should_apply: `False`
  - normalization_reason: `confidence_below_threshold`
  - agreement: `False`
  - evaluator note: LLM の方が安定事実として切り出しており、deterministic の過 concern 傾向を示す候補。

## Safety Checks

- raw response persisted count: `0`
- raw provider response text is not included in this report.
- secret-like value check is limited to persisted proposal fields and the script output; live provider was not used.
- final digest decisions remained deterministic; proposals only populated `digest_decision_proposals`.

## Recommendation Detail

- Keep `llm_shadow`; do not implement active `llm_assisted` adoption from this report alone.
- Treat agreement rate as secondary. Boundary behavior is the main signal.
- Stable project/user facts that LLM proposes as memory candidates are useful review candidates for deterministic over-concern behavior.
- Do not adopt `action_candidate` from LLM alone.
- Do not allow proposals to mutate `core_profile`, `self_model`, Discord mode, or final digest decisions.
- Re-run live `openrouter` / `deepseek/deepseek-v4-pro` only with explicit provider, model, and credential configuration.

## Live OpenRouter v4pro Addendum

This addendum records a live OpenRouter run after prompt v3 and deterministic `should_apply` normalization. It used an isolated temp project root and the sample world fixture. It did not implement `llm_assisted`, did not change the default digest decider, did not enable Discord mode, and did not persist raw provider responses.

### Live Run Configuration

- temp root: `/tmp/digest-proposal-live-v4pro-gj_wbpbm`
- provider: `openrouter`
- model: `deepseek/deepseek-v4-pro`
- digest decider: `llm_shadow`
- prompt version: `digest_decision_llm.v3`
- Web search: disabled by environment (`AGENT_MAX_WEB_QUERIES=0`)
- command shape: `AGENT_LLM_PROVIDER=openrouter AGENT_LLM_MODEL=deepseek/deepseek-v4-pro AGENT_DIGEST_DECIDER=llm_shadow AGENT_MAX_WEB_QUERIES=0 uv run --python /home/penne/.local/bin/python3.12 python - <<'PY' ...`

### Live Metrics

| Metric | Value |
| --- | --- |
| total observations | `16` |
| total proposals | `16` |
| schema-valid proposals | `15` |
| rejected/fallback proposals | `1` |
| malformed JSON count | `0` |
| validation error count | `1` |
| provider error count | `0` |
| agreement count | `10` |
| disagreement count | `5` |
| agreement rate | `0.667` |
| proposed distribution | `concern_candidate=5`, `memory_candidate=6`, `discard=4`, `action_candidate=0`, `no_op=0` |
| final distribution | `concern_candidate=8`, `memory_candidate=5`, `discard=3`, `action_candidate=0`, `no_op=0` |
| action_candidate count | `0` |
| model_should_apply=true count | `3` |
| normalized should_apply=true count | `3` |
| confidence distribution | `0.55-0.74=2`, `0.75-0.89=9`, `0.90-1.00=4` |
| risk flag distribution | `ambiguous_discard_vs_memory=3`, `ambiguous_memory_vs_concern=7`, `low_signal=4`, `possible_over_concern=1`, `project_requirement=2`, `repetition=1`, `self_model_boundary=2`, `stable_fact=6`, `traceability=1`, `unknown_context=2`, `unresolved_tension=5`, `user_feedback=1` |
| normalization reasons | `allowed_discard=2`, `allowed_memory=1`, `blocked_risk_flag=1`, `confidence_below_threshold=6`, `decision_not_auto_applicable=5` |
| raw response persisted count | `0` |
| core_profile unchanged | `true` |
| Discord enabled | `false` |

### Live Qualitative Examples

- Stable project frame: final `concern_candidate`, proposed `memory_candidate`, confidence `0.78`, flags `stable_fact`, `ambiguous_memory_vs_concern`, normalized false. This is a useful over-concern review case, not an adoption signal.
- User correction example: proposal was rejected by schema validation once. This is safe fallback behavior, but it means JSON/schema adherence is not perfect.
- Low-signal receipt examples: proposed `discard` with confidence `0.90` and `0.92`; normalized true in two direct low-signal cases.
- Repeated low-value observation: model proposed `discard` at `0.92`, but `ambiguous_discard_vs_memory` blocked normalization.
- PoC requirements: model proposed `memory_candidate` while deterministic chose `concern_candidate`; normalized false because confidence was below threshold and ambiguity remained.

### Live Safety Checks

- final digest decisions remained deterministic: `PASS`
- `llm_shadow` remained proposal-only: `PASS`
- `llm_assisted` was not implemented or enabled: `PASS`
- malformed JSON fell back safely: `PASS` (none observed; validation error produced fallback)
- raw provider response persisted: `PASS` (`0`)
- secret values printed or persisted: `PASS` (no secret values emitted; only presence was checked)
- core_profile unchanged: `PASS`
- Discord mode unchanged: `PASS`
- real Web search: `PASS` (not used)

### Live Recommendation

Recommendation: `KEEP_SHADOW_AND_COLLECT_MORE`.

JSON adherence improved from the previous live run (`9/16` schema-valid, `4` malformed JSON, `3` validation errors) to `15/16` schema-valid with `0` malformed JSON and `1` validation error. `action_candidate` stayed at `0`, and deterministic normalization prevented ambiguous high-confidence cases from becoming applicable. Still, one live schema validation failure remains and the sample size is too small for assisted adoption design.
