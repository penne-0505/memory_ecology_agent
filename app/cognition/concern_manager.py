"""Concern identity and lifecycle helpers."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.json_utils import json_dict, json_dumps, json_list
from app.db.models import Action, Concern, ConcernEvent, Observation, Outcome


STOPWORDS = {
    "about",
    "after",
    "agent",
    "because",
    "current",
    "from",
    "into",
    "observation",
    "policy",
    "should",
    "that",
    "this",
    "trace",
    "with",
}

RESOLUTION_WORDS = {
    "resolved": "completed",
    "answered": "answered",
    "accepted": "accepted",
    "corrected": "answered",
    "abandoned": "abandoned",
    "irrelevant": "irrelevant",
}

SUCCESSOR_MODES = {"absorbed", "transformed", "superseded"}


def _tokens(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9_+-]{4,}", text.lower())
    seen: list[str] = []
    for word in words:
        if word in STOPWORDS or word in seen:
            continue
        seen.append(word)
        if len(seen) >= 12:
            break
    return seen


def _title_for(observation: Observation) -> str:
    words = observation.summary.split()
    return " ".join(words[:10]) or f"Observation {observation.id}"


def _identity_key_for_observation(observation: Observation) -> str:
    object_tokens = _tokens(observation.summary)
    score_band = (
        "high_uncertainty" if observation.uncertainty >= 0.6 else "low_uncertainty"
    )
    relevance_band = "self_relevant" if observation.self_relevance >= 0.65 else "ambient"
    if not object_tokens:
        return f"obs:{observation.id}:{score_band}:{relevance_band}"
    return ":".join([score_band, relevance_band, *object_tokens[:5]])


def _identity_key_for_concern(concern: Concern) -> str:
    payload = json_dict(concern.object_json)
    identity = payload.get("identity_key")
    if isinstance(identity, str) and identity:
        return identity
    return ":".join(_tokens(concern.title)[:6])


def _token_overlap(left: str, right: str) -> float:
    left_tokens = set(left.split(":"))
    right_tokens = set(right.split(":"))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / max(len(left_tokens), len(right_tokens))


def _activation_components(observation: Observation, recurrence: float) -> dict[str, float]:
    unresolvedness = max(observation.uncertainty, 0.35)
    self_relevance = observation.self_relevance
    external_relevance = observation.salience
    attempt_pressure = min(0.75, (observation.salience + observation.self_relevance) / 2)
    saturation_penalty = 0.05 if recurrence else 0.0
    recency = 0.25
    activation = (
        unresolvedness
        + recurrence
        + self_relevance
        + attempt_pressure
        + recency
        + external_relevance
        - saturation_penalty
    )
    return {
        "unresolvedness": unresolvedness,
        "recurrence_score": recurrence,
        "self_relevance": self_relevance,
        "external_relevance": external_relevance,
        "attempt_pressure": attempt_pressure,
        "recency": recency,
        "saturation_penalty": saturation_penalty,
        "activation_score": round(activation, 4),
    }


def _matching_concern(session: Session, observation: Observation) -> Concern | None:
    identity_key = _identity_key_for_observation(observation)
    candidates = session.scalars(
        select(Concern)
        .where(Concern.state.in_(["seed", "active", "dormant"]))
        .order_by(Concern.updated_at.desc(), Concern.id.desc())
        .limit(50)
    ).all()
    best: tuple[float, Concern] | None = None
    for concern in candidates:
        concern_key = _identity_key_for_concern(concern)
        exact = concern_key == identity_key
        overlap = _token_overlap(concern_key, identity_key)
        same_object = bool(
            set(_tokens(json_dict(concern.object_json).get("summary", "")))
            & set(_tokens(observation.summary))
        )
        score = 1.0 if exact else overlap + (0.2 if same_object else 0.0)
        if score >= 0.55 and (best is None or score > best[0]):
            best = (score, concern)
    return best[1] if best else None


def _add_concern_event(
    session: Session,
    concern: Concern,
    event_type: str,
    reason: str,
    *,
    previous_state: str | None,
    new_state: str | None,
    delta: dict[str, Any] | None = None,
    observation_ids: list[int] | None = None,
    action_id: int | None = None,
    outcome_ids: list[int] | None = None,
) -> ConcernEvent:
    payload = {
        "previous_state": previous_state,
        "new_state": new_state,
        "evidence_observation_ids": observation_ids or [],
        "evidence_action_id": action_id,
        "evidence_outcome_ids": outcome_ids or [],
        **(delta or {}),
    }
    event = ConcernEvent(
        concern_id=concern.id,
        event_type=event_type,
        delta_json=json_dumps(payload),
        reason=reason,
        source_observation_ids_json=json_dumps(observation_ids or []),
        source_action_id=action_id,
    )
    session.add(event)
    session.flush()
    return event


def transition_concern_state(
    session: Session,
    concern: Concern,
    new_state: str,
    *,
    event_type: str,
    reason: str,
    closure_mode: str | None = None,
    closed_by: int | None = None,
    successor_concern_id: int | None = None,
    observation_ids: list[int] | None = None,
    action_id: int | None = None,
    outcome_ids: list[int] | None = None,
    delta: dict[str, Any] | None = None,
) -> ConcernEvent:
    previous_state = concern.state
    concern.state = new_state
    if closure_mode is not None:
        concern.closure_mode = closure_mode
    if closed_by is not None:
        concern.closed_by = closed_by
    if successor_concern_id is not None:
        concern.successor_concern_id = successor_concern_id
    if new_state == "resolved":
        concern.activation_score = min(concern.activation_score, 0.2)
        concern.unresolvedness = min(concern.unresolvedness, 0.1)
    elif new_state == "archived":
        concern.activation_score = 0.0
    event_delta = {
        "closure_mode": concern.closure_mode,
        "closed_by": concern.closed_by,
        "successor_concern_id": concern.successor_concern_id,
        **(delta or {}),
    }
    return _add_concern_event(
        session,
        concern,
        event_type,
        reason,
        previous_state=previous_state,
        new_state=new_state,
        delta=event_delta,
        observation_ids=observation_ids,
        action_id=action_id,
        outcome_ids=outcome_ids,
    )


def upsert_concern_from_observation(session: Session, observation: Observation) -> Concern:
    title = _title_for(observation)
    identity_key = _identity_key_for_observation(observation)
    existing = _matching_concern(session, observation)
    if existing:
        sources = json_list(existing.source_observation_ids_json)
        if observation.id not in sources:
            sources.append(observation.id)
        components = _activation_components(
            observation, recurrence=min(existing.recurrence_score + 0.15, 1.0)
        )
        previous_state = existing.state
        previous_activation = existing.activation_score
        existing.state = "active"
        existing.activation_score = components["activation_score"]
        existing.unresolvedness = components["unresolvedness"]
        existing.recurrence_score = components["recurrence_score"]
        existing.self_relevance = components["self_relevance"]
        existing.external_relevance = components["external_relevance"]
        existing.attempt_pressure = components["attempt_pressure"]
        existing.saturation_penalty = components["saturation_penalty"]
        existing.last_observed_at = observation.created_at
        existing.source_observation_ids_json = json_dumps(sources)
        payload = json_dict(existing.object_json)
        payload["identity_key"] = _identity_key_for_concern(existing) or identity_key
        payload["last_summary"] = observation.summary
        existing.object_json = json_dumps(payload)
        if previous_state == "dormant":
            event_type = "reactivated"
            reason = "Dormant concern matched a new related observation and became active again."
        elif previous_state == "seed":
            event_type = "activated"
            reason = "Seed concern received related evidence and became active."
        else:
            event_type = "reinforced"
            reason = (
                "Matched an existing concern by deterministic identity and reinforced it "
                f"from a new observation. activation {previous_activation:.2f}->{existing.activation_score:.2f}."
            )
        concern = existing
        previous_for_event = previous_state
    else:
        components = _activation_components(observation, recurrence=0.10)
        concern = Concern(
            title=title,
            object_json=json_dumps(
                {
                    "summary": observation.summary,
                    "identity_key": identity_key,
                    "tokens": _tokens(observation.summary),
                }
            ),
            tension_json=json_dumps(
                {
                    "uncertainty": observation.uncertainty,
                    "salience": observation.salience,
                }
            ),
            closure_hypothesis=(
                "Concern can close when later observations or actions reduce the "
                "unresolved tension."
            ),
            state="seed",
            activation_score=components["activation_score"],
            unresolvedness=components["unresolvedness"],
            recurrence_score=components["recurrence_score"],
            self_relevance=components["self_relevance"],
            external_relevance=components["external_relevance"],
            attempt_pressure=components["attempt_pressure"],
            saturation_penalty=components["saturation_penalty"],
            last_observed_at=observation.created_at,
            opened_reason=(
                "Observation was classified as unresolved and salient enough to "
                "hold as a seed concern."
            ),
            source_observation_ids_json=json_dumps([observation.id]),
            closure_mode="",
        )
        session.add(concern)
        session.flush()
        event_type = "seeded"
        reason = "Created a seed concern from a salient unresolved observation."
        previous_for_event = None

    _add_concern_event(
        session,
        concern,
        event_type,
        reason,
        previous_state=previous_for_event,
        new_state=concern.state,
        delta={
            **components,
            "identity_key": identity_key,
            "identity_match": bool(existing),
        },
        observation_ids=[observation.id],
        action_id=None,
    )
    session.flush()
    return concern


def create_successor_concern(
    session: Session,
    concern: Concern,
    *,
    title: str,
    closure_mode: str,
    reason: str,
    action_id: int | None = None,
    outcome_ids: list[int] | None = None,
) -> Concern:
    if closure_mode not in SUCCESSOR_MODES:
        raise ValueError(f"successor closure_mode must be one of {sorted(SUCCESSOR_MODES)}")
    successor = Concern(
        title=title,
        object_json=json_dumps(
            {
                "successor_for": concern.id,
                "identity_key": f"successor:{concern.id}:{':'.join(_tokens(title)[:4])}",
            }
        ),
        tension_json=concern.tension_json,
        closure_hypothesis="Successor concern closes when the transformed tension is handled.",
        state="seed",
        activation_score=max(0.1, concern.activation_score + 0.1),
        unresolvedness=max(0.35, concern.unresolvedness),
        recurrence_score=0.0,
        self_relevance=concern.self_relevance,
        external_relevance=concern.external_relevance,
        attempt_pressure=concern.attempt_pressure,
        saturation_penalty=0.0,
        last_observed_at=concern.last_observed_at,
        opened_reason=reason,
        source_observation_ids_json=concern.source_observation_ids_json,
        closure_mode="",
    )
    session.add(successor)
    session.flush()
    transition_concern_state(
        session,
        concern,
        "resolved",
        event_type="successor_linked",
        reason=reason,
        closure_mode=closure_mode,
        closed_by=action_id,
        successor_concern_id=successor.id,
        action_id=action_id,
        outcome_ids=outcome_ids,
    )
    _add_concern_event(
        session,
        successor,
        "successor_created",
        reason,
        previous_state=None,
        new_state=successor.state,
        delta={"predecessor_concern_id": concern.id, "closure_mode": closure_mode},
        action_id=action_id,
        outcome_ids=outcome_ids,
    )
    return successor


def _outcome_effect(outcome: Outcome) -> dict[str, Any]:
    effect = json_dict(outcome.effect_on_concerns_json)
    if effect:
        return effect
    return json_dict(outcome.effect_on_attention_policy_json)


def _related_concern_ids_for_outcome(session: Session, outcome: Outcome) -> list[int]:
    effect = _outcome_effect(outcome)
    ids = effect.get("concern_ids") or effect.get("resolved") or effect.get("touched") or []
    if isinstance(ids, int):
        return [ids]
    if isinstance(ids, list):
        return [int(value) for value in ids if str(value).isdigit()]
    action = session.get(Action, outcome.action_id)
    if action is None:
        return []
    return [int(value) for value in json_list(action.related_concern_ids_json) if str(value).isdigit()]


def apply_outcome_to_concern_lifecycle(session: Session, outcome: Outcome) -> dict[str, int]:
    effect = _outcome_effect(outcome)
    counts = {"resolved": 0, "successors": 0}
    successor_payload = effect.get("successor")
    if isinstance(successor_payload, dict):
        concern_id = successor_payload.get("concern_id")
        if str(concern_id).isdigit():
            concern = session.get(Concern, int(concern_id))
            if concern and concern.state in {"active", "dormant", "seed"}:
                mode = str(successor_payload.get("closure_mode") or "transformed")
                title = str(successor_payload.get("title") or f"Successor: {concern.title}")
                create_successor_concern(
                    session,
                    concern,
                    title=title,
                    closure_mode=mode,
                    reason="Outcome transformed the concern into a successor concern.",
                    action_id=outcome.action_id,
                    outcome_ids=[outcome.id],
                )
                counts["successors"] += 1
        return counts

    text = " ".join(
        [
            outcome.observed_result.lower(),
            outcome.user_feedback.lower(),
            json_dumps(effect).lower(),
        ]
    )
    closure_mode = str(effect.get("closure_mode") or "")
    if not closure_mode:
        for word, mode in RESOLUTION_WORDS.items():
            if word in text:
                closure_mode = mode
                break
    if closure_mode not in {
        "completed",
        "answered",
        "accepted",
        "abandoned",
        "absorbed",
        "transformed",
        "superseded",
        "irrelevant",
    }:
        return counts

    for concern_id in _related_concern_ids_for_outcome(session, outcome):
        concern = session.get(Concern, concern_id)
        if concern is None or concern.state not in {"active", "dormant", "seed"}:
            continue
        transition_concern_state(
            session,
            concern,
            "resolved",
            event_type="resolved",
            reason=f"Outcome {outcome.id} satisfied the closure hypothesis ({closure_mode}).",
            closure_mode=closure_mode,
            closed_by=outcome.action_id,
            action_id=outcome.action_id,
            outcome_ids=[outcome.id],
        )
        counts["resolved"] += 1
    return counts


def review_concern_lifecycle(session: Session) -> dict[str, int]:
    counts = {
        "activated": 0,
        "dormant": 0,
        "resolved": 0,
        "archived": 0,
        "successors": 0,
    }
    resolved_this_cycle: set[int] = set()
    for outcome in session.scalars(select(Outcome).order_by(Outcome.id)).all():
        result = apply_outcome_to_concern_lifecycle(session, outcome)
        counts["resolved"] += result["resolved"]
        counts["successors"] += result["successors"]
        if result["resolved"]:
            resolved_this_cycle.update(_related_concern_ids_for_outcome(session, outcome))
        if result["successors"]:
            effect = _outcome_effect(outcome)
            successor_payload = effect.get("successor")
            if isinstance(successor_payload, dict) and str(successor_payload.get("concern_id")).isdigit():
                resolved_this_cycle.add(int(successor_payload["concern_id"]))

    for concern in session.scalars(
        select(Concern).where(Concern.state.in_(["active", "seed", "dormant", "resolved"]))
    ).all():
        if concern.state == "seed" and (
            concern.recurrence_score >= 0.25
            or concern.unresolvedness >= 0.70
            or concern.self_relevance >= 0.70
            or concern.attempt_pressure >= 0.55
        ):
            transition_concern_state(
                session,
                concern,
                "active",
                event_type="activated",
                reason="Review promoted seed concern because recurrence or pressure crossed threshold.",
            )
            counts["activated"] += 1
        elif concern.state == "active" and (
            concern.activation_score < 0.75
            and concern.unresolvedness < 0.45
            and concern.attempt_pressure < 0.35
        ):
            transition_concern_state(
                session,
                concern,
                "dormant",
                event_type="dormant",
                reason="Review made concern dormant after low activation and low unresolvedness.",
            )
            counts["dormant"] += 1
        elif (
            concern.state == "resolved"
            and concern.id not in resolved_this_cycle
            and concern.activation_score <= 0.2
        ):
            transition_concern_state(
                session,
                concern,
                "archived",
                event_type="archived",
                reason="Resolved concern remained low-activation and was archived.",
            )
            counts["archived"] += 1
    session.flush()
    return counts
