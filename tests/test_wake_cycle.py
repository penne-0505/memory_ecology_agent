from __future__ import annotations

from sqlalchemy import func, select

from app.db.models import (
    Action,
    AttentionPolicyEvent,
    Concern,
    ConcernEvent,
    InputProbe,
    Observation,
    Outcome,
    RawEvent,
    WakeRequest,
)
from app.runtime.wake_cycle import run_wake_cycle


def test_ac002_wake_cycle_creates_trace_vertical(seeded_session, settings):
    result = run_wake_cycle(seeded_session, settings, reason="cron")
    assert result["probes"] >= 1
    assert result["raw_events"] >= 1
    assert result["observations"] >= 1
    assert result["concerns"] >= 1
    assert result["actions"] >= 1
    assert result["outcomes"] >= 1
    assert result["wake_requests"] >= 1

    assert seeded_session.scalar(select(func.count(InputProbe.id))) >= 1
    assert seeded_session.scalar(select(func.count(RawEvent.id))) >= 1
    assert seeded_session.scalar(select(func.count(Observation.id))) >= 1
    assert seeded_session.scalar(select(func.count(Concern.id))) >= 1
    assert seeded_session.scalar(select(func.count(ConcernEvent.id))) >= 1
    assert seeded_session.scalar(select(func.count(Action.id))) >= 1
    assert seeded_session.scalar(select(func.count(Outcome.id))) >= 1
    assert seeded_session.scalar(select(func.count(AttentionPolicyEvent.id))) >= 1
    assert seeded_session.scalar(select(func.count(WakeRequest.id))) >= 1


def test_inv004_inv005_events_keep_reason_and_delta(seeded_session, settings):
    run_wake_cycle(seeded_session, settings, reason="cron")
    concern_event = seeded_session.scalar(select(ConcernEvent).limit(1))
    policy_event = seeded_session.scalar(select(AttentionPolicyEvent).limit(1))
    assert concern_event is not None
    assert "concern" in concern_event.reason.lower()
    assert "activation_score" in concern_event.delta_json
    assert policy_event is not None
    assert policy_event.target_field.startswith("source_preferences.")
    assert policy_event.reason
    assert policy_event.evidence_observation_ids_json != "[]"
