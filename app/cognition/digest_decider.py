"""LLM-backed digest proposal generation and safe arbitration."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.llm import (
    LLMClient,
    LLMProviderError,
    create_llm_client,
    openrouter_json_schema_payload,
)
from app.config import Settings
from app.db.json_utils import json_dumps
from app.db.models import Concern, DigestDecisionProposal, Observation
from app.schemas import DigestDecision


PROMPT_VERSION = "digest_decision_llm.v3"
PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "digest_decision_llm.md"
DECISIONS = {
    "concern_candidate",
    "memory_candidate",
    "discard",
    "action_candidate",
    "no_op",
}
TEXT_LIMIT = 180
QUOTE_LIMIT = 120
USER_PAYLOAD_LIMIT = 2_500
SECRET_PATTERN = re.compile(
    r"(sk-[A-Za-z0-9_-]{8,}|[A-Za-z0-9_]*API[_-]?KEY|Authorization:|Bearer\s+[A-Za-z0-9._-]+)",
    re.IGNORECASE,
)


class DigestProposalError(RuntimeError):
    """LLM digest proposal failed but deterministic digest may continue."""


class LLMDigestProposal(BaseModel):
    decision: Literal[
        "concern_candidate",
        "memory_candidate",
        "discard",
        "action_candidate",
        "no_op",
    ]
    reason: str = Field(default="", max_length=TEXT_LIMIT)
    confidence: float = 0.0
    evidence_summary: str = Field(default="", max_length=TEXT_LIMIT)
    evidence_quote: str = Field(default="", max_length=QUOTE_LIMIT)
    related_concern_ids: list[int] = Field(default_factory=list, max_length=12)
    alternative_decision: Literal[
        "concern_candidate",
        "memory_candidate",
        "discard",
        "action_candidate",
        "no_op",
    ] = "discard"
    risk_flags: list[str] = Field(default_factory=list, max_length=12)
    should_apply: bool = False

    @field_validator("confidence", mode="before")
    @classmethod
    def _clamp_confidence(cls, value: object) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = 0.0
        return max(0.0, min(1.0, number))

    @field_validator("reason", "evidence_summary", "evidence_quote", mode="before")
    @classmethod
    def _normalize_text(cls, value: object) -> str:
        text = "" if value is None else str(value)
        return " ".join(text.split())

    @field_validator("risk_flags", mode="before")
    @classmethod
    def _normalize_flags(cls, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        flags: list[str] = []
        for item in value:
            flag = " ".join(str(item).lower().split())[:80]
            if flag and flag not in flags:
                flags.append(flag)
        return flags


@dataclass(frozen=True)
class DigestProposalResult:
    proposal: DigestDecisionProposal | None
    agreement: bool | None
    fallback_used: bool
    arbitration_reason: str
    deterministic_decision: DigestDecision
    final_decision: DigestDecision
    assisted_gate_result: str = "not_applicable"
    assisted_gate_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class ShouldApplyNormalization:
    model_should_apply: bool
    normalized_should_apply: bool
    reason: str


def _load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _sanitize_error(error: Exception) -> str:
    if isinstance(error, ValidationError):
        counts: dict[str, int] = {}
        for item in error.errors():
            loc = ".".join(str(part) for part in item.get("loc", ())) or "(root)"
            error_type = str(item.get("type") or "unknown")
            key = f"{loc}:{error_type}"
            counts[key] = counts.get(key, 0) + 1
        if counts:
            return json.dumps(counts, sort_keys=True)
    return error.__class__.__name__


def _raw_hash(text: str | None) -> str | None:
    if not text:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _contains_secret_like_text(*values: str) -> bool:
    return any(SECRET_PATTERN.search(value or "") for value in values)


def _clip(text: str, limit: int) -> str:
    normalized = " ".join((text or "").split())
    return normalized[:limit]


def _active_concerns(session: Session) -> list[Concern]:
    return session.scalars(
        select(Concern).where(Concern.state != "closed").order_by(Concern.id).limit(8)
    ).all()


def _user_payload(
    session: Session, observation: Observation, deterministic_decision: DigestDecision
) -> str:
    concerns = _active_concerns(session)
    concern_lines = [
        f"- concern#{concern.id} state={concern.state} title={_clip(concern.title, 100)}"
        for concern in concerns
    ]
    return "\n".join(
        [
            f"observation_id: {observation.id}",
            f"source_event_id: {observation.source_event_id}",
            f"source_type: raw_event#{observation.source_event_id}",
            f"summary: {_clip(observation.summary, USER_PAYLOAD_LIMIT)}",
            "scores:",
            f"- salience: {observation.salience:.2f}",
            f"- novelty: {observation.novelty:.2f}",
            f"- uncertainty: {observation.uncertainty:.2f}",
            f"- self_relevance: {observation.self_relevance:.2f}",
            f"possible_disposition: {observation.possible_disposition}",
            f"deterministic_decision_for_comparison: {deterministic_decision.disposition}",
            "active_or_dormant_concerns:",
            *(concern_lines or ["- none"]),
        ]
    )


def _parse_json_text(text: str) -> object:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return json.loads(stripped)


def _known_related_ids(session: Session, related_ids: list[int]) -> list[int]:
    if not related_ids:
        return []
    known = set(
        session.scalars(select(Concern.id).where(Concern.id.in_(related_ids))).all()
    )
    return [concern_id for concern_id in related_ids if concern_id in known]


def normalize_should_apply(proposal: LLMDigestProposal) -> ShouldApplyNormalization:
    blocked_flags = {
        "manual_follow_up",
        "core_profile_boundary",
        "self_model_boundary",
        "safety_boundary",
        "discord_mode_boundary",
        "unknown_context",
        "low_confidence",
        "ambiguous_memory_vs_concern",
        "ambiguous_discard_vs_memory",
        "possible_over_action",
    }
    flags = set(proposal.risk_flags)
    model_should_apply = bool(proposal.should_apply)

    if proposal.decision not in {"memory_candidate", "discard"}:
        return ShouldApplyNormalization(
            model_should_apply,
            False,
            "decision_not_auto_applicable",
        )
    if proposal.confidence < 0.90:
        return ShouldApplyNormalization(
            model_should_apply,
            False,
            "confidence_below_threshold",
        )
    if flags & blocked_flags:
        return ShouldApplyNormalization(
            model_should_apply,
            False,
            "blocked_risk_flag",
        )
    if proposal.decision == "memory_candidate":
        allowed = {"stable_fact", "user_feedback", "project_requirement", "traceability"}
        if flags.issubset(allowed):
            return ShouldApplyNormalization(model_should_apply, True, "allowed_memory")
        return ShouldApplyNormalization(
            model_should_apply,
            False,
            "unsupported_memory_risk_flag",
        )
    if proposal.decision == "discard":
        allowed = {"low_signal", "repetition"}
        if flags.issubset(allowed):
            return ShouldApplyNormalization(model_should_apply, True, "allowed_discard")
        return ShouldApplyNormalization(
            model_should_apply,
            False,
            "unsupported_discard_risk_flag",
        )
    return ShouldApplyNormalization(
        model_should_apply,
        False,
        "not_applicable",
    )


def _persist_rejected_proposal(
    session: Session,
    observation: Observation,
    settings: Settings,
    error: Exception,
    *,
    raw_text: str | None = None,
) -> DigestDecisionProposal:
    proposal = DigestDecisionProposal(
        observation_id=observation.id,
        proposal_source="llm",
        provider=settings.llm_provider,
        model=settings.llm_model or "(provider-specific env or unset)",
        prompt_version=PROMPT_VERSION,
        proposed_decision="",
        reason="",
        confidence=0.0,
        evidence_summary="",
        evidence_quote_short="",
        related_concern_ids_json=json_dumps([]),
        alternative_decision="",
        risk_flags_json=json_dumps([]),
        should_apply=False,
        model_should_apply=False,
        should_apply_normalized=False,
        normalization_reason="proposal_rejected",
        schema_valid=False,
        fallback_used=True,
        error_class=error.__class__.__name__,
        error_message_sanitized=_sanitize_error(error),
        raw_response_hash=_raw_hash(raw_text),
        raw_response_persisted=False,
    )
    session.add(proposal)
    session.flush()
    return proposal


def _persist_valid_proposal(
    session: Session,
    observation: Observation,
    settings: Settings,
    parsed: LLMDigestProposal,
    provider: str,
    model: str | None,
    raw_text: str,
) -> DigestDecisionProposal:
    related_ids = _known_related_ids(session, parsed.related_concern_ids)
    normalization = normalize_should_apply(parsed)
    unsafe = _contains_secret_like_text(
        raw_text, parsed.reason, parsed.evidence_summary, parsed.evidence_quote
    )
    proposal = DigestDecisionProposal(
        observation_id=observation.id,
        proposal_source="llm",
        provider=provider,
        model=model or settings.llm_model or "(provider-specific env or unset)",
        prompt_version=PROMPT_VERSION,
        proposed_decision=parsed.decision if not unsafe else "",
        reason="" if unsafe else parsed.reason,
        confidence=parsed.confidence if not unsafe else 0.0,
        evidence_summary="" if unsafe else parsed.evidence_summary,
        evidence_quote_short="" if unsafe else parsed.evidence_quote,
        related_concern_ids_json=json_dumps(related_ids),
        alternative_decision=parsed.alternative_decision if not unsafe else "",
        risk_flags_json=json_dumps(parsed.risk_flags if not unsafe else ["unsafe_output"]),
        should_apply=normalization.normalized_should_apply if not unsafe else False,
        model_should_apply=normalization.model_should_apply if not unsafe else False,
        should_apply_normalized=normalization.normalized_should_apply if not unsafe else False,
        normalization_reason=normalization.reason if not unsafe else "unsafe_output",
        schema_valid=not unsafe,
        fallback_used=unsafe,
        error_class="UnsafeOutput" if unsafe else "",
        error_message_sanitized="UnsafeOutput" if unsafe else "",
        raw_response_hash=_raw_hash(raw_text),
        raw_response_persisted=False,
    )
    session.add(proposal)
    session.flush()
    return proposal


def _request_llm_proposal(
    session: Session,
    observation: Observation,
    deterministic_decision: DigestDecision,
    settings: Settings,
    llm_client: LLMClient | None = None,
    raw_failure_diagnostic: Callable[[dict[str, Any]], None] | None = None,
) -> DigestDecisionProposal:
    structured_payload = _structured_output_payload(settings)
    client = llm_client or create_llm_client(
        settings,
        temperature=0.0,
        extra_payload=structured_payload,
    )
    result = client.complete_text_with_metadata(
        _load_prompt(),
        _user_payload(session, observation, deterministic_decision),
    )
    try:
        parsed = LLMDigestProposal.model_validate(_parse_json_text(result.text))
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        if raw_failure_diagnostic is not None:
            raw_failure_diagnostic(
                {
                    "observation_id": observation.id,
                    "provider": result.provider or settings.llm_provider,
                    "model": result.model or settings.llm_model,
                    "error_class": exc.__class__.__name__,
                    "error_message_sanitized": _sanitize_error(exc),
                    "raw_response_text": result.text,
                    "usage": result.usage,
                    "response_metadata": result.response_metadata,
                }
            )
        return _persist_rejected_proposal(
            session, observation, settings, exc, raw_text=result.text
        )
    provider = result.provider or settings.llm_provider
    return _persist_valid_proposal(
        session, observation, settings, parsed, provider, result.model, result.text
    )


def _structured_output_payload(settings: Settings) -> dict[str, object] | None:
    provider = settings.llm_provider.strip().lower()
    if provider != "openrouter":
        return None
    payload = openrouter_json_schema_payload(
        LLMDigestProposal,
        name="llm_digest_proposal",
        strict=True,
        require_parameters=True,
    )
    reasoning = _openrouter_reasoning_payload()
    if reasoning:
        payload["reasoning"] = reasoning
    return payload


def _openrouter_reasoning_payload() -> dict[str, object]:
    effort = os.environ.get("AGENT_OPENROUTER_REASONING_EFFORT", "").strip().lower()
    exclude_raw = os.environ.get("AGENT_OPENROUTER_REASONING_EXCLUDE", "").strip().lower()
    reasoning: dict[str, object] = {}
    if effort:
        reasoning["effort"] = effort
    if exclude_raw in {"1", "true", "yes", "on"}:
        reasoning["exclude"] = True
    elif exclude_raw in {"0", "false", "no", "off"}:
        reasoning["exclude"] = False
    return reasoning


def _assisted_gate(
    proposal: DigestDecisionProposal, deterministic_decision: DigestDecision
) -> tuple[str, tuple[str, ...]]:
    reasons: list[str] = []
    if not proposal.schema_valid:
        reasons.append("proposal_not_schema_valid")
    if proposal.fallback_used:
        reasons.append("proposal_fallback_used")
    if proposal.raw_response_persisted:
        reasons.append("raw_response_persisted")
    if proposal.proposed_decision not in {"memory_candidate", "discard"}:
        reasons.append("decision_not_assisted_confirmable")
    if proposal.proposed_decision != deterministic_decision.disposition:
        reasons.append("deterministic_disagreement")
    if not proposal.should_apply_normalized:
        reasons.append("normalized_should_apply_false")
    if reasons:
        return "rejected", tuple(reasons)
    return "accepted", ("accepted_memory_discard_confirm",)


def _assisted_final_decision(
    proposal: DigestDecisionProposal, deterministic_decision: DigestDecision
) -> DigestDecision:
    return DigestDecision(
        observation_id=deterministic_decision.observation_id,
        disposition=proposal.proposed_decision,
        reason=f"LLM assisted confirm accepted: {proposal.reason}",
    )


def create_digest_proposal(
    session: Session,
    observation: Observation,
    deterministic_decision: DigestDecision,
    settings: Settings,
    llm_client: LLMClient | None = None,
    raw_failure_diagnostic: Callable[[dict[str, Any]], None] | None = None,
) -> DigestProposalResult:
    mode = settings.digest_decider
    if mode in ("", "deterministic"):
        return DigestProposalResult(
            proposal=None,
            agreement=None,
            fallback_used=False,
            arbitration_reason="deterministic mode; no LLM digest proposal requested.",
            deterministic_decision=deterministic_decision,
            final_decision=deterministic_decision,
        )
    if mode not in {"llm_shadow", "llm_assisted"}:
        raise DigestProposalError(
            "AGENT_DIGEST_DECIDER must be deterministic, llm_shadow, or llm_assisted."
        )
    try:
        proposal = _request_llm_proposal(
            session,
            observation,
            deterministic_decision,
            settings,
            llm_client,
            raw_failure_diagnostic,
        )
    except (LLMProviderError, RuntimeError, ValueError) as exc:
        proposal = _persist_rejected_proposal(session, observation, settings, exc)
    agreement = (
        proposal.schema_valid
        and proposal.proposed_decision == deterministic_decision.disposition
    )
    assisted_gate_result = "not_applicable"
    assisted_gate_reasons: tuple[str, ...] = ()
    final_decision = deterministic_decision
    if not proposal.schema_valid:
        reason = "LLM proposal rejected; final decision remains deterministic."
    elif mode == "llm_shadow":
        reason = "Shadow mode records proposal only; final decision remains deterministic."
    else:
        assisted_gate_result, assisted_gate_reasons = _assisted_gate(
            proposal, deterministic_decision
        )
        if assisted_gate_result == "accepted":
            final_decision = _assisted_final_decision(proposal, deterministic_decision)
            reason = "llm_assisted confirm gate accepted proposal as final decision."
        else:
            reason = "llm_assisted confirm gate rejected proposal; final decision remains deterministic."
    return DigestProposalResult(
        proposal=proposal,
        agreement=agreement,
        fallback_used=proposal.fallback_used,
        arbitration_reason=reason,
        deterministic_decision=deterministic_decision,
        final_decision=final_decision,
        assisted_gate_result=assisted_gate_result,
        assisted_gate_reasons=assisted_gate_reasons,
    )


def proposal_metadata(result: DigestProposalResult, settings: Settings) -> dict[str, object]:
    metadata: dict[str, object] = {
        "digest_decider": settings.digest_decider,
        "arbitration_reason": result.arbitration_reason,
        "assisted_gate_result": result.assisted_gate_result,
        "assisted_gate_reasons": list(result.assisted_gate_reasons),
        "final_decision_source": (
            "llm_assisted_confirm"
            if result.assisted_gate_result == "accepted"
            else "deterministic"
        ),
    }
    if result.proposal is not None:
        metadata.update(
            {
                "proposal_id": result.proposal.id,
                "proposal_agreement": result.agreement,
                "proposal_fallback": result.fallback_used,
                "proposal_schema_valid": result.proposal.schema_valid,
                "proposal_decision": result.proposal.proposed_decision,
                "deterministic_decision": result.deterministic_decision.disposition,
                "final_decision": result.final_decision.disposition,
                "proposal_provider": result.proposal.provider,
                "proposal_model": result.proposal.model,
                "model_should_apply": result.proposal.model_should_apply,
                "normalized_should_apply": result.proposal.should_apply_normalized,
                "normalization_reason": result.proposal.normalization_reason,
            }
        )
    return metadata
