---
title: "QA Test Plan: LLM Digest Live Runner Hardening"
status: active
draft_status: n/a
qa_status: planned
risk: Medium
created_at: 2026-06-02
updated_at: 2026-06-03
references:
  - "_docs/intent/Core/llm-digest-live-runner-hardening/decision.md"
  - "_docs/plan/Core/llm-digest-live-runner-hardening/plan.md"
  - "_docs/qa/Core/llm-digest-live-runner-hardening/verification.md"
related_issues: []
related_prs: []
---

# QA Test Plan: `LLM Digest Live Runner Hardening`

## Source of Intent

- TODO: `Core-Enhance-15`
- Plan: `_docs/plan/Core/llm-digest-live-runner-hardening/plan.md`
- Intent: `_docs/intent/Core/llm-digest-live-runner-hardening/decision.md`

## Quality Goal

Live digest proposal evaluation runner が、provider / schema の失敗を早期に検出しつつ、問題がない場合は bounded concurrency で効率的に複数モデルを評価できる。

## Acceptance Criteria

- AC-001: 複数モデルを指定して live `llm_shadow` evaluation を実行できる runner が存在する。
- AC-002: runner は初期 safe batch を小さく実行し、重大な provider/schema 問題がなければ bounded concurrency で残りを実行する。
- AC-003: モデル単位の完了結果を逐次 flush し、長時間直列実行中の不可視時間を減らす。
- AC-004: JSON decode / schema validation / provider / timeout / orchestration failure の原因分類が report と JSON output に残る。
- AC-005: raw provider response と secrets を保存・表示せず、isolated temp root、final deterministic decision、no Web search、Discord disabled の安全境界を維持する。
- AC-006: 明示 opt-in diagnostic mode だけが、失敗ケースの raw response content を通常 artifact から分離した dedicated JSON に保存できる。

## Intent-derived Invariants

- INV-001: Runner は final digest decision を deterministic のまま維持し、`llm_assisted` adoption を実装しない。
- INV-002: Runner は raw provider response と secrets を report / JSON / stdout に出力しない。
- INV-007: Diagnostic raw capture は eval/probe artifact に限定され、production final digest decision path、DB raw persistence、Discord/Web search、`llm_assisted` adoption を変更しない。
- INV-003: Runner は safe batch を先に完了させてから bounded concurrency へ進む。
- INV-004: Runner はモデル単位の結果を逐次 flush する。
- INV-005: Runner は failure cause を provider / JSON / schema / timeout / orchestration / safety boundary に分類する。
- INV-006: Real provider run は optional であり、CI の必須条件にしない。

## Risk Assessment

- Risk level: Medium
- Risk rationale: Evaluation workflow の挙動を追加し、外部 provider を任意で扱う。
- Regression risk: Low。runtime default は変更しない。
- Data safety risk: Medium。raw provider output と credential の非保存を確認する。
- Security / privacy risk: Medium。secret は env var の存在確認だけに留める。
- Agent misbehavior risk: Medium。evaluation と active adoption を混同しないことを確認する。

## Test Strategy

- Unit: failure cause classifier and safe batch gate.
- Offline integration: fake client / mock provider で multi-model runner を実行する。
- Validator: `./scripts/check-docs.sh`。
- Diff review: runtime adoption、Discord/Web mode、raw response persistence がないことを確認する。
- Manual QA: optional OpenRouter smoke。credential が明示されている場合のみ実行する。

## Test Matrix

| ID | Source | Requirement / Invariant | Test Type | Command / File | Expected Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| AC-001 | TODO | Multiple models can be evaluated by one runner. | integration | `tests/test_live_digest_runner.py` | Fake multi-model run returns one result per model. | verified |
| AC-002 | TODO | Safe batch gates bounded concurrency. | unit | `tests/test_live_digest_runner.py` | Remaining models are skipped when safe batch has severe failures; otherwise bounded phase runs. | verified |
| AC-003 | TODO | Results are flushed per model. | integration | `tests/test_live_digest_runner.py` | Output JSON contains partial result after each completed model. | verified |
| AC-004 | TODO | Failure causes are classified. | unit | `tests/test_live_digest_runner.py` | JSON/schema/provider/timeout/orchestration causes are counted. | verified |
| AC-005 | TODO | Safety boundaries are maintained. | integration / diff review | runner report and `git diff -- app _evals tests _docs TODO.md` | No raw response in standard artifacts, no secrets, isolated temp roots, no Web search, Discord disabled, final deterministic decisions. | verified |
| AC-006 | TODO | Raw diagnostic capture is explicit opt-in and separated. | unit / live diagnostic | `tests/test_live_digest_runner.py`; DeepSeek diagnostic artifacts | Dedicated `.raw.json` files contain only failed redacted raw content; standard JSON/Markdown keep `raw_provider_response_persisted=false`. | verified |
| INV-001 | intent | No active adoption is implemented. | diff review | `git diff -- app _evals tests _docs TODO.md` | `AGENT_DIGEST_DECIDER` default and final digest path are unchanged. | verified |
| INV-002 | intent | Raw provider response and secrets are not output. | static / integration | `tests/test_live_digest_runner.py` | Report/output omit raw response text and credential values. | verified |
| INV-003 | intent | Safe batch precedes bounded concurrency. | unit | `tests/test_live_digest_runner.py` | Event order records safe phase before bounded phase. | verified |
| INV-004 | intent | Per-model flush exists. | integration | `tests/test_live_digest_runner.py` | Flush writer is called after each model result. | verified |
| INV-005 | intent | Failure causes are classified. | unit | `tests/test_live_digest_runner.py` | Cause distribution includes expected categories. | verified |
| INV-006 | intent | Real provider is optional. | docs / integration | runner CLI help and test config | Offline fake path works without `OPENROUTER_API_KEY`. | verified |
| INV-007 | intent | Diagnostic capture does not change production/default/adoption boundaries. | diff review / live diagnostic | `app/cognition/digest_decider.py`; runner artifacts | Callback defaults to disabled; DB proposals still record `raw_response_persisted=false`; `llm_assisted` and runtime defaults are unchanged. | verified |

## Manual QA Checklist

- [ ] Run optional OpenRouter smoke only if `OPENROUTER_API_KEY` is explicitly present.
- [x] Confirm stdout / report does not include raw provider response text.
- [x] Confirm long live runs show per-model completion progress.
- [x] Confirm raw diagnostic capture, when explicitly enabled, writes a dedicated artifact and captures only failed proposal outputs.

## Regression Checklist

- [x] Existing digest proposal tests still pass.
- [x] Full pytest suite still passes.
- [x] Docs validator still passes.

## Out of Scope

- Active `llm_assisted` adoption.
- CI real provider benchmark.
- Provider-specific rate-limit tuning beyond bounded concurrency.

## Open Questions

- Which severe failure threshold should be used for larger model sets after the first few live runs?
