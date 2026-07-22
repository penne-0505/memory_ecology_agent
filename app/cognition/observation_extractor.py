"""Observation extraction from raw events."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy.orm import Session

from app.adapters.llm import LLMClient, LLMProviderError, create_llm_client
from app.config import Settings
from app.db.json_utils import json_dumps
from app.db.models import Observation, RawEvent
from app.schemas import ObservationDraft


SUMMARY_LIMIT = 220
RATIONALE_LIMIT = 260
EVIDENCE_QUOTE_LIMIT = 160
USER_INPUT_LIMIT = 6_000
PROMPT_PATH = (
    Path(__file__).resolve().parents[1] / "prompts" / "observation_extraction_llm.md"
)

KEY_TERMS = {
    "risk",
    "trace",
    "concern",
    "memory",
    "policy",
    "correction",
    "boundary",
    "secret",
    "implementation",
    "uncertain",
    "question",
}


class ObservationExtractorError(RuntimeError):
    """Observation extraction failed after applying configured fallback policy."""


class LLMObservationProposal(BaseModel):
    summary: str = Field(min_length=1, max_length=SUMMARY_LIMIT)
    entities: list[str] = Field(default_factory=list, max_length=12)
    salience: float
    novelty: float
    uncertainty: float
    emotional_charge: float
    self_relevance: float
    possible_disposition: Literal[
        "concern_candidate",
        "memory_candidate",
        "discard",
        "action_candidate",
    ]
    rationale: str = Field(min_length=1, max_length=RATIONALE_LIMIT)
    evidence_quote: str = Field(default="", max_length=EVIDENCE_QUOTE_LIMIT)
    confidence: float

    @field_validator(
        "salience",
        "novelty",
        "uncertainty",
        "emotional_charge",
        "self_relevance",
        "confidence",
        mode="before",
    )
    @classmethod
    def _clamp_score(cls, value: object) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = 0.0
        return max(0.0, min(1.0, number))

    @field_validator("summary", "rationale", "evidence_quote", mode="before")
    @classmethod
    def _normalize_text(cls, value: object) -> str:
        text = "" if value is None else str(value)
        return " ".join(text.split())

    @field_validator("entities", mode="before")
    @classmethod
    def _normalize_entities(cls, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        entities: list[str] = []
        for item in value:
            text = " ".join(str(item).split()).lower()
            if text and text not in entities:
                entities.append(text[:80])
            if len(entities) >= 12:
                break
        return entities


class LLMObservationResponse(BaseModel):
    observations: list[LLMObservationProposal] = Field(min_length=1, max_length=5)


@dataclass(frozen=True)
class ObservationExtractionResult:
    drafts: list[ObservationDraft]
    metadata: dict[str, object]

    @property
    def draft(self) -> ObservationDraft:
        return self.drafts[0]


def _clip_summary(text: str, limit: int = 180) -> str:
    normalized = " ".join(text.split())
    return normalized[:limit] if normalized else "(empty input)"


def _entities(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", text)
    seen: list[str] = []
    for word in words:
        lowered = word.lower()
        if lowered not in seen:
            seen.append(lowered)
        if len(seen) >= 8:
            break
    return seen


def extract_observations_deterministic(
    raw_event: RawEvent, source_probe_id: int | None
) -> ObservationExtractionResult:
    text = raw_event.content_text
    lowered = text.lower()
    hits = sum(1 for term in KEY_TERMS if term in lowered)
    salience = min(1.0, 0.25 + hits * 0.12)
    uncertainty = (
        0.65 if any(term in lowered for term in ["?", "uncertain", "risk"]) else 0.25
    )
    self_relevance = (
        0.75
        if any(term in lowered for term in ["agent", "poc", "implementation"])
        else 0.35
    )
    novelty = 0.60 if raw_event.source_type == "local_file" else 0.45
    emotional_charge = 0.45 if "correction" in lowered else 0.20
    disposition = (
        "concern_candidate"
        if salience >= 0.45 or uncertainty >= 0.6
        else "memory_candidate"
    )
    draft = ObservationDraft(
        source_event_id=raw_event.id,
        source_probe_id=source_probe_id,
        summary=_clip_summary(text),
        entities=_entities(text),
        salience=salience,
        novelty=novelty,
        uncertainty=uncertainty,
        emotional_charge=emotional_charge,
        self_relevance=self_relevance,
        possible_disposition=disposition,
        rationale=(
            "Heuristic extractor scored key terms and uncertainty markers; "
            f"hits={hits}, source={raw_event.source_type}."
        ),
        confidence=0.72 if raw_event.source_type == "local_file" else 0.55,
    )
    return ObservationExtractionResult(
        drafts=[draft],
        metadata={
            "extractor": "deterministic",
            "provider": "none",
            "fallback": False,
        },
    )


def draft_observation(
    raw_event: RawEvent, source_probe_id: int | None
) -> ObservationDraft:
    return extract_observations_deterministic(raw_event, source_probe_id).draft


def _load_llm_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _llm_user_payload(raw_event: RawEvent) -> str:
    content = raw_event.content_text[:USER_INPUT_LIMIT]
    truncated = len(raw_event.content_text) > USER_INPUT_LIMIT
    return "\n".join(
        [
            f"source_type: {raw_event.source_type}",
            f"event_type: {raw_event.event_type}",
            f"content_truncated: {str(truncated).lower()}",
            "raw_input:",
            content,
        ]
    )


def _proposal_to_draft(
    proposal: LLMObservationProposal,
    raw_event: RawEvent,
    source_probe_id: int | None,
    provider: str,
) -> ObservationDraft:
    rationale_parts = [
        f"LLM observation proposal via provider={provider}.",
        proposal.rationale,
    ]
    if proposal.evidence_quote:
        rationale_parts.append(f"evidence_quote={proposal.evidence_quote!r}")
    return ObservationDraft(
        source_event_id=raw_event.id,
        source_probe_id=source_probe_id,
        summary=proposal.summary,
        entities=proposal.entities,
        salience=proposal.salience,
        novelty=proposal.novelty,
        uncertainty=proposal.uncertainty,
        emotional_charge=proposal.emotional_charge,
        self_relevance=proposal.self_relevance,
        possible_disposition=proposal.possible_disposition,
        rationale=" ".join(rationale_parts)[:420],
        confidence=proposal.confidence,
    )


def extract_observations_llm(
    raw_event: RawEvent,
    source_probe_id: int | None,
    settings: Settings,
    llm_client: LLMClient | None = None,
) -> ObservationExtractionResult:
    client = llm_client or create_llm_client(settings, temperature=0.0)
    response = client.complete_json(
        _load_llm_prompt(),
        _llm_user_payload(raw_event),
        LLMObservationResponse,
    )
    provider = settings.llm_provider or client.__class__.__name__
    drafts = [
        _proposal_to_draft(proposal, raw_event, source_probe_id, provider)
        for proposal in response.observations
    ]
    return ObservationExtractionResult(
        drafts=drafts,
        metadata={
            "extractor": "llm",
            "provider": provider,
            "fallback": False,
            "model": settings.llm_model or "(provider-specific env or unset)",
        },
    )


def _fallback_result(
    raw_event: RawEvent,
    source_probe_id: int | None,
    settings: Settings,
    error: Exception,
) -> ObservationExtractionResult:
    if settings.observation_extractor_fallback == "error":
        raise ObservationExtractorError(
            f"LLM observation extraction failed: {error.__class__.__name__}"
        ) from error
    if settings.observation_extractor_fallback != "deterministic":
        raise ObservationExtractorError(
            "AGENT_OBSERVATION_EXTRACTOR_FALLBACK must be deterministic or error."
        ) from error
    fallback = extract_observations_deterministic(raw_event, source_probe_id)
    metadata = {
        **fallback.metadata,
        "requested_extractor": "llm",
        "fallback": True,
        "fallback_reason": error.__class__.__name__,
        "fallback_provider": settings.llm_provider,
    }
    fallback.drafts[0].rationale = (
        "LLM observation extraction failed safely; deterministic fallback used. "
        f"reason={error.__class__.__name__}. {fallback.drafts[0].rationale}"
    )
    return ObservationExtractionResult(drafts=fallback.drafts, metadata=metadata)


def extract_observation(
    raw_event: RawEvent,
    source_probe_id: int | None,
    settings: Settings,
    llm_client: LLMClient | None = None,
) -> ObservationExtractionResult:
    extractor = settings.observation_extractor
    if extractor in ("", "deterministic"):
        return extract_observations_deterministic(raw_event, source_probe_id)
    if extractor != "llm":
        raise ObservationExtractorError(
            "AGENT_OBSERVATION_EXTRACTOR must be deterministic or llm."
        )
    try:
        return extract_observations_llm(raw_event, source_probe_id, settings, llm_client)
    except (LLMProviderError, RuntimeError, ValidationError, ValueError) as exc:
        return _fallback_result(raw_event, source_probe_id, settings, exc)


def persist_observation(session: Session, draft: ObservationDraft) -> Observation:
    observation = Observation(
        source_event_id=draft.source_event_id,
        source_probe_id=draft.source_probe_id,
        summary=draft.summary,
        entities_json=json_dumps(draft.entities),
        salience=draft.salience,
        novelty=draft.novelty,
        uncertainty=draft.uncertainty,
        emotional_charge=draft.emotional_charge,
        self_relevance=draft.self_relevance,
        possible_disposition=draft.possible_disposition,
        rationale=draft.rationale,
        confidence=draft.confidence,
    )
    session.add(observation)
    session.flush()
    return observation
