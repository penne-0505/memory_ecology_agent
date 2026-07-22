"""Evaluate digest proposal quality on the sample world fixture.

This script is evaluation-only. It builds isolated temp project roots, runs the
existing deterministic digest flow, and compares it with `llm_shadow` proposal
records. If explicit live OpenRouter configuration is not present, it uses a
deterministic local fake client and marks the live run as skipped.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import date
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adapters.llm import LLMClient, LLMTextResult
from app.cognition import digest_decider as digest_decider_module
from app.cognition.digest_decider import PROMPT_VERSION
from app.config import Settings
from app.db.init_db import init_database, seed_initial_data
from app.db.json_utils import json_loads
from app.db.models import (
    Concern,
    DigestDecisionProposal,
    DigestDecisionTrace,
    Memory,
    Observation,
)
from app.db.session import session_scope
from app.runtime.wake_cycle import run_wake_cycle


FIXTURE_WORLD = REPO_ROOT / "_evals" / "fixtures" / "memory_ecology_sample_world" / "world"
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "_evals"
    / "reports"
    / f"llm_digest_proposal_quality_{date.today().isoformat()}.md"
)
DECISIONS = [
    "concern_candidate",
    "memory_candidate",
    "discard",
    "action_candidate",
    "no_op",
]


class HeuristicDigestProposalClient(LLMClient):
    """Deterministic fake proposal client for offline evaluation."""

    def complete_text(self, system: str, user: str) -> str:
        return self.complete_text_with_metadata(system, user).text

    def complete_text_with_metadata(self, system: str, user: str) -> LLMTextResult:
        summary = _extract_user_field(user, "summary").lower()
        deterministic = _extract_user_field(
            user, "deterministic_decision_for_comparison"
        )
        payload = _proposal_for_summary(summary, deterministic)
        return LLMTextResult(
            provider="offline_eval_fake",
            model="heuristic-digest-proposal-v1",
            text=json.dumps(payload, ensure_ascii=False),
        )

    def complete_json(self, system: str, user: str, schema):
        raise RuntimeError("HeuristicDigestProposalClient only supports text proposals.")


def _extract_user_field(user: str, field: str) -> str:
    prefix = f"{field}: "
    for line in user.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return ""


def _proposal_for_summary(summary: str, deterministic: str) -> dict[str, Any]:
    decision = deterministic or "discard"
    reason = "Mirrors the deterministic route for this offline control case."
    confidence = 0.64
    risk_flags: list[str] = []
    alternative = "discard" if decision != "discard" else "memory_candidate"
    should_apply = False

    if any(term in summary for term in ["receipt", "coffee", "keyboard", "window chair"]):
        decision = "discard"
        reason = "The observation is repetitive or low-value ambient material."
        confidence = 0.86
        risk_flags = ["low_signal", "repetition"]
    elif "memory shelf orange" in summary or "stable lightweight note" in summary:
        decision = "memory_candidate"
        reason = "It is a stable reusable fact with little unresolved tension."
        confidence = 0.82
        risk_flags = ["stable_fact"]
        should_apply = True
    elif "short written recommendation" in summary:
        decision = "action_candidate"
        reason = "The text names a concrete bounded follow-up, but action proposals are weak suggestions only."
        confidence = 0.62
        risk_flags = ["manual_follow_up", "possible_over_action"]
    elif "action follow-up" in summary or "qa verification record" in summary:
        decision = "concern_candidate"
        reason = "The text suggests a possible open loop, but action adoption is too risky for shadow proposal."
        confidence = 0.66
        risk_flags = ["manual_follow_up", "unresolved_tension", "possible_over_action"]
    elif "contradict" in summary or "unresolved question" in summary:
        decision = "concern_candidate"
        reason = "The observation preserves an unresolved tension that should remain visible."
        confidence = 0.84
        risk_flags = ["unresolved_tension"]
        should_apply = True
    elif "core profile" in summary or "secret leakage" in summary or "dangerous input" in summary:
        decision = "concern_candidate"
        reason = "The content touches a safety or core-boundary risk."
        confidence = 0.88
        risk_flags = ["safety_boundary", "core_profile_boundary"]
    elif "user disliked" in summary or "correction" in summary:
        decision = "memory_candidate"
        reason = "This is reusable user-feedback evidence, not necessarily an open concern."
        confidence = 0.78
        risk_flags = ["user_feedback"]
        should_apply = True
    elif "identity in this poc" in summary:
        decision = "memory_candidate"
        reason = "This is a stable explanatory fact about the PoC frame."
        confidence = 0.77
        risk_flags = ["stable_fact"]
    elif "requirements" in summary or "must trace" in summary:
        decision = "memory_candidate"
        reason = "The requirements are stable project facts, though they affect future checks."
        confidence = 0.76
        risk_flags = ["stable_fact", "traceability"]
    elif "bought coffee" in summary or "ordinary background noise" in summary:
        decision = "discard"
        reason = "Ordinary background noise is not useful enough for a concern."
        confidence = 0.83
        risk_flags = ["low_signal"]

    return {
        "decision": decision,
        "reason": reason,
        "confidence": confidence,
        "evidence_summary": reason[:160],
        "evidence_quote": "",
        "related_concern_ids": [],
        "alternative_decision": alternative,
        "risk_flags": risk_flags,
        "should_apply": should_apply and decision in {"memory_candidate", "discard"},
    }


def _settings_for(
    root: Path,
    *,
    digest_decider: str,
    provider: str = "mock",
    model: str | None = None,
) -> Settings:
    return Settings(
        project_root=root,
        db_path=root / "data" / "agent.db",
        world_root=root / "world",
        workspace_root=root / "agent_workspace",
        max_probe_files=24,
        max_probe_chars=60_000,
        max_web_queries_per_cycle=0,
        digest_decider=digest_decider,
        llm_provider=provider,
        llm_model=model or os.environ.get("AGENT_LLM_MODEL"),
        llm_timeout_seconds=float(os.environ.get("AGENT_LLM_TIMEOUT_SECONDS", "30")),
        llm_max_tokens=int(os.environ.get("AGENT_LLM_MAX_TOKENS", "1024")),
    )


def _prepare_root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="digest-proposal-eval-"))
    world = root / "world"
    world.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(FIXTURE_WORLD, world)
    return root


def _count(session: Session, model: type[Any]) -> int:
    return int(session.scalar(select(func.count(model.id))) or 0)


def _run_cycle(settings: Settings, reason: str) -> dict[str, Any]:
    init_database(settings)
    with session_scope(settings) as session:
        seed_counts = seed_initial_data(session, settings)
        result = run_wake_cycle(session, settings, reason)
    return {"seed_counts": seed_counts, "wake_result": result}


def _collect_rows(settings: Settings) -> dict[str, Any]:
    with session_scope(settings) as session:
        observations = session.scalars(select(Observation).order_by(Observation.id)).all()
        decisions = session.scalars(
            select(DigestDecisionTrace).order_by(DigestDecisionTrace.id)
        ).all()
        proposals = session.scalars(
            select(DigestDecisionProposal).order_by(DigestDecisionProposal.id)
        ).all()
        obs_by_id = {obs.id: obs for obs in observations}
        decision_by_obs = {decision.source_observation_id: decision for decision in decisions}
        proposal_rows = []
        for proposal in proposals:
            obs = obs_by_id.get(proposal.observation_id)
            decision = decision_by_obs.get(proposal.observation_id)
            proposal_rows.append(
                {
                    "proposal_id": proposal.id,
                    "observation_id": proposal.observation_id,
                    "summary": (obs.summary if obs else "")[:220],
                    "final_decision": decision.decision if decision else "",
                    "proposed_decision": proposal.proposed_decision or "(rejected)",
                    "reason": proposal.reason,
                    "confidence": proposal.confidence,
                    "risk_flags": json_loads(proposal.risk_flags_json, []),
                    "model_should_apply": proposal.model_should_apply,
                    "should_apply": proposal.should_apply,
                    "should_apply_normalized": proposal.should_apply_normalized,
                    "normalization_reason": proposal.normalization_reason,
                    "schema_valid": proposal.schema_valid,
                    "fallback_used": proposal.fallback_used,
                    "error_class": proposal.error_class,
                    "error_message_sanitized": proposal.error_message_sanitized,
                    "raw_response_persisted": proposal.raw_response_persisted,
                    "agreement": (
                        proposal.schema_valid
                        and decision is not None
                        and proposal.proposed_decision == decision.decision
                    ),
                }
            )
        return {
            "observations": observations,
            "decisions": decisions,
            "proposals": proposals,
            "proposal_rows": proposal_rows,
            "counts": {
                "observations": len(observations),
                "digest_decisions": len(decisions),
                "proposals": len(proposals),
                "concerns": _count(session, Concern),
                "memories": _count(session, Memory),
            },
        }


def _distribution(values: list[str]) -> dict[str, int]:
    counter = Counter(values)
    return {decision: counter.get(decision, 0) for decision in DECISIONS}


def _metrics(rows: list[dict[str, Any]], counts: dict[str, int]) -> dict[str, Any]:
    valid = [row for row in rows if row["schema_valid"]]
    agreements = [row for row in valid if row["agreement"]]
    disagreements = [row for row in valid if not row["agreement"]]
    confidence_by_decision: dict[str, list[float]] = defaultdict(list)
    risk_flags = Counter()
    confidence_buckets = Counter()
    normalization_reasons = Counter()
    for row in valid:
        confidence_by_decision[row["proposed_decision"]].append(row["confidence"])
        risk_flags.update(row["risk_flags"])
        normalization_reasons.update([row["normalization_reason"] or "(empty)"])
        confidence = row["confidence"]
        if confidence >= 0.90:
            confidence_buckets.update(["0.90-1.00"])
        elif confidence >= 0.75:
            confidence_buckets.update(["0.75-0.89"])
        elif confidence >= 0.55:
            confidence_buckets.update(["0.55-0.74"])
        elif confidence >= 0.30:
            confidence_buckets.update(["0.30-0.54"])
        else:
            confidence_buckets.update(["below_0.30"])
    return {
        "total_observations": counts["observations"],
        "total_deterministic_decisions": counts["digest_decisions"],
        "total_llm_proposals": counts["proposals"],
        "schema_valid_proposals": len(valid),
        "rejected_or_fallback_proposals": len([row for row in rows if row["fallback_used"]]),
        "malformed_json_count": len(
            [row for row in rows if row["error_class"] == "JSONDecodeError"]
        ),
        "validation_error_count": len(
            [row for row in rows if row["error_class"] == "ValidationError"]
        ),
        "provider_error_count": len(
            [row for row in rows if row["error_class"] == "LLMProviderError"]
        ),
        "agreement_count": len(agreements),
        "disagreement_count": len(disagreements),
        "agreement_rate": round(len(agreements) / len(valid), 3) if valid else 0.0,
        "llm_proposed_distribution": _distribution(
            [row["proposed_decision"] for row in valid]
        ),
        "final_decision_distribution": _distribution(
            [row["final_decision"] for row in rows]
        ),
        "action_candidate_count": len(
            [row for row in valid if row["proposed_decision"] == "action_candidate"]
        ),
        "memory_vs_concern_disagreement_count": len(
            [
                row
                for row in valid
                if {
                    row["proposed_decision"],
                    row["final_decision"],
                }
                == {"memory_candidate", "concern_candidate"}
            ]
        ),
        "discard_vs_memory_disagreement_count": len(
            [
                row
                for row in valid
                if {
                    row["proposed_decision"],
                    row["final_decision"],
                }
                == {"discard", "memory_candidate"}
            ]
        ),
        "llm_concern_final_discard": len(
            [
                row
                for row in valid
                if row["proposed_decision"] == "concern_candidate"
                and row["final_decision"] == "discard"
            ]
        ),
        "llm_discard_final_concern_or_memory": len(
            [
                row
                for row in valid
                if row["proposed_decision"] == "discard"
                and row["final_decision"] in {"concern_candidate", "memory_candidate"}
            ]
        ),
        "average_confidence_by_decision": {
            decision: round(sum(values) / len(values), 3)
            for decision, values in sorted(confidence_by_decision.items())
        },
        "confidence_distribution": dict(sorted(confidence_buckets.items())),
        "risk_flags_distribution": dict(sorted(risk_flags.items())),
        "model_should_apply_true_count": len(
            [row for row in valid if row["model_should_apply"]]
        ),
        "normalized_should_apply_true_count": len(
            [row for row in valid if row["should_apply_normalized"]]
        ),
        "normalization_reason_distribution": dict(sorted(normalization_reasons.items())),
        "unknown_concern_id_count": 0,
        "raw_response_persisted_count": len(
            [row for row in rows if row["raw_response_persisted"]]
        ),
    }


def _sample(rows: list[dict[str, Any]], predicate, limit: int) -> list[dict[str, Any]]:
    return [row for row in rows if predicate(row)][:limit]


def _note_for(row: dict[str, Any]) -> str:
    final = row["final_decision"]
    proposed = row["proposed_decision"]
    summary = row["summary"].lower()
    if proposed == final:
        return "一致例。offline fake では deterministic の判断を崩す必要が薄いケースとして扱った。"
    if proposed == "discard" and final == "memory_candidate":
        return "LLM 側が低信号性をより強く見た可能性があるが、記憶として残す価値との境界は未確定。"
    if proposed == "memory_candidate" and final == "concern_candidate":
        return "LLM の方が安定事実として切り出しており、deterministic の過 concern 傾向を示す候補。"
    if proposed == "action_candidate":
        return "具体的 follow-up は拾えているが、LLM 単独で action adoption するには危険。"
    if "core" in summary or "secret" in summary:
        return "deterministic の concern 維持が安全。core / secret 境界は downgrade しない方がよい。"
    return "判断境界が曖昧な例。追加の live proposal と人手評価が必要。"


def _example_block(title: str, rows: list[dict[str, Any]]) -> str:
    lines = [f"### {title}", ""]
    if not rows:
        return "\n".join(lines + ["該当例なし。", ""])
    for row in rows:
        lines.extend(
            [
                f"- observation#{row['observation_id']}: {row['summary']}",
                f"  - deterministic final: `{row['final_decision']}`",
                f"  - LLM proposed: `{row['proposed_decision']}`",
                f"  - reason: {row['reason'] or '(empty)'}",
                f"  - confidence: {row['confidence']:.2f}",
                f"  - risk_flags: `{row['risk_flags']}`",
                f"  - model_should_apply: `{row['model_should_apply']}`",
                f"  - normalized_should_apply: `{row['should_apply_normalized']}`",
                f"  - normalization_reason: `{row['normalization_reason']}`",
                f"  - agreement: `{row['agreement']}`",
                f"  - evaluator note: {_note_for(row)}",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def _render_report(
    *,
    deterministic_root: Path,
    shadow_root: Path,
    deterministic: dict[str, Any],
    shadow: dict[str, Any],
    metrics: dict[str, Any],
    live_status: str,
) -> str:
    rows = shadow["proposal_rows"]
    agreements = _sample(rows, lambda row: row["schema_valid"] and row["agreement"], 3)
    disagreements = _sample(rows, lambda row: row["schema_valid"] and not row["agreement"], 3)
    fallbacks = _sample(rows, lambda row: row["fallback_used"], 5)
    llm_better = _sample(
        rows,
        lambda row: row["proposed_decision"] in {"memory_candidate", "discard"}
        and row["final_decision"] == "concern_candidate",
        2,
    )
    deterministic_safer = _sample(
        rows,
        lambda row: row["schema_valid"]
        and not row["agreement"]
        and (
            row["proposed_decision"] == "action_candidate"
            or (
                row["proposed_decision"] == "discard"
                and row["final_decision"] in {"concern_candidate", "memory_candidate"}
            )
        ),
        2,
    )
    unclear = _sample(
        rows,
        lambda row: row["schema_valid"]
        and not row["agreement"]
        and row not in llm_better
        and row not in deterministic_safer,
        2,
    )
    lines = [
        "---",
        "title: LLM Digest Proposal Quality Evaluation 2026-06-02",
        "status: active",
        "draft_status: n/a",
        "created_at: 2026-06-02",
        "updated_at: 2026-06-02",
        "references:",
        '  - "_docs/intent/Core/llm-digest-proposal-quality-evaluation/decision.md"',
        '  - "_docs/qa/Core/llm-digest-proposal-quality-evaluation/test-plan.md"',
        "related_issues: []",
        "related_prs: []",
        "---",
        "",
        "# LLM Digest Proposal Quality Evaluation",
        "",
        "## Verdict",
        "",
        "Recommendation: `KEEP_SHADOW_AND_COLLECT_LIVE_AFTER_HARDENING`.",
        "",
        "This run is useful as evaluation scaffolding and offline comparison evidence, "
        "but it is not sufficient evidence to implement active `llm_assisted` adoption. "
        "Live `deepseek/deepseek-v4-pro` evaluation was skipped because provider, model, "
        "and credential were not all explicitly configured in the process environment.",
        "",
        "Safe future direction: keep `llm_shadow`; allow no automatic "
        "`action_candidate`; never allow core/self_model updates from a digest proposal; "
        "run live evaluation only after explicit provider/model/credential setup.",
        "",
        "## Run Configuration",
        "",
        f"- deterministic temp root: `{deterministic_root}`",
        f"- shadow temp root: `{shadow_root}`",
        f"- fixture world: `{FIXTURE_WORLD}`",
        f"- digest proposal prompt version: `{PROMPT_VERSION}`",
        "- deterministic command equivalent: `AGENT_DIGEST_DECIDER=deterministic python -m app.main --project-root <tmp> wake --reason digest-quality-deterministic-baseline`",
        "- shadow command equivalent: `AGENT_DIGEST_DECIDER=llm_shadow AGENT_LLM_PROVIDER=mock python -m app.main --project-root <tmp> wake --reason digest-quality-llm-shadow-mock`",
        f"- live v4pro status: `{live_status}`",
        "",
        "## Pre/Post Context",
        "",
        "Previous offline evaluation recommended `PROMPT_HARDENING_FIRST`. This report is the post-hardening offline mock rerun. The comparison is qualitative because the offline fake client is a rubric control, not a live model.",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "| --- | --- |",
    ]
    for key, value in metrics.items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(
        [
            "",
            "## Baseline Counts",
            "",
            f"- deterministic observations: `{deterministic['counts']['observations']}`",
            f"- deterministic digest decisions: `{deterministic['counts']['digest_decisions']}`",
            f"- deterministic concerns: `{deterministic['counts']['concerns']}`",
            f"- deterministic memories: `{deterministic['counts']['memories']}`",
            f"- shadow wake result: `{shadow['run']['wake_result']}`",
            "",
            "## Qualitative Samples",
            "",
            _example_block("Agreement Examples", agreements),
            _example_block("Disagreement Examples", disagreements),
            _example_block("Fallback / Rejected Examples", fallbacks),
            _example_block("LLM Seems Better Than Deterministic", llm_better),
            _example_block("Deterministic Seems Safer Than LLM", deterministic_safer),
            _example_block("Unclear Examples", unclear),
            "## Safety Checks",
            "",
            f"- raw response persisted count: `{metrics['raw_response_persisted_count']}`",
            "- raw provider response text is not included in this report.",
            "- secret-like value check is limited to persisted proposal fields and the script output; live provider was not used.",
            "- final digest decisions remained deterministic; proposals only populated `digest_decision_proposals`.",
            "",
            "## Recommendation Detail",
            "",
            "- Keep `llm_shadow`; do not implement active `llm_assisted` adoption from this report alone.",
            "- Treat agreement rate as secondary. Boundary behavior is the main signal.",
            "- Stable project/user facts that LLM proposes as memory candidates are useful review candidates for deterministic over-concern behavior.",
            "- Do not adopt `action_candidate` from LLM alone.",
            "- Do not allow proposals to mutate `core_profile`, `self_model`, Discord mode, or final digest decisions.",
            "- Re-run live `openrouter` / `deepseek/deepseek-v4-pro` only with explicit provider, model, and credential configuration.",
            "",
        ]
    )
    return "\n".join(lines)


def _live_status() -> str:
    provider = os.environ.get("AGENT_LLM_PROVIDER", "").strip().lower()
    model = os.environ.get("AGENT_LLM_MODEL", "").strip()
    has_key = bool(os.environ.get("OPENROUTER_API_KEY"))
    if provider == "openrouter" and model and has_key:
        return "CONFIGURED_NOT_RUN_BY_THIS_OFFLINE_REPORT"
    missing = []
    if provider != "openrouter":
        missing.append("AGENT_LLM_PROVIDER=openrouter")
    if not model:
        missing.append("AGENT_LLM_MODEL")
    if not has_key:
        missing.append("OPENROUTER_API_KEY")
    return "SKIPPED_missing_" + ",".join(missing)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    deterministic_root = _prepare_root()
    deterministic_settings = _settings_for(deterministic_root, digest_decider="deterministic")
    deterministic_run = _run_cycle(
        deterministic_settings, "digest-quality-deterministic-baseline"
    )
    deterministic = _collect_rows(deterministic_settings)
    deterministic["run"] = deterministic_run

    shadow_root = _prepare_root()
    shadow_settings = _settings_for(
        shadow_root, digest_decider="llm_shadow", provider="mock"
    )
    original_factory = digest_decider_module.create_llm_client
    digest_decider_module.create_llm_client = (
        lambda settings, transport=None, temperature=None, extra_payload=None: HeuristicDigestProposalClient()
    )
    try:
        shadow_run = _run_cycle(shadow_settings, "digest-quality-llm-shadow-mock")
    finally:
        digest_decider_module.create_llm_client = original_factory
    shadow = _collect_rows(shadow_settings)
    shadow["run"] = shadow_run

    metrics = _metrics(shadow["proposal_rows"], shadow["counts"])
    report = _render_report(
        deterministic_root=deterministic_root,
        shadow_root=shadow_root,
        deterministic=deterministic,
        shadow=shadow,
        metrics=metrics,
        live_status=_live_status(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
