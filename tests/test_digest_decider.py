from __future__ import annotations

from dataclasses import replace
import json

from sqlalchemy import func, select

from app.adapters.llm import LLMProviderError, LLMTextResult, MockLLMClient
from app.cognition.digest_decider import (
    LLMDigestProposal,
    PROMPT_PATH,
    PROMPT_VERSION,
    create_digest_proposal,
    proposal_metadata,
)
from app.cognition.digestor import digest_observation
from app.db.json_utils import json_loads
from app.db.models import (
    Concern,
    CoreProfile,
    DigestDecisionProposal,
    DigestDecisionTrace,
    Memory,
    Observation,
)
from app.runtime.events import persist_raw_event
from app.runtime.wake_cycle import run_wake_cycle
from app.schemas import RawEventInput
from app.schemas import DigestDecision


class TextJsonClient(MockLLMClient):
    def __init__(self, text: str):
        super().__init__()
        self.text = text

    def complete_text_with_metadata(self, system, user):
        return LLMTextResult(
            provider="mock",
            model="mock-digest-model",
            text=self.text,
        )


class FailingTextClient(MockLLMClient):
    def complete_text_with_metadata(self, system, user):
        raise LLMProviderError("provider failed with sk-secret-value")


def _proposal_text(**overrides) -> str:
    payload = {
        "decision": "concern_candidate",
        "reason": "The observation contains unresolved trace risk.",
        "confidence": 0.82,
        "evidence_summary": "A trace boundary risk needs review.",
        "evidence_quote": "trace risk",
        "related_concern_ids": [],
        "alternative_decision": "discard",
        "risk_flags": [],
        "should_apply": False,
    }
    payload.update(overrides)
    import json

    return json.dumps(payload)


def _raw_event(session, text: str):
    return persist_raw_event(
        session,
        RawEventInput(
            source_type="local_file",
            event_type="file_excerpt",
            payload={"path": "world/notes/digest.md"},
            content_text=text,
        ),
    )


def _prompt_text() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _expected_json_after(prompt: str, observation_text: str) -> dict:
    start = prompt.index(f"Observation:\n{observation_text}")
    output_start = prompt.index("Output:\n", start) + len("Output:\n")
    payload, _ = json.JSONDecoder().raw_decode(prompt[output_start:].lstrip())
    return payload


def test_prompt_hardening_ac001_ac004_defines_decision_rubric():
    prompt = _prompt_text()
    normalized = " ".join(prompt.split())

    assert PROMPT_VERSION == "digest_decision_llm.v3"
    assert "Use concern_candidate only for a live unresolved tension" in prompt
    assert "Stable project facts" in normalized
    assert "reusable user feedback" in normalized
    assert "project requirement" in prompt
    assert "Use discard for low-value or redundant material" in prompt
    assert "Use action_candidate extremely rarely" in prompt
    assert "Use no_op only when no meaningful route exists" in prompt
    assert "0.75-0.89: strong but slightly ambiguous" in prompt
    assert "ambiguous_memory_vs_concern" in prompt
    assert "ambiguous_discard_vs_memory" in prompt


def test_prompt_hardening_ac002_ac003_forbids_action_adoption_and_mutation():
    prompt = _prompt_text()

    assert "Action_candidate from the LLM must never be adopted automatically" in prompt
    assert "Never set should_apply=true for action_candidate" in prompt
    assert "Do not create or modify memories" in prompt
    assert "You are not the final decision maker" in prompt
    for flag in [
        "manual_follow_up",
        "core_profile_boundary",
        "safety_boundary",
        "self_model_boundary",
        "discord_mode_boundary",
        "unknown_context",
        "low_confidence",
    ]:
        assert flag in prompt


def test_prompt_hardening_examples_cover_expected_boundaries():
    prompt = _prompt_text()

    stable = _expected_json_after(
        prompt,
        "Identity in this PoC is treated as an ecological loop: attention selects inputs, observations become memories or concerns, actions produce outcomes.",
    )
    assert stable["decision"] == "memory_candidate"
    assert stable["should_apply"] is False
    assert "stable_fact" in stable["risk_flags"]

    true_concern = _expected_json_after(
        prompt,
        "The agent repeatedly fails to distinguish trace output from ingestable user input, creating a risk of self-ingestion.",
    )
    assert true_concern["decision"] == "concern_candidate"
    assert true_concern["should_apply"] is False
    assert "unresolved_tension" in true_concern["risk_flags"]

    repeated = _expected_json_after(
        prompt,
        "Coffee receipt, keyboard cleaning, window chair note. Coffee receipt, keyboard cleaning, window chair note.",
    )
    assert repeated["decision"] == "discard"
    assert repeated["should_apply"] is False
    assert "repetition" in repeated["risk_flags"]

    action = _expected_json_after(
        prompt,
        "The digest quality evaluation still needs a short written recommendation after agreement and disagreement examples are reviewed.",
    )
    assert action["decision"] == "action_candidate"
    assert action["should_apply"] is False
    assert "possible_over_action" in action["risk_flags"]


def test_prompt_hardening_related_concern_ids_contract():
    prompt = _prompt_text()
    normalized = " ".join(prompt.split())

    assert "related_concern_ids contract:" in prompt
    assert "Always output related_concern_ids as an array for every decision" in prompt
    assert "memory_candidate, discard, and action_candidate" in prompt
    assert "Use only numeric concern ID values from active_or_dormant_concerns" in prompt
    assert "concern#1 must be output as 1" in prompt
    assert "Example: [1, 3]." in prompt
    assert (
        'Do not output "concern#1", concern titles, objects, string labels, "none", or "unknown".'
        in prompt
    )
    assert "If no directly related concern exists, output []" in prompt
    assert "If uncertain, output []" in prompt
    assert "Do not invent new concern IDs" in prompt
    assert '"related_concern_ids": []' in normalized


def test_evaluation_metrics_ac005_include_boundary_counts_and_risk_flags():
    from _evals.scripts.evaluate_llm_digest_proposals import _metrics

    rows = [
        {
            "schema_valid": True,
            "agreement": False,
            "fallback_used": False,
            "error_class": "",
            "proposed_decision": "memory_candidate",
            "final_decision": "concern_candidate",
            "confidence": 0.78,
            "risk_flags": ["stable_fact", "ambiguous_memory_vs_concern"],
            "model_should_apply": True,
            "should_apply": True,
            "should_apply_normalized": False,
            "normalization_reason": "blocked_risk_flag",
            "raw_response_persisted": False,
        },
        {
            "schema_valid": True,
            "agreement": False,
            "fallback_used": False,
            "error_class": "",
            "proposed_decision": "discard",
            "final_decision": "memory_candidate",
            "confidence": 0.72,
            "risk_flags": ["low_signal", "ambiguous_discard_vs_memory"],
            "model_should_apply": False,
            "should_apply": False,
            "should_apply_normalized": False,
            "normalization_reason": "confidence_below_threshold",
            "raw_response_persisted": False,
        },
        {
            "schema_valid": True,
            "agreement": True,
            "fallback_used": False,
            "error_class": "",
            "proposed_decision": "action_candidate",
            "final_decision": "action_candidate",
            "confidence": 0.62,
            "risk_flags": ["manual_follow_up", "possible_over_action"],
            "model_should_apply": False,
            "should_apply": False,
            "should_apply_normalized": False,
            "normalization_reason": "decision_not_auto_applicable",
            "raw_response_persisted": False,
        },
    ]

    metrics = _metrics(rows, {"observations": 3, "digest_decisions": 3, "proposals": 3})

    assert metrics["action_candidate_count"] == 1
    assert metrics["memory_vs_concern_disagreement_count"] == 1
    assert metrics["discard_vs_memory_disagreement_count"] == 1
    assert metrics["model_should_apply_true_count"] == 1
    assert metrics["normalized_should_apply_true_count"] == 0
    assert metrics["risk_flags_distribution"]["possible_over_action"] == 1


def test_default_digest_decider_is_deterministic_without_proposals(
    seeded_session, settings, monkeypatch
):
    def explode(*args, **kwargs):
        raise AssertionError("provider should not be constructed in deterministic mode")

    monkeypatch.setattr("app.cognition.digest_decider.create_llm_client", explode)

    result = run_wake_cycle(seeded_session, settings, reason="default-digest-test")

    assert result["observations"] >= 1
    assert seeded_session.scalar(select(func.count(DigestDecisionProposal.id))) == 0
    decisions = seeded_session.scalars(select(DigestDecisionTrace)).all()
    assert decisions
    assert all(
        json_loads(decision.metadata_json, {})["digest_decider"] == "deterministic"
        for decision in decisions
    )


def test_llm_shadow_persists_agreeing_proposal_but_final_remains_deterministic(
    seeded_session, settings, monkeypatch
):
    llm_settings = replace(
        settings,
        digest_decider="llm_shadow",
        llm_provider="mock",
        llm_model="mock-digest-model",
    )

    def fake_client(settings, transport=None, temperature=None, extra_payload=None):
        return TextJsonClient(_proposal_text(decision="concern_candidate"))

    monkeypatch.setattr("app.cognition.digest_decider.create_llm_client", fake_client)

    run_wake_cycle(seeded_session, llm_settings, reason="shadow-digest-test")

    proposal = seeded_session.scalar(select(DigestDecisionProposal).order_by(DigestDecisionProposal.id))
    decision = seeded_session.scalar(select(DigestDecisionTrace).order_by(DigestDecisionTrace.id))
    assert proposal is not None
    assert decision is not None
    metadata = json_loads(decision.metadata_json, {})
    assert proposal.proposed_decision == decision.decision == "concern_candidate"
    assert proposal.schema_valid is True
    assert proposal.raw_response_persisted is False
    assert metadata["proposal_id"] == proposal.id
    assert metadata["proposal_agreement"] is True
    assert proposal.final_digest_decision_id == decision.id
    assert proposal.deterministic_digest_decision_id == decision.id


def test_openrouter_shadow_uses_structured_output_payload(
    seeded_session, settings, monkeypatch
):
    monkeypatch.delenv("AGENT_OPENROUTER_REASONING_EFFORT", raising=False)
    monkeypatch.delenv("AGENT_OPENROUTER_REASONING_EXCLUDE", raising=False)
    captured_extra_payloads = []
    llm_settings = replace(
        settings,
        digest_decider="llm_shadow",
        llm_provider="openrouter",
        llm_model="qwen/qwen3.6-plus",
    )

    def fake_client(settings, transport=None, temperature=None, extra_payload=None):
        captured_extra_payloads.append(extra_payload)
        return TextJsonClient(_proposal_text(decision="concern_candidate"))

    monkeypatch.setattr("app.cognition.digest_decider.create_llm_client", fake_client)

    run_wake_cycle(seeded_session, llm_settings, reason="structured-output-test")

    payload = captured_extra_payloads[0]
    assert payload["response_format"]["type"] == "json_schema"
    assert payload["response_format"]["json_schema"]["name"] == "llm_digest_proposal"
    schema = payload["response_format"]["json_schema"]["schema"]
    assert schema["required"] == list(LLMDigestProposal.model_json_schema()["properties"].keys())
    assert schema["additionalProperties"] is False
    assert "default" not in json.dumps(schema)
    assert payload["structured_outputs"] is True
    assert payload["provider"] == {"require_parameters": True}
    assert "reasoning" not in payload


def test_openrouter_shadow_can_opt_into_reasoning_disable_for_evaluation(
    seeded_session, settings, monkeypatch
):
    captured_extra_payloads = []
    monkeypatch.setenv("AGENT_OPENROUTER_REASONING_EFFORT", "none")
    monkeypatch.setenv("AGENT_OPENROUTER_REASONING_EXCLUDE", "true")
    llm_settings = replace(
        settings,
        digest_decider="llm_shadow",
        llm_provider="openrouter",
        llm_model="deepseek/deepseek-v4-pro",
    )

    def fake_client(settings, transport=None, temperature=None, extra_payload=None):
        captured_extra_payloads.append(extra_payload)
        return TextJsonClient(_proposal_text(decision="concern_candidate"))

    monkeypatch.setattr("app.cognition.digest_decider.create_llm_client", fake_client)

    run_wake_cycle(seeded_session, llm_settings, reason="reasoning-disable-test")

    payload = captured_extra_payloads[0]
    assert payload["response_format"]["type"] == "json_schema"
    assert payload["structured_outputs"] is True
    assert payload["provider"] == {"require_parameters": True}
    assert payload["reasoning"] == {"effort": "none", "exclude": True}


def test_mock_shadow_keeps_prompt_only_fallback_payload(
    seeded_session, settings, monkeypatch
):
    captured_extra_payloads = []
    llm_settings = replace(settings, digest_decider="llm_shadow", llm_provider="mock")

    def fake_client(settings, transport=None, temperature=None, extra_payload=None):
        captured_extra_payloads.append(extra_payload)
        return TextJsonClient(_proposal_text(decision="concern_candidate"))

    monkeypatch.setattr("app.cognition.digest_decider.create_llm_client", fake_client)

    run_wake_cycle(seeded_session, llm_settings, reason="prompt-only-fallback-test")

    assert captured_extra_payloads
    assert all(payload is None for payload in captured_extra_payloads)


def test_should_apply_is_normalized_after_schema_validation(
    seeded_session, settings
):
    raw_event = _raw_event(
        seeded_session,
        "A stable project requirement says digest proposals remain advisory.",
    )
    observation = Observation(
        source_event_id=raw_event.id,
        source_probe_id=None,
        summary="A stable project requirement says digest proposals remain advisory.",
        salience=0.8,
        novelty=0.6,
        uncertainty=0.2,
        emotional_charge=0.0,
        self_relevance=0.7,
        possible_disposition="memory_candidate",
        rationale="manual test observation",
        confidence=0.9,
    )
    seeded_session.add(observation)
    seeded_session.flush()
    deterministic = digest_observation(observation)
    llm_settings = replace(settings, digest_decider="llm_shadow", llm_provider="mock")

    low_confidence = create_digest_proposal(
        seeded_session,
        observation,
        deterministic,
        llm_settings,
        TextJsonClient(
            _proposal_text(
                decision="memory_candidate",
                confidence=0.89,
                risk_flags=["stable_fact"],
                should_apply=True,
            )
        ),
    ).proposal

    assert low_confidence is not None
    assert low_confidence.schema_valid is True
    assert low_confidence.model_should_apply is True
    assert low_confidence.should_apply is False
    assert low_confidence.should_apply_normalized is False
    assert low_confidence.normalization_reason == "confidence_below_threshold"

    high_confidence = create_digest_proposal(
        seeded_session,
        observation,
        deterministic,
        llm_settings,
        TextJsonClient(
            _proposal_text(
                decision="memory_candidate",
                confidence=0.95,
                risk_flags=["stable_fact", "project_requirement"],
                should_apply=True,
            )
        ),
    ).proposal

    assert high_confidence is not None
    assert high_confidence.model_should_apply is True
    assert high_confidence.should_apply is True
    assert high_confidence.should_apply_normalized is True
    assert high_confidence.normalization_reason == "allowed_memory"


def test_llm_assisted_accepts_safe_agreeing_memory_confirm(seeded_session, settings):
    raw_event = _raw_event(
        seeded_session,
        "A stable project fact says digest proposal raw responses are not persisted.",
    )
    observation = Observation(
        source_event_id=raw_event.id,
        source_probe_id=None,
        summary="A stable project fact says digest proposal raw responses are not persisted.",
        salience=0.35,
        novelty=0.7,
        uncertainty=0.2,
        emotional_charge=0.0,
        self_relevance=0.4,
        possible_disposition="memory_candidate",
        rationale="manual test observation",
        confidence=0.9,
    )
    seeded_session.add(observation)
    seeded_session.flush()
    deterministic = DigestDecision(
        observation_id=observation.id,
        disposition="memory_candidate",
        reason="Deterministic memory route.",
    )
    llm_settings = replace(settings, digest_decider="llm_assisted", llm_provider="mock")

    result = create_digest_proposal(
        seeded_session,
        observation,
        deterministic,
        llm_settings,
        TextJsonClient(
            _proposal_text(
                decision="memory_candidate",
                confidence=0.95,
                risk_flags=["stable_fact"],
                should_apply=True,
            )
        ),
    )

    assert result.assisted_gate_result == "accepted"
    assert result.assisted_gate_reasons == ("accepted_memory_discard_confirm",)
    assert result.final_decision.disposition == "memory_candidate"
    assert result.final_decision.reason.startswith("LLM assisted confirm accepted")
    metadata = proposal_metadata(result, llm_settings)
    assert metadata["assisted_gate_result"] == "accepted"
    assert metadata["final_decision_source"] == "llm_assisted_confirm"
    assert metadata["deterministic_decision"] == "memory_candidate"
    assert metadata["final_decision"] == "memory_candidate"


def test_llm_assisted_rejects_disagreement_and_action_candidates(
    seeded_session, settings
):
    raw_event = _raw_event(seeded_session, "A durable fact should be kept as memory.")
    observation = Observation(
        source_event_id=raw_event.id,
        source_probe_id=None,
        summary="A durable fact should be kept as memory.",
        salience=0.35,
        novelty=0.7,
        uncertainty=0.2,
        emotional_charge=0.0,
        self_relevance=0.4,
        possible_disposition="memory_candidate",
        rationale="manual test observation",
        confidence=0.9,
    )
    seeded_session.add(observation)
    seeded_session.flush()
    deterministic = DigestDecision(
        observation_id=observation.id,
        disposition="memory_candidate",
        reason="Deterministic memory route.",
    )
    llm_settings = replace(settings, digest_decider="llm_assisted", llm_provider="mock")

    disagree = create_digest_proposal(
        seeded_session,
        observation,
        deterministic,
        llm_settings,
        TextJsonClient(
            _proposal_text(
                decision="discard",
                confidence=0.95,
                risk_flags=["low_signal"],
                should_apply=True,
            )
        ),
    )
    assert disagree.assisted_gate_result == "rejected"
    assert "deterministic_disagreement" in disagree.assisted_gate_reasons
    assert disagree.final_decision == deterministic

    action = create_digest_proposal(
        seeded_session,
        observation,
        deterministic,
        llm_settings,
        TextJsonClient(
            _proposal_text(
                decision="action_candidate",
                confidence=0.95,
                risk_flags=[],
                should_apply=True,
            )
        ),
    )
    assert action.assisted_gate_result == "rejected"
    assert "decision_not_assisted_confirmable" in action.assisted_gate_reasons
    assert "normalized_should_apply_false" in action.assisted_gate_reasons
    assert action.final_decision == deterministic


def test_llm_shadow_records_disagreement_and_downstream_uses_final_decision(
    seeded_session, settings, monkeypatch
):
    llm_settings = replace(settings, digest_decider="llm_shadow", llm_provider="mock")
    core_profiles_before = seeded_session.scalar(select(func.count(CoreProfile.id)))
    concerns_before = seeded_session.scalar(select(func.count(Concern.id)))

    def fake_client(settings, transport=None, temperature=None, extra_payload=None):
        return TextJsonClient(
            _proposal_text(
                decision="discard",
                reason="The proposal would discard this, but it is only a shadow.",
            )
        )

    monkeypatch.setattr("app.cognition.digest_decider.create_llm_client", fake_client)

    run_wake_cycle(seeded_session, llm_settings, reason="shadow-disagree-test")

    proposal = seeded_session.scalar(select(DigestDecisionProposal).order_by(DigestDecisionProposal.id))
    decision = seeded_session.scalar(select(DigestDecisionTrace).order_by(DigestDecisionTrace.id))
    metadata = json_loads(decision.metadata_json, {})
    assert proposal.proposed_decision == "discard"
    assert decision.decision == "concern_candidate"
    assert metadata["proposal_agreement"] is False
    assert seeded_session.scalar(select(func.count(Concern.id))) > concerns_before
    assert seeded_session.scalar(select(func.count(Memory.id))) >= 1
    assert seeded_session.scalar(select(func.count(CoreProfile.id))) == core_profiles_before


def test_invalid_json_creates_rejected_proposal_and_final_deterministic_decision(
    seeded_session, settings, monkeypatch
):
    llm_settings = replace(settings, digest_decider="llm_shadow", llm_provider="mock")

    def fake_client(settings, transport=None, temperature=None, extra_payload=None):
        return TextJsonClient("{not valid json")

    monkeypatch.setattr("app.cognition.digest_decider.create_llm_client", fake_client)

    run_wake_cycle(seeded_session, llm_settings, reason="invalid-json-test")

    proposal = seeded_session.scalar(select(DigestDecisionProposal).order_by(DigestDecisionProposal.id))
    decision = seeded_session.scalar(select(DigestDecisionTrace).order_by(DigestDecisionTrace.id))
    metadata = json_loads(decision.metadata_json, {})
    assert proposal.schema_valid is False
    assert proposal.fallback_used is True
    assert proposal.error_class == "JSONDecodeError"
    assert proposal.raw_response_persisted is False
    assert decision.decision == "concern_candidate"
    assert metadata["proposal_fallback"] is True


def test_structured_output_still_uses_pydantic_as_final_gate(
    seeded_session, settings, monkeypatch
):
    llm_settings = replace(
        settings,
        digest_decider="llm_shadow",
        llm_provider="openrouter",
        llm_model="qwen/qwen3.6-plus",
    )

    def fake_client(settings, transport=None, temperature=None, extra_payload=None):
        return TextJsonClient(_proposal_text(decision="mutate_core_profile"))

    monkeypatch.setattr("app.cognition.digest_decider.create_llm_client", fake_client)

    run_wake_cycle(seeded_session, llm_settings, reason="structured-final-gate-test")

    proposal = seeded_session.scalar(select(DigestDecisionProposal).order_by(DigestDecisionProposal.id))
    decision = seeded_session.scalar(select(DigestDecisionTrace).order_by(DigestDecisionTrace.id))
    assert proposal.schema_valid is False
    assert proposal.fallback_used is True
    assert proposal.error_class == "ValidationError"
    assert "decision:literal_error" in proposal.error_message_sanitized
    assert proposal.raw_response_persisted is False
    assert decision.decision == "concern_candidate"


def test_schema_invalid_provider_error_unknown_concern_and_secret_are_safe(
    seeded_session, settings, monkeypatch
):
    raw_event = _raw_event(
        seeded_session,
        "Agent risk trace needs careful observation and should remain unresolved.",
    )
    observation = Observation(
        source_event_id=raw_event.id,
        source_probe_id=None,
        summary="Agent risk trace needs careful observation.",
        salience=0.9,
        novelty=0.6,
        uncertainty=0.8,
        emotional_charge=0.2,
        self_relevance=0.8,
        possible_disposition="concern_candidate",
        rationale="manual test observation",
        confidence=0.9,
    )
    seeded_session.add(observation)
    seeded_session.flush()
    deterministic = digest_observation(observation)
    llm_settings = replace(settings, digest_decider="llm_shadow", llm_provider="mock")

    schema_bad = create_digest_proposal(
        seeded_session,
        observation,
        deterministic,
        llm_settings,
        TextJsonClient(_proposal_text(decision="mutate_core_profile")),
    ).proposal
    assert schema_bad is not None
    assert schema_bad.schema_valid is False
    assert schema_bad.fallback_used is True

    provider_bad = create_digest_proposal(
        seeded_session,
        observation,
        deterministic,
        llm_settings,
        FailingTextClient(),
    ).proposal
    assert provider_bad is not None
    assert provider_bad.error_class == "LLMProviderError"
    assert "sk-secret-value" not in (
        provider_bad.error_message_sanitized + provider_bad.reason
    )

    unknown = create_digest_proposal(
        seeded_session,
        observation,
        deterministic,
        llm_settings,
        TextJsonClient(_proposal_text(related_concern_ids=[999999])),
    ).proposal
    assert unknown is not None
    assert json_loads(unknown.related_concern_ids_json, []) == []

    unsafe = create_digest_proposal(
        seeded_session,
        observation,
        deterministic,
        llm_settings,
        TextJsonClient(_proposal_text(reason="use token sk-secret-value here")),
    ).proposal
    assert unsafe is not None
    serialized = (
        unsafe.reason
        + unsafe.evidence_summary
        + unsafe.evidence_quote_short
        + unsafe.error_message_sanitized
    )
    assert unsafe.schema_valid is False
    assert unsafe.fallback_used is True
    assert "sk-secret-value" not in serialized
