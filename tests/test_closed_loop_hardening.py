from __future__ import annotations

from sqlalchemy import select

from app.adapters.llm import StateSensitiveFakeLLMClient
from app.cognition.attention_policy import update_policy_from_outcomes
from app.cognition.concern_manager import (
    review_concern_lifecycle,
    upsert_concern_from_observation,
)
from app.cognition.observation_extractor import draft_observation, persist_observation
from app.cognition.probe_planner import plan_probes
from app.db.json_utils import json_dict, json_dumps, json_loads
from app.db.models import (
    Action,
    AttentionPolicy,
    AttentionPolicyEvent,
    Concern,
    ConcernEvent,
    CoreProfile,
    DigestDecisionTrace,
    Outcome,
    RawEvent,
    ReplayRun,
)
from app.eval.replay import run_replay_eval
from app.runtime.events import persist_raw_event
from app.runtime.wake_cycle import run_wake_cycle
from app.schemas import RawEventInput


def _observation(session, text: str):
    raw_event = persist_raw_event(
        session,
        RawEventInput(
            source_type="conversation",
            event_type="test_observation",
            payload={"test": True},
            content_text=text,
        ),
    )
    return persist_observation(session, draft_observation(raw_event, source_probe_id=None))


def test_digest_decisions_persist_concern_memory_and_discard(seeded_session, settings):
    run_wake_cycle(seeded_session, settings, reason="digest-decision-test")

    decisions = seeded_session.scalars(
        select(DigestDecisionTrace).order_by(DigestDecisionTrace.id)
    ).all()
    decision_types = {decision.decision for decision in decisions}

    assert {"concern_candidate", "memory_candidate", "discard"} <= decision_types
    discard = next(decision for decision in decisions if decision.decision == "discard")
    assert "low signal" in discard.reason.lower()
    assert discard.source_observation_id
    assert discard.source_raw_event_id
    assert discard.salience_snapshot < 0.30


def test_concern_identity_and_lifecycle_paths_are_auditable(seeded_session):
    obs1 = _observation(
        seeded_session,
        "Lifecycle digest risk remains unresolved for implementation trace review.",
    )
    concern = upsert_concern_from_observation(seeded_session, obs1)
    assert concern.state == "seed"

    obs2 = _observation(
        seeded_session,
        "Lifecycle digest risk remains unresolved for implementation evidence review.",
    )
    same = upsert_concern_from_observation(seeded_session, obs2)
    assert same.id == concern.id
    assert same.state == "active"

    different_obs = _observation(
        seeded_session,
        "Shoegaze playlist texture preference belongs to a music listening note.",
    )
    different = upsert_concern_from_observation(seeded_session, different_obs)
    assert different.id != concern.id

    concern.activation_score = 0.2
    concern.unresolvedness = 0.1
    concern.attempt_pressure = 0.1
    lifecycle = review_concern_lifecycle(seeded_session)
    assert lifecycle["dormant"] >= 1
    assert concern.state == "dormant"

    obs3 = _observation(
        seeded_session,
        "Lifecycle digest risk remains unresolved for implementation transition review.",
    )
    reactivated = upsert_concern_from_observation(seeded_session, obs3)
    assert reactivated.id == concern.id
    assert reactivated.state == "active"

    action = Action(
        action_type="test_resolution",
        rationale="Test action resolved lifecycle concern.",
        related_concern_ids_json=json_dumps([concern.id]),
        input_probe_ids_json=json_dumps([]),
        payload_json=json_dumps({}),
        external_effect="none",
        status="completed",
    )
    seeded_session.add(action)
    seeded_session.flush()
    outcome = Outcome(
        action_id=action.id,
        observed_result="Concern resolved by deterministic test outcome.",
        effect_on_concerns_json=json_dumps(
            {"resolved": [concern.id], "closure_mode": "completed"}
        ),
        effect_on_attention_policy_json=json_dumps({}),
    )
    seeded_session.add(outcome)
    seeded_session.flush()

    lifecycle = review_concern_lifecycle(seeded_session)
    assert lifecycle["resolved"] >= 1
    assert concern.state == "resolved"
    resolved_event = seeded_session.scalar(
        select(ConcernEvent)
        .where(ConcernEvent.concern_id == concern.id)
        .where(ConcernEvent.event_type == "resolved")
        .order_by(ConcernEvent.id.desc())
        .limit(1)
    )
    delta = json_loads(resolved_event.delta_json, {})
    assert delta["previous_state"] == "active"
    assert delta["new_state"] == "resolved"
    assert delta["evidence_outcome_ids"] == [outcome.id]

    lifecycle = review_concern_lifecycle(seeded_session)
    assert lifecycle["archived"] >= 1
    assert concern.state == "archived"


def test_successor_concern_is_created_from_transformed_outcome(seeded_session):
    observation = _observation(
        seeded_session,
        "Successor lifecycle risk remains unresolved for digest transition.",
    )
    concern = upsert_concern_from_observation(seeded_session, observation)
    upsert_concern_from_observation(
        seeded_session,
        _observation(
            seeded_session,
            "Successor lifecycle risk remains unresolved for digest transition evidence.",
        ),
    )
    action = Action(
        action_type="test_successor",
        rationale="Test action transforms concern.",
        related_concern_ids_json=json_dumps([concern.id]),
        input_probe_ids_json=json_dumps([]),
        payload_json=json_dumps({}),
        external_effect="none",
        status="completed",
    )
    seeded_session.add(action)
    seeded_session.flush()
    outcome = Outcome(
        action_id=action.id,
        observed_result="Concern transformed into a larger successor concern.",
        effect_on_concerns_json=json_dumps(
            {
                "successor": {
                    "concern_id": concern.id,
                    "title": "Successor concern for lifecycle evidence",
                    "closure_mode": "transformed",
                }
            }
        ),
        effect_on_attention_policy_json=json_dumps({}),
    )
    seeded_session.add(outcome)
    seeded_session.flush()

    lifecycle = review_concern_lifecycle(seeded_session)

    assert lifecycle["successors"] == 1
    assert concern.successor_concern_id is not None
    successor = seeded_session.get(Concern, concern.successor_concern_id)
    assert successor is not None
    assert successor.state == "seed"
    assert concern.closure_mode == "transformed"


def test_attention_policy_drives_probe_source_selection(seeded_session, settings):
    previous = seeded_session.scalar(
        select(AttentionPolicy).order_by(AttentionPolicy.version.desc()).limit(1)
    )
    source_preferences = json_dict(previous.source_preferences_json)
    source_preferences["web"] = 0.95
    source_preferences["local_file"] = 0.01
    policy = AttentionPolicy(
        version=previous.version + 1,
        source_preferences_json=json_dumps(source_preferences),
        salience_preferences_json=previous.salience_preferences_json,
        concern_type_preferences_json=previous.concern_type_preferences_json,
        action_preferences_json=previous.action_preferences_json,
        response_preferences_json=previous.response_preferences_json,
        exploration_randomness=previous.exploration_randomness,
        stability=previous.stability,
    )
    seeded_session.add(policy)
    seeded_session.flush()

    plans = plan_probes(seeded_session, settings=settings, trigger_type="policy-test")

    assert plans[0].source_type == "web_search"
    selection = plans[0].budget["policy_selection"]
    assert selection["selected_source_key"] == "web"
    assert any(item["source_key"] == "local_file" for item in selection["skipped_sources"])


def test_outcome_driven_policy_update_keeps_outcome_evidence(seeded_session):
    action = Action(
        action_type="test_probe_result",
        rationale="Noisy source test.",
        related_concern_ids_json=json_dumps([]),
        input_probe_ids_json=json_dumps([]),
        payload_json=json_dumps({}),
        external_effect="none",
        status="completed",
    )
    seeded_session.add(action)
    seeded_session.flush()
    outcome = Outcome(
        action_id=action.id,
        observed_result="Noisy web_stub result should reduce web preference slightly.",
        effect_on_concerns_json=json_dumps({}),
        effect_on_attention_policy_json=json_dumps(
            {"source_type": "web_search", "result": "noisy"}
        ),
    )
    seeded_session.add(outcome)
    seeded_session.flush()

    policy = update_policy_from_outcomes(seeded_session, [outcome])
    event = seeded_session.scalar(
        select(AttentionPolicyEvent)
        .where(AttentionPolicyEvent.attention_policy_id == policy.id)
        .order_by(AttentionPolicyEvent.id.desc())
        .limit(1)
    )

    assert event is not None
    assert event.target_field == "source_preferences.web"
    assert json_loads(event.evidence_outcome_ids_json, []) == [outcome.id]
    assert abs(json_loads(event.delta_json, {})["delta"]) <= 0.04


def test_state_sensitive_replay_shows_text_drift_without_core_change(
    seeded_session, settings
):
    core_before = seeded_session.scalar(select(CoreProfile).limit(1)).content
    before = run_replay_eval(
        seeded_session, eval_prompt_id=1, llm=StateSensitiveFakeLLMClient()
    )[0]
    run_wake_cycle(seeded_session, settings, reason="state-sensitive-replay-test")
    after = run_replay_eval(
        seeded_session, eval_prompt_id=1, llm=StateSensitiveFakeLLMClient()
    )[0]
    core_after = seeded_session.scalar(select(CoreProfile).limit(1)).content

    assert before.response_text != after.response_text
    assert json_loads(before.selected_concerns_json, []) != json_loads(
        after.selected_concerns_json, []
    )
    assert core_after == core_before
    assert seeded_session.scalar(select(ReplayRun).where(ReplayRun.id == after.id))
    assert seeded_session.scalar(select(RawEvent).limit(1)) is not None
