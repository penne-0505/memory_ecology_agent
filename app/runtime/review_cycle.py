"""Review cycle v0."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.cognition.attention_policy import update_policy_from_outcomes
from app.cognition.concern_manager import review_concern_lifecycle
from app.db.json_utils import json_dumps
from app.db.models import Action, Observation, Outcome, RawEvent


def run_review_cycle(session: Session) -> dict[str, int]:
    raw_events = session.scalar(select(func.count(RawEvent.id))) or 0
    observations = session.scalar(select(func.count(Observation.id))) or 0
    action = Action(
        action_type="no_op",
        rationale="Review cycle v0 only reports counts; no state mutation needed.",
        related_concern_ids_json=json_dumps([]),
        input_probe_ids_json=json_dumps([]),
        payload_json=json_dumps({"raw_events": raw_events, "observations": observations}),
        external_effect="none",
        status="completed",
    )
    session.add(action)
    session.flush()
    outcomes = session.scalars(select(Outcome).order_by(Outcome.id)).all()
    policy = update_policy_from_outcomes(session, outcomes)
    lifecycle = review_concern_lifecycle(session)
    return {
        "raw_events": raw_events,
        "observations": observations,
        "actions": 1,
        "attention_policy_version": policy.version,
        **{f"concerns_{key}": value for key, value in lifecycle.items()},
    }
