from __future__ import annotations

from dataclasses import replace

import pytest
from sqlalchemy import select

from app.adapters.llm import LLMProviderError, MockLLMClient
from app.cognition.observation_extractor import (
    ObservationExtractorError,
    extract_observation,
)
from app.db.json_utils import json_loads
from app.db.models import DigestDecisionTrace, Observation
from app.runtime.events import persist_raw_event
from app.runtime.wake_cycle import run_wake_cycle
from app.schemas import RawEventInput


def _raw_event(session, text: str = "Agent risk trace needs careful observation."):
    return persist_raw_event(
        session,
        RawEventInput(
            source_type="local_file",
            event_type="file_excerpt",
            payload={"path": "world/notes/example.md"},
            content_text=text,
        ),
    )


def _llm_response(**overrides):
    payload = {
        "summary": "A boundary concern is visible in the raw input.",
        "entities": ["Boundary", "Trace", "Boundary"],
        "salience": 1.5,
        "novelty": 0.4,
        "uncertainty": -0.2,
        "emotional_charge": 0.25,
        "self_relevance": 0.9,
        "possible_disposition": "concern_candidate",
        "rationale": "The input names a trace boundary that may need follow-up.",
        "evidence_quote": "trace boundary",
        "confidence": 0.8,
    }
    payload.update(overrides)
    return {"observations": [payload]}


def test_ac001_default_extractor_is_deterministic(seeded_session, settings):
    raw_event = _raw_event(seeded_session)

    result = extract_observation(raw_event, source_probe_id=None, settings=settings)

    assert result.metadata["extractor"] == "deterministic"
    assert result.metadata["provider"] == "none"
    assert result.metadata["fallback"] is False
    assert "Heuristic extractor" in result.draft.rationale


def test_ac002_ac004_llm_extractor_accepts_validated_proposal(
    seeded_session, settings
):
    raw_event = _raw_event(seeded_session)
    llm_settings = replace(
        settings,
        observation_extractor="llm",
        llm_provider="mock",
        llm_model="mock-observation-model",
    )
    client = MockLLMClient(json_response=_llm_response())

    result = extract_observation(
        raw_event, source_probe_id=7, settings=llm_settings, llm_client=client
    )

    assert result.metadata == {
        "extractor": "llm",
        "provider": "mock",
        "fallback": False,
        "model": "mock-observation-model",
    }
    assert result.draft.source_probe_id == 7
    assert result.draft.summary == "A boundary concern is visible in the raw input."
    assert result.draft.entities == ["boundary", "trace"]
    assert result.draft.salience == 1.0
    assert result.draft.uncertainty == 0.0
    assert result.draft.possible_disposition == "concern_candidate"
    assert "trace boundary" in result.draft.rationale


def test_ac005_invalid_llm_output_falls_back_without_raw_response(
    seeded_session, settings
):
    raw_event = _raw_event(seeded_session)
    llm_settings = replace(settings, observation_extractor="llm", llm_provider="mock")
    client = MockLLMClient(
        json_response=_llm_response(
            possible_disposition="mutate_core_profile",
            rationale="raw-secret-provider-output",
        )
    )

    result = extract_observation(
        raw_event, source_probe_id=None, settings=llm_settings, llm_client=client
    )

    assert result.metadata["extractor"] == "deterministic"
    assert result.metadata["requested_extractor"] == "llm"
    assert result.metadata["fallback"] is True
    assert result.metadata["fallback_reason"] == "ValidationError"
    assert "raw-secret-provider-output" not in result.draft.rationale


def test_ac005_provider_error_fallback_sanitizes_secret_like_message(
    seeded_session, settings
):
    class FailingClient(MockLLMClient):
        def complete_json(self, system, user, schema):
            raise LLMProviderError("provider failed with token sk-secret-value")

    raw_event = _raw_event(seeded_session)
    llm_settings = replace(
        settings,
        observation_extractor="llm",
        llm_provider="openrouter",
        llm_model="deepseek/deepseek-v4-pro",
    )

    result = extract_observation(
        raw_event, source_probe_id=None, settings=llm_settings, llm_client=FailingClient()
    )

    serialized = str(result.metadata) + result.draft.rationale
    assert result.metadata["fallback_reason"] == "LLMProviderError"
    assert "sk-secret-value" not in serialized
    assert "provider failed" not in serialized


def test_strict_llm_extractor_error_raises(seeded_session, settings):
    raw_event = _raw_event(seeded_session)
    llm_settings = replace(
        settings,
        observation_extractor="llm",
        observation_extractor_fallback="error",
        llm_provider="mock",
    )
    client = MockLLMClient(json_response={})

    with pytest.raises(ObservationExtractorError):
        extract_observation(
            raw_event, source_probe_id=None, settings=llm_settings, llm_client=client
        )


def test_ac006_wake_cycle_records_extractor_metadata(
    seeded_session, settings, monkeypatch
):
    llm_settings = replace(
        settings,
        observation_extractor="llm",
        llm_provider="mock",
        llm_model="mock-observation-model",
    )

    def fake_client(settings, transport=None, temperature=None, extra_payload=None):
        return MockLLMClient(json_response=_llm_response())

    monkeypatch.setattr("app.cognition.observation_extractor.create_llm_client", fake_client)

    result = run_wake_cycle(seeded_session, llm_settings, reason="llm-extraction-test")

    assert result["observations"] >= 1
    observation = seeded_session.scalar(select(Observation).order_by(Observation.id))
    decision = seeded_session.scalar(
        select(DigestDecisionTrace).order_by(DigestDecisionTrace.id)
    )
    assert observation is not None
    assert decision is not None
    assert "LLM observation proposal" in observation.rationale
    metadata = json_loads(decision.metadata_json, {})
    assert metadata["extractor"] == "llm"
    assert metadata["provider"] == "mock"
    assert metadata["fallback"] is False


def test_llm_extractor_can_persist_multiple_proposals(
    seeded_session, settings, monkeypatch
):
    llm_settings = replace(
        settings,
        observation_extractor="llm",
        llm_provider="mock",
        llm_model="mock-observation-model",
    )

    def fake_client(settings, transport=None, temperature=None, extra_payload=None):
        return MockLLMClient(
            json_response={
                "observations": [
                    _llm_response(summary="First proposal.")["observations"][0],
                    _llm_response(
                        summary="Second proposal.",
                        possible_disposition="memory_candidate",
                    )["observations"][0],
                ]
            }
        )

    monkeypatch.setattr(
        "app.cognition.observation_extractor.create_llm_client", fake_client
    )

    run_wake_cycle(seeded_session, llm_settings, reason="multi-proposal-test")

    observations = seeded_session.scalars(
        select(Observation).order_by(Observation.id)
    ).all()
    decisions = seeded_session.scalars(
        select(DigestDecisionTrace).order_by(DigestDecisionTrace.id)
    ).all()
    assert len(observations) >= 2
    assert observations[0].summary == "First proposal."
    assert observations[1].summary == "Second proposal."
    assert json_loads(decisions[0].metadata_json, {})["proposal_index"] == 0
    assert json_loads(decisions[1].metadata_json, {})["proposal_index"] == 1
