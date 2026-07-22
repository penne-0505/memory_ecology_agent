"""Create bounded input probes from the current state and attention policy."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.json_utils import json_dict, json_dumps
from app.db.models import AttentionPolicy, Concern, InputProbe, Memory
from app.schemas import ProbePlan


DEFAULT_SOURCE_PREFERENCES = {
    "local_file": 0.45,
    "web": 0.15,
    "memory": 0.20,
    "concern": 0.20,
    "random_sample": 0.05,
}


@dataclass(frozen=True)
class ProbeCandidate:
    source_key: str
    source_type: str
    query_or_path: str
    exploration_mode: str
    expected_gain: str
    base_score: float
    policy_score: float
    total_score: float
    available: bool
    skip_reason: str
    related_concern_ids: list[int]


def _source_preferences(policy: AttentionPolicy | None) -> dict[str, float]:
    preferences = DEFAULT_SOURCE_PREFERENCES.copy()
    if policy is not None:
        preferences.update(
            {
                str(key): float(value)
                for key, value in json_dict(policy.source_preferences_json).items()
                if isinstance(value, int | float)
            }
        )
    return preferences


def _rank_candidates(
    *,
    policy: AttentionPolicy | None,
    active_concerns: list[Concern],
    memories: list[Memory],
) -> list[ProbeCandidate]:
    preferences = _source_preferences(policy)
    randomness = policy.exploration_randomness if policy else 0.25
    top_concern_ids = [concern.id for concern in active_concerns[:1]]
    has_concern = bool(active_concerns)
    has_memory = bool(memories)
    candidates = [
        (
            "local_file",
            "local_file",
            "world/",
            "concern_driven" if has_concern else "random_environment_sample",
            "Read local ecology files for evidence that can change concern state.",
            0.30 + (0.20 if has_concern else 0.05),
            True,
            "",
            top_concern_ids,
        ),
        (
            "web",
            "web_search",
            "memory ecology deterministic stub",
            "contradiction_or_self_consistency_check",
            "Use deterministic web stub when policy wants outside contrast.",
            0.10 + (0.10 if has_concern else 0.0),
            True,
            "",
            top_concern_ids,
        ),
        (
            "memory",
            "memory",
            "recent_memories",
            "scheduled_revisit",
            "Re-read recent memories to check whether selected state should influence response.",
            0.15,
            has_memory,
            "" if has_memory else "no_memories_available",
            top_concern_ids,
        ),
        (
            "concern",
            "concern",
            "active_concerns",
            "concern_driven",
            "Sample current concerns as input when policy favors internal lifecycle review.",
            0.18,
            has_concern,
            "" if has_concern else "no_active_concerns_available",
            top_concern_ids,
        ),
        (
            "random_sample",
            "random_environment_sample",
            "world/",
            "random_environment_sample",
            "Keep a bounded non-greedy local sample available for exploration.",
            randomness * 0.20,
            True,
            "",
            [],
        ),
    ]
    ranked: list[ProbeCandidate] = []
    for (
        source_key,
        source_type,
        query_or_path,
        exploration_mode,
        expected_gain,
        base_score,
        available,
        skip_reason,
        related_concern_ids,
    ) in candidates:
        policy_score = float(preferences.get(source_key, 0.0))
        ranked.append(
            ProbeCandidate(
                source_key=source_key,
                source_type=source_type,
                query_or_path=query_or_path,
                exploration_mode=exploration_mode,
                expected_gain=expected_gain,
                base_score=round(base_score, 4),
                policy_score=round(policy_score, 4),
                total_score=round(base_score + policy_score, 4),
                available=available,
                skip_reason=skip_reason,
                related_concern_ids=related_concern_ids,
            )
        )
    return sorted(
        ranked,
        key=lambda candidate: (
            candidate.available,
            candidate.total_score,
            -len(candidate.skip_reason),
        ),
        reverse=True,
    )


def plan_probes(session: Session, settings: Settings, trigger_type: str) -> list[ProbePlan]:
    active_concerns = session.scalars(
        select(Concern)
        .where(Concern.state.in_(["seed", "active", "dormant"]))
        .order_by(Concern.activation_score.desc(), Concern.updated_at.desc())
        .limit(3)
    ).all()
    memories = session.scalars(select(Memory).order_by(Memory.updated_at.desc()).limit(3)).all()
    latest_policy = session.scalar(
        select(AttentionPolicy).order_by(AttentionPolicy.version.desc()).limit(1)
    )
    max_files = settings.max_probe_files
    max_chars = settings.max_probe_chars
    ranked = _rank_candidates(
        policy=latest_policy,
        active_concerns=active_concerns,
        memories=memories,
    )
    selected = next(candidate for candidate in ranked if candidate.available)
    skipped = [
        {
            "source_key": candidate.source_key,
            "source_type": candidate.source_type,
            "reason": candidate.skip_reason or "lower_policy_rank",
            "score": candidate.total_score,
        }
        for candidate in ranked
        if candidate.source_key != selected.source_key
    ]
    policy_payload = {
        "policy_id": latest_policy.id if latest_policy else None,
        "policy_version": latest_policy.version if latest_policy else None,
        "selected_source_key": selected.source_key,
        "selected_score": selected.total_score,
        "candidate_ranking": [
            {
                "source_key": candidate.source_key,
                "source_type": candidate.source_type,
                "available": candidate.available,
                "score": candidate.total_score,
                "policy_score": candidate.policy_score,
                "base_score": candidate.base_score,
                "skip_reason": candidate.skip_reason,
            }
            for candidate in ranked
        ],
        "skipped_sources": skipped,
        "exploration_randomness": latest_policy.exploration_randomness
        if latest_policy
        else None,
    }
    rationale = (
        f"Selected {selected.source_key} because attention_policy ranking gave "
        f"score={selected.total_score:.2f}; trigger={trigger_type}."
    )
    if active_concerns:
        rationale += f" Top concern={active_concerns[0].id} influences target."
    return [
        ProbePlan(
            trigger_type=trigger_type,
            source_type=selected.source_type,  # type: ignore[arg-type]
            query_or_path=selected.query_or_path,
            rationale=rationale,
            expected_gain=selected.expected_gain,
            related_concern_ids=selected.related_concern_ids,
            exploration_mode=selected.exploration_mode,
            budget={
                "max_files": max_files,
                "max_chars": max_chars,
                "policy_selection": policy_payload,
            },
        )
    ]


def persist_probe(session: Session, plan: ProbePlan) -> InputProbe:
    probe = InputProbe(
        trigger_type=plan.trigger_type,
        source_type=plan.source_type,
        query_or_path=plan.query_or_path,
        rationale=plan.rationale,
        expected_gain=plan.expected_gain,
        related_concern_ids_json=json_dumps(plan.related_concern_ids),
        exploration_mode=plan.exploration_mode,
        budget_json=json_dumps(plan.budget),
        budget_used_json=json_dumps({}),
        status="planned",
        result_summary="",
    )
    session.add(probe)
    session.flush()
    return probe
