"""Wake cycle integration."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.local_files import execute_local_probe
from app.adapters.web_search import WebSearchAdapter, WebSearchQuery
from app.cognition.action_planner import plan_wake_actions
from app.cognition.attention_policy import (
    update_policy_from_observations,
    update_policy_from_outcomes,
)
from app.cognition.concern_manager import upsert_concern_from_observation
from app.cognition.digest_decider import create_digest_proposal, proposal_metadata
from app.cognition.digestor import digest_observation, persist_digest_decision
from app.cognition.memory_manager import create_memory_from_observation
from app.cognition.observation_extractor import extract_observation, persist_observation
from app.cognition.probe_planner import persist_probe, plan_probes
from app.config import Settings
from app.db.json_utils import json_dict, json_dumps
from app.db.models import Concern, Memory, Observation
from app.runtime.events import persist_raw_event
from app.schemas import RawEventInput


def _execute_memory_probe(session: Session, probe_id: int) -> list[RawEventInput]:
    memories = session.scalars(
        select(Memory).order_by(Memory.updated_at.desc()).limit(5)
    ).all()
    return [
        RawEventInput(
            source_type="memory",
            event_type="memory_revisit",
            payload={"memory_id": memory.id, "source_probe_id": probe_id},
            content_text=memory.content,
        )
        for memory in memories
    ]


def _execute_concern_probe(session: Session, probe_id: int) -> list[RawEventInput]:
    concerns = session.scalars(
        select(Concern)
        .where(Concern.state.in_(["seed", "active", "dormant"]))
        .order_by(Concern.activation_score.desc(), Concern.updated_at.desc())
        .limit(5)
    ).all()
    return [
        RawEventInput(
            source_type="concern",
            event_type="concern_revisit",
            payload={"concern_id": concern.id, "source_probe_id": probe_id},
            content_text=(
                f"{concern.title}\nstate={concern.state}\n"
                f"closure_hypothesis={concern.closure_hypothesis}"
            ),
        )
        for concern in concerns
    ]


def _execute_probe(session: Session, probe, settings: Settings) -> list[RawEventInput]:
    if (
        probe.source_type == "local_file"
        or probe.source_type == "random_environment_sample"
    ):
        return execute_local_probe(probe, settings)
    if probe.source_type == "web_search":
        return WebSearchAdapter().search(
            [
                WebSearchQuery(
                    query=probe.query_or_path,
                    rationale=probe.rationale,
                )
            ],
            settings,
        )
    if probe.source_type == "memory":
        return _execute_memory_probe(session, probe.id)
    if probe.source_type == "concern":
        return _execute_concern_probe(session, probe.id)
    return []


def run_wake_cycle(
    session: Session, settings: Settings, reason: str = "manual"
) -> dict[str, int]:
    plans = plan_probes(session, settings, trigger_type=reason)
    probes = [persist_probe(session, plan) for plan in plans]
    session.flush()

    raw_count = 0
    observations: list[Observation] = []
    concerns: list[Concern] = []
    memory_count = 0

    for probe in probes:
        probe.status = "running"
        raw_inputs = _execute_probe(session, probe, settings)
        raw_count += len(raw_inputs)
        budget = json_dict(probe.budget_json)
        probe.budget_used_json = json_dumps(
            {
                "raw_events": len(raw_inputs),
                "source_type": probe.source_type,
                "policy_selection": budget.get("policy_selection", {}),
                "skipped_sources": budget.get("policy_selection", {}).get(
                    "skipped_sources", []
                ),
            }
        )
        for raw_input in raw_inputs:
            raw_event = persist_raw_event(session, raw_input)
            extraction = extract_observation(
                raw_event, source_probe_id=probe.id, settings=settings
            )
            for proposal_index, draft in enumerate(extraction.drafts):
                observation = persist_observation(session, draft)
                observations.append(observation)
                decision = digest_observation(observation)
                proposal_result = create_digest_proposal(
                    session, observation, decision, settings
                )
                final_decision = proposal_result.final_decision
                related_concern_ids: list[int] = []
                if final_decision.disposition == "concern_candidate":
                    concern = upsert_concern_from_observation(session, observation)
                    related_concern_ids = [concern.id]
                    concerns.append(concern)
                    create_memory_from_observation(session, observation, [concern.id])
                    memory_count += 1
                elif final_decision.disposition == "memory_candidate":
                    create_memory_from_observation(session, observation, [])
                    memory_count += 1
                trace = persist_digest_decision(
                    session,
                    observation,
                    final_decision,
                    run_id=reason,
                    related_concern_ids=related_concern_ids,
                    metadata={
                        "probe_id": probe.id,
                        "probe_source_type": probe.source_type,
                        "proposal_index": proposal_index,
                        **proposal_metadata(proposal_result, settings),
                        **extraction.metadata,
                    },
                )
                if proposal_result.proposal is not None:
                    proposal_result.proposal.deterministic_digest_decision_id = trace.id
                    proposal_result.proposal.final_digest_decision_id = trace.id
        probe.status = "completed"
        probe.result_summary = (
            f"Read {len(raw_inputs)} raw events and produced "
            f"{len(observations)} total observations so far."
        )

    latest_policy = update_policy_from_observations(
        session, observations, probes[0].source_type if probes else "local_file"
    )
    actions, outcomes, wake_request = plan_wake_actions(
        session,
        settings,
        concerns,
        [probe.id for probe in probes],
        observation_count=len(observations),
    )
    latest_policy = update_policy_from_outcomes(session, outcomes)
    session.flush()
    return {
        "probes": len(probes),
        "raw_events": raw_count,
        "observations": len(observations),
        "concerns": len({concern.id for concern in concerns}),
        "memories": memory_count,
        "actions": len(actions),
        "outcomes": len(outcomes),
        "attention_policy_version": latest_policy.version,
        "wake_requests": 1 if wake_request else 0,
    }
