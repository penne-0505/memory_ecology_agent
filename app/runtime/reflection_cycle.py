"""Reflection cycle v0."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.json_utils import json_dumps
from app.db.models import (
    AttentionPolicy,
    Concern,
    CoreChangeProposal,
    SelfModelSnapshot,
)


def run_reflection_cycle(session: Session) -> dict[str, int]:
    active_count = session.scalar(
        select(func.count(Concern.id)).where(Concern.state.in_(["seed", "active"]))
    ) or 0
    latest_policy = session.scalar(
        select(AttentionPolicy).order_by(AttentionPolicy.version.desc()).limit(1)
    )
    snapshots = 0
    proposals = 0
    if active_count >= 3:
        session.add(
            SelfModelSnapshot(
                summary=(
                    "Reflection v0 observed multiple active concerns and keeps "
                    "the self model descriptive without changing the locked core."
                ),
                stable_traits_json=json_dumps(["traceability_first"]),
                current_dispositions_json=json_dumps(["concern_density_detected"]),
                known_limitations_json=json_dumps(["reflection_v0_is_heuristic"]),
                source_concern_ids_json=json_dumps([]),
                source_attention_policy_id=latest_policy.id if latest_policy else None,
            )
        )
        snapshots += 1
    if active_count >= 6:
        session.add(
            CoreChangeProposal(
                proposed_change="Consider whether concern saturation should affect core narrative.",
                reason="High active concern count; stored as proposal only.",
                supporting_events_json=json_dumps([]),
                risk="High",
                status="proposed",
            )
        )
        proposals += 1
    session.flush()
    return {"self_model_snapshots": snapshots, "core_change_proposals": proposals}
