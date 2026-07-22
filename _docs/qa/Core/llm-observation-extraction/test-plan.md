---
title: "QA Test Plan: LLM Observation Extraction"
status: active
draft_status: n/a
qa_status: planned
risk: Medium
created_at: 2026-06-02
updated_at: 2026-06-02
references:
  - "_docs/intent/Core/llm-observation-extraction/decision.md"
  - "_docs/plan/Core/llm-observation-extraction/plan.md"
related_issues: []
related_prs: []
---

# QA Test Plan: `LLM Observation Extraction`

## Source of Intent

- TODO: `Core-Feat-11`
- Plan: `_docs/plan/Core/llm-observation-extraction/plan.md`
- Intent: `_docs/intent/Core/llm-observation-extraction/decision.md`

## Quality Goal

LLM を observation proposal にだけ opt-in 導入し、default offline behavior、deterministic downstream pipeline、安全な fallback trace を維持する。

## Acceptance Criteria

- AC-001: 既定設定と CI は deterministic observation extractor を使い、real provider credential を要求しない。
- AC-002: `AGENT_OBSERVATION_EXTRACTOR=llm` のときだけ LLM observation extraction が走る。
- AC-003: LLM extractor は validated `ObservationDraft` proposal だけを返し、concern / memory / digest decision / attention_policy / core_profile / action / outcome を直接変更しない。
- AC-004: LLM output は JSON schema validation、score clamp、disposition allowlist、summary / evidence quote length limit を通過したものだけ採用される。
- AC-005: missing credentials、provider error、invalid JSON、schema validation error、unsafe output では raw provider response を保存せず、deterministic fallback と traceable warning を残す。
- AC-006: observation / digest trace から extractor と provider が deterministic / llm / fallback のどれだったか確認できる。
- AC-007: OpenRouter / `deepseek/deepseek-v4-pro` の live-test 手順は docs に残すが、自動検証や既定動作にはしない。

## Intent-derived Invariants

- INV-001: 既定設定では real provider call が発生せず、deterministic extractor が使われる。
- INV-002: LLM extractor は `ObservationDraft` proposal 以外の DB row を直接作成・更新しない。
- INV-003: unsupported disposition、invalid JSON、schema validation error、provider/config error は raw response persistence なしに deterministic fallback または strict error になる。
- INV-004: score fields は 0.0 から 1.0 に収まり、summary / rationale / evidence quote は bounded length になる。
- INV-005: digest trace metadata は extractor mode、provider、fallback status を secret なしで示す。
- INV-006: OpenRouter live usage は manual opt-in であり、CI / default path / Discord / Web search を有効化しない。

## Risk Assessment

- Risk level: Medium
- Risk rationale: cognition loop の入口に feature flag と provider call path を追加するため。
- Regression risk: default deterministic wake behavior、digest trace metadata、provider mock/offline CI が壊れる可能性。
- Data safety risk: raw provider response や長い quote を保存すると外部入力・secret 周辺情報を残す可能性。
- Security / privacy risk: API key や Authorization header を trace しないことが必須。
- UX risk: CLI の既定 wake が provider credential 欠落で crash しないこと。
- Agent misbehavior risk: LLM に downstream mutation を任せる、または docs なしに real provider を既定化するリスク。

## Test Strategy

- Unit: validation helper と LLM success/fallback を fake client で確認する。
- Integration: `run_wake_cycle` の default deterministic と opt-in LLM/fallback metadata を確認する。
- E2E: live provider は任意 manual QA とし、自動実行しない。
- Manual QA: OpenRouter / `deepseek/deepseek-v4-pro` 手順を README / reference で確認する。
- Validator / static check: `uv run --python /home/penne/.local/bin/python3.12 pytest` と `./scripts/check-docs.sh`。
- Diff review: LLM path が concern / memory / policy / core / Discord / Web search を直接変更していないことを確認する。

## Test Matrix

| ID | Source | Requirement / Invariant | Test Type | Command / File | Expected Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| AC-001 | TODO | default / CI は deterministic/offline。 | integration | `tests/test_observation_extractor.py`, `tests/test_wake_cycle.py` | default settings で extractor metadata が deterministic。 | planned |
| AC-002 | TODO | `AGENT_OBSERVATION_EXTRACTOR=llm` のときだけ LLM path。 | unit/integration | `tests/test_observation_extractor.py` | fake LLM client の proposal が observation に保存され、複数 proposal は個別に digest へ進む。 | planned |
| AC-003 | TODO | LLM は proposal-only。 | diff review/integration | `app/cognition/observation_extractor.py`, `app/runtime/wake_cycle.py` | LLM function は `ObservationDraft` を返し、DB write は existing runtime persistence のみ。 | planned |
| AC-004 | TODO | schema validation と bounds。 | unit | `tests/test_observation_extractor.py` | score clamp、unsupported disposition fallback、bounded text を確認。 | planned |
| AC-005 | TODO | failure は deterministic fallback と safe warning。 | unit/integration | `tests/test_observation_extractor.py` | provider/config/validation failure で fallback metadata、raw response 未保存。 | planned |
| AC-006 | TODO | extractor/provider trace が確認できる。 | integration | `tests/test_observation_extractor.py` | observation rationale と digest metadata に sanitized extractor info。 | planned |
| AC-007 | TODO | OpenRouter live test は manual opt-in。 | docs/validator | `README.md`, `_docs/reference/Core/memory-ecology-poc/reference.md` | live command は explicit env var 付きで記載され、CI required ではない。 | planned |
| INV-001 | intent | default は real provider call なし。 | unit/integration | `tests/test_observation_extractor.py` | default path は LLM client を作らない。 | planned |
| INV-002 | intent | LLM は proposal 以外を直接 mutate しない。 | diff review | `app/cognition/observation_extractor.py` | session / models の downstream write がない。 | planned |
| INV-003 | intent | failure は raw response persistence なし。 | unit | `tests/test_observation_extractor.py` | raw invalid provider text が observation/digest に含まれない。 | planned |
| INV-004 | intent | score/text bounds。 | unit | `tests/test_observation_extractor.py` | values and text lengths are bounded. | planned |
| INV-005 | intent | safe trace metadata。 | integration | `tests/test_observation_extractor.py` | provider / fallback status only; no key/header/raw payload。 | planned |
| INV-006 | intent | live OpenRouter は manual opt-in。 | docs/validator | `README.md` | docs state no default provider usage. | planned |

## Manual QA Checklist

- [ ] README の LLM observation extraction 手順が explicit opt-in になっている。
- [ ] OpenRouter / `deepseek/deepseek-v4-pro` 手順が isolated project root での任意 live test として書かれている。
- [ ] CI / default path が real provider credential を必要としないことが明記されている。

## Regression Checklist

- [ ] default `wake` が既存 deterministic trace vertical を維持する。
- [ ] provider smoke command の既存 docs / tests を壊していない。
- [ ] Discord mode と Web search stub に変更がない。

## High-risk Checklist

Use this section only for Risk High / Critical.

- [ ] Not applicable. Risk is Medium.

## Out of Scope

- LLM-backed digest decisions。
- real Web search。
- Discord operational mode changes。
- raw provider response persistence。

## Open Questions

- None
