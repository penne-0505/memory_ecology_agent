"""Small bounded attention policy updates."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.json_utils import json_dict, json_dumps, json_list
from app.db.models import (
    AttentionPolicy,
    AttentionPolicyEvent,
    INITIAL_ATTENTION_POLICY,
    Observation,
    Outcome,
)


def latest_or_create_policy(session: Session) -> AttentionPolicy:
    latest = session.scalar(
        select(AttentionPolicy).order_by(AttentionPolicy.version.desc()).limit(1)
    )
    if latest is not None:
        return latest
    policy = AttentionPolicy(version=1, **INITIAL_ATTENTION_POLICY)
    session.add(policy)
    session.flush()
    return policy


def _clamp(value: float, floor: float = 0.0, ceiling: float = 1.0) -> float:
    return max(floor, min(ceiling, value))


def _source_preference_key(source_type: str) -> str:
    if source_type in {"web_search", "web_stub"}:
        return "web"
    if source_type == "random_environment_sample":
        return "random_sample"
    return source_type


def update_policy_from_observations(
    session: Session, observations: list[Observation], source_type: str
) -> AttentionPolicy:
    previous = latest_or_create_policy(session)
    source_preferences = json_dict(previous.source_preferences_json)
    useful = [obs for obs in observations if obs.salience >= 0.45]
    source_key = _source_preference_key(source_type)
    if source_key == "local_file" and useful:
        delta = min(0.05, 0.015 * len(useful))
        key = "local_file"
        reason = (
            "Local file probe produced useful observations, so the policy makes "
            "a small bounded increase to local_file preference."
        )
    elif source_key == "web" and not useful:
        delta = -0.02
        key = "web"
        reason = "Web stub produced no useful observation, so preference is weakened slightly."
    else:
        delta = 0.0
        key = source_key
        reason = "No policy preference changed because evidence was weak."

    if delta == 0.0:
        return previous

    before = float(source_preferences.get(key, 0.0))
    after = _clamp(before + delta, floor=0.02 if key == "random_sample" else 0.0)
    source_preferences[key] = round(after, 4)
    new_policy = AttentionPolicy(
        version=previous.version + 1,
        source_preferences_json=json_dumps(source_preferences),
        salience_preferences_json=previous.salience_preferences_json,
        concern_type_preferences_json=previous.concern_type_preferences_json,
        action_preferences_json=previous.action_preferences_json,
        response_preferences_json=previous.response_preferences_json,
        exploration_randomness=max(previous.exploration_randomness, 0.05),
        stability=previous.stability,
    )
    session.add(new_policy)
    session.flush()

    event_type = "drift_warning" if abs(delta) > 0.10 else "preference_adjusted"
    session.add(
        AttentionPolicyEvent(
            attention_policy_id=new_policy.id,
            event_type=event_type,
            target_field=f"source_preferences.{key}",
            delta_json=json_dumps({"before": before, "after": after, "delta": delta}),
            reason=reason,
            evidence_observation_ids_json=json_dumps([obs.id for obs in useful]),
            evidence_action_ids_json=json_dumps([]),
            evidence_outcome_ids_json=json_dumps([]),
            confidence=0.70 if useful else 0.45,
        )
    )
    session.flush()
    return new_policy


def update_policy_from_outcomes(
    session: Session, outcomes: list[Outcome]
) -> AttentionPolicy:
    policy = latest_or_create_policy(session)
    changed_policy = policy
    for outcome in outcomes:
        existing_events = session.scalars(
            select(AttentionPolicyEvent)
            .where(AttentionPolicyEvent.evidence_outcome_ids_json != "[]")
            .order_by(AttentionPolicyEvent.id.desc())
            .limit(100)
        ).all()
        if any(outcome.id in json_list(event.evidence_outcome_ids_json) for event in existing_events):
            continue
        effect = json_dict(outcome.effect_on_attention_policy_json)
        feedback = (outcome.user_feedback or "").lower()
        result = (outcome.observed_result or "").lower()
        if effect.get("direct_effect") == "none" and not feedback:
            continue

        target_group = "source_preferences"
        target_key = _source_preference_key(str(effect.get("source_type") or ""))
        delta = 0.0
        reason = ""
        confidence = 0.55

        feedback_type = str(effect.get("feedback_type") or "")
        if effect.get("result") in {"useful", "accepted"} or "useful" in feedback_type or "useful" in feedback:
            target_key = target_key or "local_file"
            delta = 0.025
            reason = f"Outcome {outcome.id} marked source evidence useful; preference nudged up."
            confidence = 0.68
        elif effect.get("result") in {"noisy", "noise"} or "noise" in feedback_type or "noise" in feedback:
            target_key = target_key or "web"
            delta = -0.025
            reason = f"Outcome {outcome.id} marked source evidence noisy; preference nudged down."
            confidence = 0.62
        elif "too_much" in feedback_type or "too much" in feedback:
            target_group = "response_preferences"
            target_key = "mention_internal_state"
            delta = -0.03
            reason = "User feedback said internal state was too much; mention_internal_state decreased."
            confidence = 0.72
        elif "correction" in feedback_type or "correction" in feedback or "corrected" in result:
            target_group = "salience_preferences"
            target_key = "contradiction"
            delta = 0.03
            reason = f"Correction outcome {outcome.id} increases attention to contradiction/correction."
            confidence = 0.74
        elif "accepted" in feedback or "positive" in feedback_type:
            target_group = "response_preferences"
            target_key = "ask_when_uncertain"
            delta = 0.015
            reason = f"Positive feedback outcome {outcome.id} slightly reinforces response preference."
            confidence = 0.60

        if delta == 0.0 or not target_key:
            continue

        current = changed_policy
        source_preferences = json_dict(current.source_preferences_json)
        salience_preferences = json_dict(current.salience_preferences_json)
        response_preferences = json_dict(current.response_preferences_json)
        if target_group == "source_preferences":
            target_map = source_preferences
        elif target_group == "salience_preferences":
            target_map = salience_preferences
        else:
            target_map = response_preferences
        before = float(target_map.get(target_key, 0.0))
        bounded_delta = max(-0.04, min(0.04, delta))
        after = _clamp(before + bounded_delta, floor=0.0, ceiling=1.0)
        target_map[target_key] = round(after, 4)

        changed_policy = AttentionPolicy(
            version=current.version + 1,
            source_preferences_json=json_dumps(source_preferences),
            salience_preferences_json=json_dumps(salience_preferences),
            concern_type_preferences_json=current.concern_type_preferences_json,
            action_preferences_json=current.action_preferences_json,
            response_preferences_json=json_dumps(response_preferences),
            exploration_randomness=max(0.05, min(0.8, current.exploration_randomness)),
            stability=current.stability,
        )
        session.add(changed_policy)
        session.flush()
        session.add(
            AttentionPolicyEvent(
                attention_policy_id=changed_policy.id,
                event_type="outcome_preference_adjusted",
                target_field=f"{target_group}.{target_key}",
                delta_json=json_dumps(
                    {"before": before, "after": after, "delta": bounded_delta}
                ),
                reason=reason,
                evidence_observation_ids_json=json_dumps([]),
                evidence_action_ids_json=json_dumps([outcome.action_id]),
                evidence_outcome_ids_json=json_dumps([outcome.id]),
                confidence=confidence,
            )
        )
        session.flush()
    return changed_policy
