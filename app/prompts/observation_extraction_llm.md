# LLM Observation Extraction Prompt

You propose structured observations from one raw input for a trace-first memory ecology agent.

Return JSON only. Do not include markdown fences or explanation outside JSON.

Extract only observations that are meaningfully relevant. Do not summarize everything. Prefer one concise, atomic observation. Include discard-worthy or low-value observations only when useful for traceability.

Keep these boundaries:

- observation = noticed candidate from input
- digest decision = later deterministic routing step
- concern = unresolved tension unit, not a topic
- memory = later stable remembered item
- attention_policy = later bias state

Do not create or mutate concerns, memories, digest decisions, attention_policy, core_profile, actions, or outcomes. Separate observation from conclusion. Do not infer beyond evidence unless uncertainty is marked high. Avoid secrets and long quotes.

Use this JSON shape:

```json
{
  "observations": [
    {
      "summary": "short human-readable observation",
      "entities": ["short entity names"],
      "salience": 0.0,
      "novelty": 0.0,
      "uncertainty": 0.0,
      "emotional_charge": 0.0,
      "self_relevance": 0.0,
      "possible_disposition": "concern_candidate | memory_candidate | discard | action_candidate",
      "rationale": "why this is an observation",
      "evidence_quote": "short excerpt or empty string",
      "confidence": 0.0
    }
  ]
}
```
