---
title: LLM Digest Proposal Quality Evaluation Plan
status: active
draft_status: n/a
created_at: 2026-06-02
updated_at: 2026-06-02
references:
  - "_docs/intent/Core/llm-digest-proposal-quality-evaluation/decision.md"
  - "_docs/qa/Core/llm-digest-proposal-quality-evaluation/test-plan.md"
  - "_docs/qa/Core/llm-digest-decision-proposals/verification.md"
  - "_evals/reports/llm_digest_proposal_quality_2026-06-02.md"
related_issues: []
related_prs: []
---

## Overview

`llm_shadow` で保存される digest proposal を sample world 上で評価し、deterministic final decision と比較する。目的は、active `llm_assisted` adoption rule を実装する前に、agreement / disagreement / fallback / unsafe rejection の傾向を evidence として残すことである。

## Scope

- isolated project root と sample world fixture で `llm_shadow` を実行する。
- proposal と final digest decision の agreement / disagreement を集計する。
- disagreement 例を分類し、LLM proposal を採用すべきでないケースを明確にする。
- `llm_assisted` を実装するか、shadow 継続に留めるかの判断を intent に残す。

## Non-Goals

- このタスク内で `llm_assisted` を実装しない。
- real provider を CI 必須にしない。
- raw provider response を保存しない。

## Requirements

- **Functional**: comparison report が deterministic final decision、LLM proposal、agreement、fallback を含む。
- **Functional**: representative disagreement examples が分類される。
- **Non-Functional**: real provider usage は optional manual smoke に留め、CI は offline を維持する。

## Tasks

- sample world / fixture run の実行条件を決める。
- report script または notebook 相当の軽量集計を作る。
- disagreement examples と adoption constraints を survey / intent に記録する。
- QA verification に executed commands と skipped manual live smoke を残す。

## QA Plan

- QA document: `_docs/qa/Core/llm-digest-proposal-quality-evaluation/test-plan.md`
- Risk level: Medium
- Test strategy:
  - Integration: fixture run and report generation.
  - Manual QA: optional real provider run if credentials are explicitly configured.
  - Validator / static check: `./scripts/check-docs.sh`.

## Deployment / Rollout

Production rollout はない。評価後、active `llm_assisted` implementation に進む場合は別 TODO として扱う。
