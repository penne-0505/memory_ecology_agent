"""Route observations into concern, memory, action, or discard candidates."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.json_utils import json_dumps
from app.db.models import DigestDecisionTrace, Observation
from app.schemas import DigestDecision


def digest_observation(observation: Observation) -> DigestDecision:
    if (
        observation.salience < 0.30
        and observation.uncertainty < 0.40
        and observation.self_relevance < 0.45
    ):
        return DigestDecision(
            observation_id=observation.id,
            disposition="discard",
            reason=(
                "Observation is low signal across salience, uncertainty, and "
                "self relevance, so it is explicitly discarded."
            ),
        )
    if observation.salience >= 0.45 or observation.uncertainty >= 0.60:
        return DigestDecision(
            observation_id=observation.id,
            disposition="concern_candidate",
            reason=(
                "Observation remains unresolved enough to become or reinforce "
                f"a concern; salience={observation.salience:.2f}, "
                f"uncertainty={observation.uncertainty:.2f}."
            ),
        )
    if observation.novelty >= 0.50 and observation.confidence >= 0.60:
        return DigestDecision(
            observation_id=observation.id,
            disposition="memory_candidate",
            reason="Observation is stable enough to keep as a lightweight memory.",
        )
    if observation.self_relevance >= 0.70:
        return DigestDecision(
            observation_id=observation.id,
            disposition="action_candidate",
            reason="Observation is self-relevant enough to consider an action.",
        )
    return DigestDecision(
        observation_id=observation.id,
        disposition="discard",
        reason="Observation has low salience, low novelty, and low self relevance.",
    )


def persist_digest_decision(
    session: Session,
    observation: Observation,
    decision: DigestDecision,
    *,
    run_id: str = "",
    related_concern_ids: list[int] | None = None,
    metadata: dict[str, object] | None = None,
) -> DigestDecisionTrace:
    trace = DigestDecisionTrace(
        run_id=run_id,
        source_observation_id=observation.id,
        source_raw_event_id=observation.source_event_id,
        decision=decision.disposition,
        reason=decision.reason,
        confidence=observation.confidence,
        salience_snapshot=observation.salience,
        novelty_snapshot=observation.novelty,
        uncertainty_snapshot=observation.uncertainty,
        self_relevance_snapshot=observation.self_relevance,
        related_concern_ids_json=json_dumps(related_concern_ids or []),
        metadata_json=json_dumps(
            {
                "possible_disposition": observation.possible_disposition,
                **(metadata or {}),
            }
        ),
    )
    session.add(trace)
    session.flush()
    return trace
