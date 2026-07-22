"""Lightweight memory creation."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.json_utils import json_dumps
from app.db.models import Memory, Observation


def create_memory_from_observation(
    session: Session, observation: Observation, related_concern_ids: list[int] | None = None
) -> Memory:
    memory = Memory(
        kind="observation_digest",
        content=observation.summary,
        confidence=observation.confidence,
        stability=0.45 + min(observation.confidence, 0.5) / 2,
        source_ids_json=json_dumps([observation.id]),
        related_concern_ids_json=json_dumps(related_concern_ids or []),
    )
    session.add(memory)
    session.flush()
    return memory
