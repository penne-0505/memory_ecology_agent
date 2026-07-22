"""Run an evidence-focused Memory Ecology Agent PoC verification.

This script is intentionally outside product runtime. It builds an isolated
project root, copies the chaotic sample world fixture, runs the existing cycles,
and writes a JSON evidence bundle for the human verification report.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adapters.llm import MockLLMClient, StateSensitiveFakeLLMClient
from app.adapters.web_search import WebSearchAdapter, WebSearchQuery
from app.cognition.attention_policy import update_policy_from_observations
from app.cognition.concern_manager import (
    review_concern_lifecycle,
    upsert_concern_from_observation,
)
from app.cognition.digestor import digest_observation, persist_digest_decision
from app.cognition.observation_extractor import draft_observation, persist_observation
from app.cognition.probe_planner import plan_probes
from app.config import Settings
from app.db.init_db import init_database, seed_initial_data
from app.db.json_utils import json_dumps, json_loads
from app.db.models import (
    Action,
    AttentionPolicy,
    AttentionPolicyEvent,
    Concern,
    ConcernEvent,
    CoreChangeProposal,
    CoreProfile,
    DigestDecisionTrace,
    EvalPrompt,
    InputProbe,
    Memory,
    Observation,
    Outcome,
    RawEvent,
    ReplayRun,
    ResponseTrace,
    SelfModelSnapshot,
    WakeRequest,
)
from app.db.session import session_scope
from app.eval.replay import run_replay_eval
from app.runtime.chat_cycle import run_chat_cycle
from app.runtime.events import persist_raw_event
from app.runtime.reflection_cycle import run_reflection_cycle
from app.runtime.review_cycle import run_review_cycle
from app.runtime.wake_cycle import run_wake_cycle
from app.schemas import RawEventInput


FIXTURE_WORLD = REPO_ROOT / "_evals" / "fixtures" / "memory_ecology_sample_world" / "world"
DEFAULT_OUTPUT = (
    REPO_ROOT / "_evals" / "reports" / "memory_ecology_verification_2026-05-30.json"
)


def _count(session: Session, model: type[Any]) -> int:
    return int(session.scalar(select(func.count(model.id))) or 0)


def _json(value: str | None, default: Any) -> Any:
    return json_loads(value, default)


def _latest_policy(session: Session) -> AttentionPolicy | None:
    return session.scalar(
        select(AttentionPolicy).order_by(AttentionPolicy.version.desc()).limit(1)
    )


def _sample_probes(session: Session) -> list[dict[str, Any]]:
    probes = session.scalars(select(InputProbe).order_by(InputProbe.id)).all()
    return [
        {
            "id": probe.id,
            "source_type": probe.source_type,
            "query_or_path": probe.query_or_path,
            "rationale": probe.rationale,
            "expected_gain": probe.expected_gain,
            "exploration_mode": probe.exploration_mode,
            "related_concern_ids": _json(probe.related_concern_ids_json, []),
            "budget": _json(probe.budget_json, {}),
            "budget_used": _json(probe.budget_used_json, {}),
            "status": probe.status,
            "result_summary": probe.result_summary,
        }
        for probe in probes
    ]


def _sample_observations(session: Session, limit: int = 12) -> list[dict[str, Any]]:
    observations = session.scalars(select(Observation).order_by(Observation.id).limit(limit)).all()
    return [
        {
            "id": obs.id,
            "source_probe_id": obs.source_probe_id,
            "possible_disposition": obs.possible_disposition,
            "salience": obs.salience,
            "uncertainty": obs.uncertainty,
            "self_relevance": obs.self_relevance,
            "rationale": obs.rationale,
            "summary": obs.summary,
        }
        for obs in observations
    ]


def _sample_concerns(session: Session) -> list[dict[str, Any]]:
    concerns = session.scalars(
        select(Concern).order_by(Concern.activation_score.desc(), Concern.id)
    ).all()
    return [
        {
            "id": concern.id,
            "title": concern.title,
            "state": concern.state,
            "activation_score": concern.activation_score,
            "unresolvedness": concern.unresolvedness,
            "recurrence_score": concern.recurrence_score,
            "attempt_pressure": concern.attempt_pressure,
            "source_observation_ids": _json(concern.source_observation_ids_json, []),
            "successor_concern_id": concern.successor_concern_id,
            "closed_by": concern.closed_by,
        }
        for concern in concerns
    ]


def _sample_concern_events(session: Session, limit: int = 20) -> list[dict[str, Any]]:
    events = session.scalars(select(ConcernEvent).order_by(ConcernEvent.id).limit(limit)).all()
    return [
        {
            "id": event.id,
            "concern_id": event.concern_id,
            "event_type": event.event_type,
            "reason": event.reason,
            "delta": _json(event.delta_json, {}),
            "source_action_id": event.source_action_id,
        }
        for event in events
    ]


def _sample_attention_events(session: Session) -> list[dict[str, Any]]:
    events = session.scalars(select(AttentionPolicyEvent).order_by(AttentionPolicyEvent.id)).all()
    return [
        {
            "id": event.id,
            "attention_policy_id": event.attention_policy_id,
            "event_type": event.event_type,
            "target_field": event.target_field,
            "delta": _json(event.delta_json, {}),
            "reason": event.reason,
            "evidence_observation_ids": _json(event.evidence_observation_ids_json, []),
            "evidence_action_ids": _json(event.evidence_action_ids_json, []),
            "evidence_outcome_ids": _json(event.evidence_outcome_ids_json, []),
            "confidence": event.confidence,
        }
        for event in events
    ]


def _sample_digest_decisions(session: Session) -> list[dict[str, Any]]:
    decisions = session.scalars(select(DigestDecisionTrace).order_by(DigestDecisionTrace.id)).all()
    return [
        {
            "id": decision.id,
            "run_id": decision.run_id,
            "source_observation_id": decision.source_observation_id,
            "source_raw_event_id": decision.source_raw_event_id,
            "decision": decision.decision,
            "reason": decision.reason,
            "confidence": decision.confidence,
            "snapshots": {
                "salience": decision.salience_snapshot,
                "novelty": decision.novelty_snapshot,
                "uncertainty": decision.uncertainty_snapshot,
                "self_relevance": decision.self_relevance_snapshot,
            },
            "related_concern_ids": _json(decision.related_concern_ids_json, []),
            "metadata": _json(decision.metadata_json, {}),
        }
        for decision in decisions
    ]


def _sample_actions_outcomes(session: Session) -> dict[str, list[dict[str, Any]]]:
    actions = session.scalars(select(Action).order_by(Action.id)).all()
    outcomes = session.scalars(select(Outcome).order_by(Outcome.id)).all()
    return {
        "actions": [
            {
                "id": action.id,
                "action_type": action.action_type,
                "rationale": action.rationale,
                "related_concern_ids": _json(action.related_concern_ids_json, []),
                "input_probe_ids": _json(action.input_probe_ids_json, []),
                "external_effect": action.external_effect,
                "status": action.status,
                "payload": _json(action.payload_json, {}),
            }
            for action in actions
        ],
        "outcomes": [
            {
                "id": outcome.id,
                "action_id": outcome.action_id,
                "observed_result": outcome.observed_result,
                "user_feedback": outcome.user_feedback,
                "effect_on_concerns": _json(outcome.effect_on_concerns_json, {}),
                "effect_on_attention_policy": _json(
                    outcome.effect_on_attention_policy_json, {}
                ),
            }
            for outcome in outcomes
        ],
    }


def _sample_response_traces(session: Session) -> list[dict[str, Any]]:
    traces = session.scalars(select(ResponseTrace).order_by(ResponseTrace.id)).all()
    return [
        {
            "id": trace.id,
            "response_action_id": trace.response_action_id,
            "selected_memory_ids": _json(trace.selected_memory_ids_json, []),
            "selected_concerns": _json(trace.selected_concerns_json, []),
            "selected_attention_policy": _json(trace.selected_attention_policy_json, {}),
            "concern_modes": _json(trace.concern_modes_json, {}),
            "prompt_summary": trace.prompt_summary,
        }
        for trace in traces
    ]


def _policy_snapshot(policy: AttentionPolicy | None) -> dict[str, Any]:
    if policy is None:
        return {}
    return {
        "id": policy.id,
        "version": policy.version,
        "source_preferences": _json(policy.source_preferences_json, {}),
        "salience_preferences": _json(policy.salience_preferences_json, {}),
        "concern_type_preferences": _json(policy.concern_type_preferences_json, {}),
        "action_preferences": _json(policy.action_preferences_json, {}),
        "response_preferences": _json(policy.response_preferences_json, {}),
        "exploration_randomness": policy.exploration_randomness,
        "stability": policy.stability,
    }


def _replay_comparison(
    before_runs: list[ReplayRun], after_runs: list[ReplayRun]
) -> list[dict[str, Any]]:
    before_by_prompt = {run.eval_prompt_id: run for run in before_runs}
    after_by_prompt = {run.eval_prompt_id: run for run in after_runs}
    rows: list[dict[str, Any]] = []
    for prompt_id in sorted(before_by_prompt):
        before = before_by_prompt[prompt_id]
        after = after_by_prompt[prompt_id]
        before_state = {
            "concerns": _json(before.selected_concerns_json, []),
            "memories": _json(before.selected_memories_json, []),
            "policy": _json(before.selected_attention_policy_json, {}),
        }
        after_state = {
            "concerns": _json(after.selected_concerns_json, []),
            "memories": _json(after.selected_memories_json, []),
            "policy": _json(after.selected_attention_policy_json, {}),
        }
        rows.append(
            {
                "prompt_id": prompt_id,
                "before_run_id": before.id,
                "after_run_id": after.id,
                "response_changed": before.response_text != after.response_text,
                "state_changed": before_state != after_state,
                "before_response": before.response_text,
                "after_response": after.response_text,
                "before_state": before_state,
                "after_state": after_state,
            }
        )
    return rows


def _apply_natural_lifecycle_probe(session: Session) -> dict[str, Any]:
    first_raw = persist_raw_event(
        session,
        RawEventInput(
            source_type="verification",
            event_type="lifecycle_seed",
            payload={"scope": "verification"},
            content_text="Lifecycle digest risk remains unresolved for implementation trace review.",
        ),
    )
    first_obs = persist_observation(session, draft_observation(first_raw, None))
    concern = upsert_concern_from_observation(session, first_obs)
    second_raw = persist_raw_event(
        session,
        RawEventInput(
            source_type="verification",
            event_type="lifecycle_reinforce",
            payload={"scope": "verification"},
            content_text="Lifecycle digest risk remains unresolved for implementation evidence review.",
        ),
    )
    second_obs = persist_observation(session, draft_observation(second_raw, None))
    concern = upsert_concern_from_observation(session, second_obs)
    concern.activation_score = 0.2
    concern.unresolvedness = 0.1
    concern.attempt_pressure = 0.1
    dormant_result = review_concern_lifecycle(session)

    third_raw = persist_raw_event(
        session,
        RawEventInput(
            source_type="verification",
            event_type="lifecycle_reactivate",
            payload={"scope": "verification"},
            content_text="Lifecycle digest risk remains unresolved for implementation transition review.",
        ),
    )
    third_obs = persist_observation(session, draft_observation(third_raw, None))
    concern = upsert_concern_from_observation(session, third_obs)

    action = Action(
        action_type="natural_lifecycle_resolution",
        rationale="Verification action supplies normal outcome evidence for lifecycle closure.",
        related_concern_ids_json=json_dumps([concern.id]),
        input_probe_ids_json=json_dumps([]),
        payload_json=json_dumps({"scope": "verification"}),
        external_effect="none",
        status="completed",
    )
    session.add(action)
    session.flush()
    outcome = Outcome(
        action_id=action.id,
        observed_result="Concern resolved by deterministic verification outcome.",
        effect_on_concerns_json=json_dumps(
            {"resolved": [concern.id], "closure_mode": "completed"}
        ),
        effect_on_attention_policy_json=json_dumps({}),
    )
    session.add(outcome)
    session.flush()
    resolved_result = review_concern_lifecycle(session)
    archived_result = review_concern_lifecycle(session)

    successor_action = Action(
        action_type="natural_lifecycle_successor",
        rationale="Verification action transforms a concern into a successor.",
        related_concern_ids_json=json_dumps([concern.id]),
        input_probe_ids_json=json_dumps([]),
        payload_json=json_dumps({"scope": "verification"}),
        external_effect="none",
        status="completed",
    )
    session.add(successor_action)
    session.flush()
    successor_seed = upsert_concern_from_observation(
        session,
        persist_observation(
            session,
            draft_observation(
                persist_raw_event(
                    session,
                    RawEventInput(
                        source_type="verification",
                        event_type="successor_seed",
                        payload={"scope": "verification"},
                        content_text="Successor lifecycle risk remains unresolved for digest transition.",
                    ),
                ),
                None,
            ),
        ),
    )
    successor_outcome = Outcome(
        action_id=successor_action.id,
        observed_result="Concern transformed into successor concern.",
        effect_on_concerns_json=json_dumps(
            {
                "successor": {
                    "concern_id": successor_seed.id,
                    "title": "Successor concern for lifecycle evidence",
                    "closure_mode": "transformed",
                }
            }
        ),
        effect_on_attention_policy_json=json_dumps({}),
    )
    session.add(successor_outcome)
    session.flush()
    successor_result = review_concern_lifecycle(session)
    return {
        "concern_id": concern.id,
        "dormant_result": dormant_result,
        "resolved_result": resolved_result,
        "archived_result": archived_result,
        "successor_result": successor_result,
    }


def run_verification(output: Path) -> dict[str, Any]:
    temp_root = Path(tempfile.mkdtemp(prefix="memory-ecology-verify-"))
    shutil.copytree(FIXTURE_WORLD, temp_root / "world", dirs_exist_ok=True)
    settings = Settings(
        project_root=temp_root,
        db_path=temp_root / "data" / "agent.db",
        world_root=temp_root / "world",
        workspace_root=temp_root / "agent_workspace",
        max_probe_files=20,
        max_probe_chars=50_000,
        llm_provider="mock",
    )
    init_database(settings)

    with session_scope(settings) as session:
        seed_counts = seed_initial_data(session, settings)
        core_before = session.scalar(select(CoreProfile).order_by(CoreProfile.id).limit(1))
        initial_policy = _policy_snapshot(_latest_policy(session))
        before_runs = run_replay_eval(session, llm=StateSensitiveFakeLLMClient())

        wake_results: list[dict[str, Any]] = []
        concern_counts_after_wake: list[int] = []
        for index in range(3):
            result = run_wake_cycle(
                session, settings, reason=f"verification_wake_{index + 1}"
            )
            wake_results.append(result)
            concern_counts_after_wake.append(_count(session, Concern))

        policy_after_wakes = _policy_snapshot(_latest_policy(session))
        review_result = run_review_cycle(session)
        reflection_result = run_reflection_cycle(session)
        self_model_count_after_reflect = _count(session, SelfModelSnapshot)
        core_after_reflect = session.scalar(select(CoreProfile).order_by(CoreProfile.id).limit(1))

        chat_results = [
            run_chat_cycle(
                session,
                "このPoCは今すぐ実装を広げてよいと思うか？",
                llm=MockLLMClient(),
            ),
            run_chat_cycle(
                session,
                "ユーザーの指摘と内部concernが衝突したらどう扱うべき？",
                llm=MockLLMClient(),
            ),
        ]

        response_actions = session.scalars(
            select(Action).where(Action.action_type == "respond").order_by(Action.id)
        ).all()
        feedback_outcome_id = None
        if response_actions:
            outcome = Outcome(
                action_id=response_actions[-1].id,
                observed_result="Verification fixture captured corrective user feedback after chat.",
                user_feedback="User asks for trace evidence and rejects thin assertion.",
                effect_on_concerns_json=json_dumps(
                    {"feedback": "response_trace_requires_evidence"}
                ),
                effect_on_attention_policy_json=json_dumps(
                    {"manual_fixture_only": "response preference feedback captured"}
                ),
            )
            session.add(outcome)
            session.flush()
            feedback_outcome_id = outcome.id

        after_runs = run_replay_eval(session, llm=StateSensitiveFakeLLMClient())
        replay_comparison = _replay_comparison(before_runs, after_runs)

        policy_before_web_noise = _policy_snapshot(_latest_policy(session))
        web_inputs = WebSearchAdapter().search(
            [
                WebSearchQuery(
                    query="cafe menu weather trivia",
                    rationale="verification noise check",
                )
            ],
            settings,
        )
        web_decisions: list[dict[str, Any]] = []
        web_observations: list[Observation] = []
        for raw_input in web_inputs:
            raw_event = persist_raw_event(session, raw_input)
            observation = persist_observation(
                session, draft_observation(raw_event, source_probe_id=None)
            )
            web_observations.append(observation)
            decision = digest_observation(observation)
            persist_digest_decision(
                session,
                observation,
                decision,
                run_id="verification_web_noise",
                metadata={"source": "web_noise"},
            )
            web_decisions.append(
                {
                    "observation_id": observation.id,
                    "disposition": decision.disposition,
                    "reason": decision.reason,
                }
            )
        policy_after_web_noise = update_policy_from_observations(
            session, web_observations, "web_search"
        )
        next_probe_plans = [
            plan.model_dump()
            for plan in plan_probes(session, settings, trigger_type="post_web_noise")
        ]

        discard_raw_event = persist_raw_event(
            session,
            RawEventInput(
                source_type="conversation",
                event_type="verification_low_signal_noise",
                payload={"scope": "verification_fixture"},
                content_text="blue chair receipt window",
            ),
        )
        discard_observation = persist_observation(
            session, draft_observation(discard_raw_event, source_probe_id=None)
        )
        discard_decision = digest_observation(discard_observation)
        persist_digest_decision(
            session,
            discard_observation,
            discard_decision,
            run_id="verification_low_signal",
            metadata={"source": "low_signal_fixture"},
        )

        natural_lifecycle = _apply_natural_lifecycle_probe(session)
        core_after_all = session.scalar(select(CoreProfile).order_by(CoreProfile.id).limit(1))

        prompts = session.scalars(select(EvalPrompt).order_by(EvalPrompt.id)).all()
        report = {
            "project_root": str(settings.project_root),
            "db_path": str(settings.db_path),
            "fixture_world": str(FIXTURE_WORLD),
            "seed_counts": seed_counts,
            "eval_prompts": [
                {
                    "id": prompt.id,
                    "title": prompt.title,
                    "prompt": prompt.prompt,
                    "expected_dimension": prompt.expected_dimension,
                }
                for prompt in prompts
            ],
            "table_counts": {
                "raw_events": _count(session, RawEvent),
                "input_probes": _count(session, InputProbe),
                "observations": _count(session, Observation),
                "concerns": _count(session, Concern),
                "concern_events": _count(session, ConcernEvent),
                "memories": _count(session, Memory),
                "actions": _count(session, Action),
                "outcomes": _count(session, Outcome),
                "attention_policies": _count(session, AttentionPolicy),
                "attention_policy_events": _count(session, AttentionPolicyEvent),
                "core_profiles": _count(session, CoreProfile),
                "core_change_proposals": _count(session, CoreChangeProposal),
                "digest_decisions": _count(session, DigestDecisionTrace),
                "self_model_snapshots": _count(session, SelfModelSnapshot),
                "wake_requests": _count(session, WakeRequest),
                "response_traces": _count(session, ResponseTrace),
                "eval_prompts": _count(session, EvalPrompt),
                "replay_runs": _count(session, ReplayRun),
            },
            "wake_results": wake_results,
            "concern_counts_after_wake": concern_counts_after_wake,
            "initial_policy": initial_policy,
            "policy_after_wakes": policy_after_wakes,
            "policy_before_web_noise": policy_before_web_noise,
            "policy_after_web_noise": _policy_snapshot(policy_after_web_noise),
            "review_result": review_result,
            "reflection_result": reflection_result,
            "self_model_count_after_reflect": self_model_count_after_reflect,
            "core_profile_stability": {
                "before_id": core_before.id if core_before else None,
                "after_reflect_id": core_after_reflect.id if core_after_reflect else None,
                "after_all_id": core_after_all.id if core_after_all else None,
                "content_unchanged_after_reflect": (
                    bool(core_before and core_after_reflect)
                    and core_before.content == core_after_reflect.content
                ),
                "content_unchanged_after_all": (
                    bool(core_before and core_after_all)
                    and core_before.content == core_after_all.content
                ),
                "locked": core_after_all.locked if core_after_all else None,
            },
            "core_change_proposals": [
                {
                    "id": proposal.id,
                    "proposed_change": proposal.proposed_change,
                    "reason": proposal.reason,
                    "risk": proposal.risk,
                    "status": proposal.status,
                }
                for proposal in session.scalars(
                    select(CoreChangeProposal).order_by(CoreChangeProposal.id)
                ).all()
            ],
            "input_probes": _sample_probes(session),
            "observations_sample": _sample_observations(session),
            "observation_dispositions": {
                disposition: int(count)
                for disposition, count in session.execute(
                    select(Observation.possible_disposition, func.count(Observation.id))
                    .group_by(Observation.possible_disposition)
                    .order_by(Observation.possible_disposition)
                ).all()
            },
            "web_noise_digest_decisions": web_decisions,
            "low_signal_digest_decision": {
                "observation_id": discard_observation.id,
                "observation_possible_disposition": discard_observation.possible_disposition,
                "digest_disposition": discard_decision.disposition,
                "digest_reason": discard_decision.reason,
                "persisted_digest_reason": True,
            },
            "digest_decisions": _sample_digest_decisions(session),
            "concerns": _sample_concerns(session),
            "concern_events": _sample_concern_events(session),
            "attention_policy_events": _sample_attention_events(session),
            "actions_outcomes": _sample_actions_outcomes(session),
            "wake_requests": [
                {
                    "id": request.id,
                    "requested_by_action_id": request.requested_by_action_id,
                    "urgency": request.urgency,
                    "reason": request.reason,
                    "accepted_by_scheduler": request.accepted_by_scheduler,
                    "scheduler_decision_reason": request.scheduler_decision_reason,
                }
                for request in session.scalars(
                    select(WakeRequest).order_by(WakeRequest.id)
                ).all()
            ],
            "chat_results": chat_results,
            "feedback_outcome_id": feedback_outcome_id,
            "response_traces": _sample_response_traces(session),
            "replay_comparison": replay_comparison,
            "next_probe_plans_after_web_noise": next_probe_plans,
            "natural_lifecycle_probe": natural_lifecycle,
        }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = run_verification(args.output.resolve())
    print(json.dumps({"output": str(args.output.resolve()), **report}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
