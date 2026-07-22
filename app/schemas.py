"""Pydantic schemas used between adapters, cognition modules, and runtime cycles."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class RawEventInput(BaseModel):
    source_type: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    content_text: str
    happened_at: datetime | None = None


class ProbePlan(BaseModel):
    trigger_type: str = "scheduler"
    source_type: Literal[
        "local_file",
        "web_search",
        "memory",
        "concern",
        "random_environment_sample",
    ] = "local_file"
    query_or_path: str
    rationale: str
    expected_gain: str
    related_concern_ids: list[int] = Field(default_factory=list)
    exploration_mode: str
    budget: dict[str, Any] = Field(default_factory=dict)


class ObservationDraft(BaseModel):
    source_event_id: int
    source_probe_id: int | None = None
    summary: str
    entities: list[str] = Field(default_factory=list)
    salience: float = Field(ge=0.0, le=1.0)
    novelty: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(ge=0.0, le=1.0)
    emotional_charge: float = Field(ge=0.0, le=1.0)
    self_relevance: float = Field(ge=0.0, le=1.0)
    possible_disposition: str
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)


class DigestDecision(BaseModel):
    observation_id: int
    disposition: Literal[
        "concern_candidate",
        "memory_candidate",
        "action_candidate",
        "discard",
        "no_op",
        "ignored",
    ]
    reason: str


class ContextBundle(BaseModel):
    system_prompt: str
    prompt_summary: str
    selected_memory_ids: list[int]
    selected_concerns: list[dict[str, Any]]
    selected_attention_policy: dict[str, Any]
    concern_modes: dict[str, str]
