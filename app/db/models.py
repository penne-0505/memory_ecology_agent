"""SQLAlchemy models for the trace-first PoC."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.db.json_utils import json_dumps


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class RawEvent(Base):
    __tablename__ = "raw_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_type: Mapped[str] = mapped_column(Text)
    event_type: Mapped[str] = mapped_column(Text)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    content_text: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(Text)
    happened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class InputProbe(Base):
    __tablename__ = "input_probes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trigger_type: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(Text)
    query_or_path: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text)
    expected_gain: Mapped[str] = mapped_column(Text)
    related_concern_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    exploration_mode: Mapped[str] = mapped_column(Text)
    budget_json: Mapped[str] = mapped_column(Text, default="{}")
    budget_used_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(Text, default="planned")
    result_summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_event_id: Mapped[int] = mapped_column(Integer)
    source_probe_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    entities_json: Mapped[str] = mapped_column(Text, default="[]")
    salience: Mapped[float] = mapped_column(Float, default=0.0)
    novelty: Mapped[float] = mapped_column(Float, default=0.0)
    uncertainty: Mapped[float] = mapped_column(Float, default=0.0)
    emotional_charge: Mapped[float] = mapped_column(Float, default=0.0)
    self_relevance: Mapped[float] = mapped_column(Float, default=0.0)
    possible_disposition: Mapped[str] = mapped_column(Text, default="discard")
    rationale: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DigestDecisionTrace(Base):
    __tablename__ = "digest_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(Text, default="")
    source_observation_id: Mapped[int] = mapped_column(Integer)
    source_raw_event_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    decision: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    salience_snapshot: Mapped[float] = mapped_column(Float, default=0.0)
    novelty_snapshot: Mapped[float] = mapped_column(Float, default=0.0)
    uncertainty_snapshot: Mapped[float] = mapped_column(Float, default=0.0)
    self_relevance_snapshot: Mapped[float] = mapped_column(Float, default=0.0)
    related_concern_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DigestDecisionProposal(Base):
    __tablename__ = "digest_decision_proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    observation_id: Mapped[int] = mapped_column(Integer)
    deterministic_digest_decision_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    final_digest_decision_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    proposal_source: Mapped[str] = mapped_column(Text, default="llm")
    provider: Mapped[str] = mapped_column(Text, default="")
    model: Mapped[str] = mapped_column(Text, default="")
    prompt_version: Mapped[str] = mapped_column(Text, default="")
    proposed_decision: Mapped[str] = mapped_column(Text, default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_summary: Mapped[str] = mapped_column(Text, default="")
    evidence_quote_short: Mapped[str] = mapped_column(Text, default="")
    related_concern_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    alternative_decision: Mapped[str] = mapped_column(Text, default="")
    risk_flags_json: Mapped[str] = mapped_column(Text, default="[]")
    should_apply: Mapped[bool] = mapped_column(Boolean, default=False)
    model_should_apply: Mapped[bool] = mapped_column(Boolean, default=False)
    should_apply_normalized: Mapped[bool] = mapped_column(Boolean, default=False)
    normalization_reason: Mapped[str] = mapped_column(Text, default="")
    schema_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    error_class: Mapped[str] = mapped_column(Text, default="")
    error_message_sanitized: Mapped[str] = mapped_column(Text, default="")
    raw_response_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_response_persisted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Concern(Base):
    __tablename__ = "concerns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    object_json: Mapped[str] = mapped_column(Text, default="{}")
    tension_json: Mapped[str] = mapped_column(Text, default="{}")
    closure_hypothesis: Mapped[str] = mapped_column(Text, default="")
    state: Mapped[str] = mapped_column(Text, default="seed")
    activation_score: Mapped[float] = mapped_column(Float, default=0.0)
    unresolvedness: Mapped[float] = mapped_column(Float, default=0.0)
    recurrence_score: Mapped[float] = mapped_column(Float, default=0.0)
    self_relevance: Mapped[float] = mapped_column(Float, default=0.0)
    external_relevance: Mapped[float] = mapped_column(Float, default=0.0)
    attempt_pressure: Mapped[float] = mapped_column(Float, default=0.0)
    saturation_penalty: Mapped[float] = mapped_column(Float, default=0.0)
    last_observed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_acted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    opened_reason: Mapped[str] = mapped_column(Text, default="")
    source_observation_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    closure_mode: Mapped[str] = mapped_column(Text, default="")
    closed_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    successor_concern_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class ConcernEvent(Base):
    __tablename__ = "concern_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    concern_id: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(Text)
    delta_json: Mapped[str] = mapped_column(Text, default="{}")
    reason: Mapped[str] = mapped_column(Text)
    source_observation_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    source_action_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    stability: Mapped[float] = mapped_column(Float, default=0.0)
    source_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    related_concern_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class AttentionPolicy(Base):
    __tablename__ = "attention_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version: Mapped[int] = mapped_column(Integer)
    source_preferences_json: Mapped[str] = mapped_column(Text, default="{}")
    salience_preferences_json: Mapped[str] = mapped_column(Text, default="{}")
    concern_type_preferences_json: Mapped[str] = mapped_column(Text, default="{}")
    action_preferences_json: Mapped[str] = mapped_column(Text, default="{}")
    response_preferences_json: Mapped[str] = mapped_column(Text, default="{}")
    exploration_randomness: Mapped[float] = mapped_column(Float, default=0.25)
    stability: Mapped[float] = mapped_column(Float, default=0.75)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class AttentionPolicyEvent(Base):
    __tablename__ = "attention_policy_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attention_policy_id: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(Text)
    target_field: Mapped[str] = mapped_column(Text)
    delta_json: Mapped[str] = mapped_column(Text, default="{}")
    reason: Mapped[str] = mapped_column(Text)
    evidence_observation_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    evidence_action_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    evidence_outcome_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CoreProfile(Base):
    __tablename__ = "core_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    locked: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CoreChangeProposal(Base):
    __tablename__ = "core_change_proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proposed_change: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    supporting_events_json: Mapped[str] = mapped_column(Text, default="[]")
    risk: Mapped[str] = mapped_column(Text, default="Medium")
    status: Mapped[str] = mapped_column(Text, default="proposed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SelfModelSnapshot(Base):
    __tablename__ = "self_model_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    summary: Mapped[str] = mapped_column(Text)
    stable_traits_json: Mapped[str] = mapped_column(Text, default="[]")
    current_dispositions_json: Mapped[str] = mapped_column(Text, default="[]")
    known_limitations_json: Mapped[str] = mapped_column(Text, default="[]")
    source_memory_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    source_concern_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    source_attention_policy_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action_type: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text)
    related_concern_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    input_probe_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    external_effect: Mapped[str] = mapped_column(Text, default="internal")
    status: Mapped[str] = mapped_column(Text, default="planned")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Outcome(Base):
    __tablename__ = "outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action_id: Mapped[int] = mapped_column(Integer)
    observed_result: Mapped[str] = mapped_column(Text)
    user_feedback: Mapped[str] = mapped_column(Text, default="")
    effect_on_concerns_json: Mapped[str] = mapped_column(Text, default="{}")
    effect_on_attention_policy_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WakeRequest(Base):
    __tablename__ = "wake_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    requested_by_action_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    not_before: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    preferred_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    urgency: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str] = mapped_column(Text)
    accepted_by_scheduler: Mapped[bool] = mapped_column(Boolean, default=False)
    scheduler_decision_reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ResponseTrace(Base):
    __tablename__ = "response_traces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_message_event_id: Mapped[int] = mapped_column(Integer)
    response_action_id: Mapped[int] = mapped_column(Integer)
    selected_memory_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    selected_concerns_json: Mapped[str] = mapped_column(Text, default="[]")
    selected_attention_policy_json: Mapped[str] = mapped_column(Text, default="{}")
    concern_modes_json: Mapped[str] = mapped_column(Text, default="{}")
    prompt_summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EvalPrompt(Base):
    __tablename__ = "eval_prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    prompt: Mapped[str] = mapped_column(Text)
    expected_dimension: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReplayRun(Base):
    __tablename__ = "replay_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    eval_prompt_id: Mapped[int] = mapped_column(Integer)
    state_snapshot_ref: Mapped[str] = mapped_column(Text, default="{}")
    response_text: Mapped[str] = mapped_column(Text)
    selected_concerns_json: Mapped[str] = mapped_column(Text, default="[]")
    selected_memories_json: Mapped[str] = mapped_column(Text, default="[]")
    selected_attention_policy_json: Mapped[str] = mapped_column(Text, default="{}")
    evaluator_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


INITIAL_ATTENTION_POLICY = {
    "source_preferences_json": json_dumps(
        {
            "local_file": 0.45,
            "web": 0.15,
            "memory": 0.20,
            "conversation": 0.15,
            "random_sample": 0.05,
        }
    ),
    "salience_preferences_json": json_dumps(
        {
            "novelty": 0.35,
            "uncertainty": 0.55,
            "self_relevance": 0.60,
            "urgency": 0.30,
            "contradiction": 0.65,
        }
    ),
    "concern_type_preferences_json": json_dumps(
        {
            "implementation_tension": 0.55,
            "user_correction": 0.70,
            "unknown_unknown": 0.40,
        }
    ),
    "action_preferences_json": json_dumps(
        {
            "respond": 0.60,
            "ask_user": 0.45,
            "read_local_file": 0.65,
            "write_internal_note": 0.35,
            "request_wake": 0.30,
        }
    ),
    "response_preferences_json": json_dumps(
        {
            "prefer_influence_over_mention": 0.75,
            "avoid_self_talk": 0.80,
            "ask_when_uncertain": 0.55,
            "mention_internal_state": 0.35,
        }
    ),
    "exploration_randomness": 0.25,
    "stability": 0.75,
}
