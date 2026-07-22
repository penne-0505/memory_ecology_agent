"""Argparse CLI commands."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.config import Settings
from app.adapters.discord_bot import run_discord_bot
from app.adapters.discord_config import diagnose_discord_settings
from app.db.init_db import init_database, seed_initial_data
from app.db.json_utils import json_loads
from app.db.models import (
    Action,
    AttentionPolicy,
    AttentionPolicyEvent,
    Concern,
    DigestDecisionProposal,
    DigestDecisionTrace,
    InputProbe,
    Observation,
    Outcome,
    ResponseTrace,
    WakeRequest,
)
from app.db.session import session_scope
from app.eval.replay import compare_replay_runs, run_replay_eval
from app.runtime.chat_cycle import run_chat_cycle
from app.runtime.discord_controller import DiscordCommandContext, DiscordController
from app.runtime.llm_smoke import run_llm_provider_smoke
from app.runtime.modes import DiscordRuntimeMode
from app.runtime.reflection_cycle import run_reflection_cycle
from app.runtime.review_cycle import run_review_cycle
from app.runtime.wake_cycle import run_wake_cycle


def _print_kv(payload: dict[str, Any]) -> None:
    for key, value in payload.items():
        print(f"{key}: {value}")


def cmd_init(settings: Settings) -> int:
    path = init_database(settings)
    print(f"initialized: {path}")
    return 0


def cmd_seed(settings: Settings) -> int:
    init_database(settings)
    with session_scope(settings) as session:
        counts = seed_initial_data(session, settings)
    _print_kv(counts)
    return 0


def cmd_wake(settings: Settings, reason: str) -> int:
    init_database(settings)
    with session_scope(settings) as session:
        result = run_wake_cycle(session, settings, reason)
    _print_kv(result)
    return 0


def cmd_chat(settings: Settings, message: str) -> int:
    init_database(settings)
    with session_scope(settings) as session:
        result = run_chat_cycle(session, message, settings=settings)
    print(result["response_text"])
    print(f"response_trace_id: {result['response_trace_id']}")
    return 0


def cmd_review(settings: Settings) -> int:
    init_database(settings)
    with session_scope(settings) as session:
        result = run_review_cycle(session)
    _print_kv(result)
    return 0


def cmd_reflect(settings: Settings) -> int:
    init_database(settings)
    with session_scope(settings) as session:
        result = run_reflection_cycle(session)
    _print_kv(result)
    return 0


def cmd_eval_run(settings: Settings, prompt_id: int | None) -> int:
    init_database(settings)
    with session_scope(settings) as session:
        runs = run_replay_eval(session, prompt_id, settings=settings)
        for run in runs:
            print(f"replay_run_id: {run.id} prompt_id: {run.eval_prompt_id}")
    return 0


def cmd_eval_compare(settings: Settings, prompt_id: int) -> int:
    init_database(settings)
    with session_scope(settings) as session:
        rows = compare_replay_runs(session, prompt_id)
    if not rows:
        print(f"no replay runs for prompt_id={prompt_id}")
        return 0
    for row in rows:
        print(f"run#{row['id']} at {row['created_at']}")
        print(f"  response: {row['response_text']}")
        print(f"  concerns: {row['selected_concerns']}")
        print(f"  memories: {row['selected_memories']}")
        print(f"  policy: {row['selected_attention_policy']}")
    return 0


def cmd_llm_smoke(settings: Settings) -> int:
    init_database(settings)
    with session_scope(settings) as session:
        result = run_llm_provider_smoke(session, settings)
    for line in result.cli_lines():
        print(line)
    return result.exit_code


def cmd_inspect(settings: Settings, target: str) -> int:
    init_database(settings)
    with session_scope(settings) as session:
        if target == "concerns":
            concerns = session.scalars(
                select(Concern).order_by(Concern.activation_score.desc(), Concern.id)
            ).all()
            for concern in concerns:
                print(
                    f"concern#{concern.id} [{concern.state}] "
                    f"activation={concern.activation_score:.2f} title={concern.title}"
                )
                print(f"  opened: {concern.opened_reason}")
        elif target == "probes":
            probes = session.scalars(select(InputProbe).order_by(InputProbe.id)).all()
            for probe in probes:
                print(
                    f"probe#{probe.id} [{probe.status}] {probe.source_type} "
                    f"{probe.query_or_path} mode={probe.exploration_mode}"
                )
                print(f"  why: {probe.rationale}")
                print(f"  result: {probe.result_summary}")
                budget = json_loads(probe.budget_json, {})
                if budget.get("policy_selection"):
                    print(f"  policy_selection: {budget['policy_selection']}")
        elif target == "observations":
            observations = session.scalars(select(Observation).order_by(Observation.id)).all()
            for observation in observations:
                print(
                    f"observation#{observation.id} raw#{observation.source_event_id} "
                    f"disposition={observation.possible_disposition} "
                    f"salience={observation.salience:.2f} uncertainty={observation.uncertainty:.2f}"
                )
                print(f"  summary: {observation.summary}")
                print(f"  rationale: {observation.rationale}")
        elif target == "digest-decisions":
            decisions = session.scalars(
                select(DigestDecisionTrace).order_by(DigestDecisionTrace.id)
            ).all()
            for decision in decisions:
                print(
                    f"digest_decision#{decision.id} {decision.decision} "
                    f"obs#{decision.source_observation_id} raw#{decision.source_raw_event_id}"
                )
                print(
                    "  scores: "
                    f"salience={decision.salience_snapshot:.2f} "
                    f"novelty={decision.novelty_snapshot:.2f} "
                    f"uncertainty={decision.uncertainty_snapshot:.2f} "
                    f"self_relevance={decision.self_relevance_snapshot:.2f}"
                )
                print(f"  related_concerns: {json_loads(decision.related_concern_ids_json, [])}")
                metadata = json_loads(decision.metadata_json, {})
                if metadata:
                    print(f"  metadata: {metadata}")
                print(f"  reason: {decision.reason}")
        elif target == "digest-proposals":
            proposals = session.scalars(
                select(DigestDecisionProposal).order_by(DigestDecisionProposal.id)
            ).all()
            for proposal in proposals:
                print(
                    f"digest_proposal#{proposal.id} obs#{proposal.observation_id} "
                    f"proposal={proposal.proposed_decision or '(rejected)'} "
                    f"schema_valid={proposal.schema_valid} fallback={proposal.fallback_used}"
                )
                print(
                    f"  provider={proposal.provider} model={proposal.model} "
                    f"confidence={proposal.confidence:.2f} "
                    f"model_should_apply={proposal.model_should_apply} "
                    f"should_apply={proposal.should_apply} "
                    f"normalization={proposal.normalization_reason}"
                )
                print(
                    "  comparison: "
                    f"deterministic_decision_id={proposal.deterministic_digest_decision_id} "
                    f"final_decision_id={proposal.final_digest_decision_id}"
                )
                print(
                    f"  related_concerns: "
                    f"{json_loads(proposal.related_concern_ids_json, [])}"
                )
                print(f"  risk_flags: {json_loads(proposal.risk_flags_json, [])}")
                if proposal.error_class:
                    print(
                        f"  error: {proposal.error_class} "
                        f"{proposal.error_message_sanitized}"
                    )
                print(f"  reason: {proposal.reason}")
        elif target == "attention-policy":
            policy = session.scalar(
                select(AttentionPolicy).order_by(AttentionPolicy.version.desc()).limit(1)
            )
            if not policy:
                print("no attention policy")
            else:
                print(f"policy#{policy.id} version={policy.version}")
                print(
                    "  source_preferences: "
                    f"{json_loads(policy.source_preferences_json, {})}"
                )
                print(
                    "  response_preferences: "
                    f"{json_loads(policy.response_preferences_json, {})}"
                )
                events = session.scalars(
                    select(AttentionPolicyEvent)
                    .order_by(AttentionPolicyEvent.created_at.desc())
                    .limit(5)
                ).all()
                for event in events:
                    print(
                        f"  event#{event.id} {event.event_type} "
                        f"{event.target_field}: {event.reason}"
                    )
                    outcome_ids = json_loads(event.evidence_outcome_ids_json, [])
                    if outcome_ids:
                        print(f"    outcome_evidence: {outcome_ids}")
        elif target == "actions":
            actions = session.scalars(select(Action).order_by(Action.id)).all()
            for action in actions:
                print(f"action#{action.id} {action.action_type} [{action.status}]")
                print(f"  rationale: {action.rationale}")
        elif target == "outcomes":
            outcomes = session.scalars(select(Outcome).order_by(Outcome.id)).all()
            for outcome in outcomes:
                print(f"outcome#{outcome.id} action#{outcome.action_id}")
                print(f"  result: {outcome.observed_result}")
                print(
                    "  attention_effect: "
                    f"{json_loads(outcome.effect_on_attention_policy_json, {})}"
                )
        elif target == "wake-requests":
            requests = session.scalars(select(WakeRequest).order_by(WakeRequest.id)).all()
            for request in requests:
                print(
                    f"wake_request#{request.id} urgency={request.urgency:.2f} "
                    f"accepted={request.accepted_by_scheduler}"
                )
                print(f"  reason: {request.reason}")
        elif target == "traces":
            traces = session.scalars(select(ResponseTrace).order_by(ResponseTrace.id)).all()
            for trace in traces:
                print(f"trace#{trace.id} action#{trace.response_action_id}")
                print(f"  memories: {json_loads(trace.selected_memory_ids_json, [])}")
                print(f"  concerns: {json_loads(trace.selected_concerns_json, [])}")
                print(f"  modes: {json_loads(trace.concern_modes_json, {})}")
                print(f"  prompt: {trace.prompt_summary}")
        elif target == "llm-provider":
            print(f"provider: {settings.llm_provider}")
            print(f"model: {settings.llm_model or '(provider-specific env or unset)'}")
            print(f"max_tokens: {settings.llm_max_tokens}")
            print(f"timeout_seconds: {settings.llm_timeout_seconds}")
        elif target == "observation-extractor":
            print(f"extractor: {settings.observation_extractor}")
            print(f"fallback: {settings.observation_extractor_fallback}")
            print(f"llm_provider: {settings.llm_provider}")
            print(f"llm_model: {settings.llm_model or '(provider-specific env or unset)'}")
            print(f"digest_decider: {settings.digest_decider}")
            print(
                "digest_proposal_confidence_threshold: "
                f"{settings.digest_proposal_confidence_threshold}"
            )
        else:
            raise ValueError(f"unknown inspect target: {target}")
    return 0


def cmd_discord_status(settings: Settings) -> int:
    init_database(settings)
    with session_scope(settings) as session:
        controller = DiscordController(settings)
        print(controller.render_status(session))
    print("Config:")
    for key, value in settings.discord.public_status().items():
        print(f"  {key}: {value}")
    return 0


def cmd_discord_doctor(
    settings: Settings, target_mode: str | None, live_run: bool
) -> int:
    mode = DiscordRuntimeMode.parse(target_mode) if target_mode else None
    report = diagnose_discord_settings(
        settings.discord,
        target_mode=mode,
        live_run=live_run,
    )
    for line in report.as_lines():
        print(line)
    return 0 if report.ok else 1


def _parse_option_assignments(assignments: Sequence[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for assignment in assignments:
        if "=" not in assignment:
            raise ValueError(f"option must be KEY=VALUE: {assignment}")
        key, value = assignment.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def cmd_discord_command(
    settings: Settings,
    name: str,
    user_id: str,
    channel_id: str | None,
    option_assignments: Sequence[str],
) -> int:
    init_database(settings)
    with session_scope(settings) as session:
        result = DiscordController(settings).dispatch_command(
            session,
            DiscordCommandContext(
                command_name=name,
                channel_id=channel_id,
                user_id=user_id,
                options=_parse_option_assignments(option_assignments),
            ),
        )
    print(result.message)
    return 0 if result.ok else 1


def cmd_discord_post(
    settings: Settings, role: str, message: str, reason: str, autonomous: bool
) -> int:
    init_database(settings)
    with session_scope(settings) as session:
        controller = DiscordController(settings)
        if autonomous:
            result = controller.prepare_autonomous_post(
                session, role, message, reason=reason
            )
        else:
            result = controller.prepare_trace_post(session, role, message, rationale=reason)
    print(result.message if result.allowed else result.reason)
    return 0 if result.allowed else 1


def cmd_discord_cycle(
    settings: Settings,
    cycle: str,
    reason: str,
    prompt_id: int | None,
) -> int:
    init_database(settings)
    with session_scope(settings) as session:
        controller = DiscordController(settings)
        if cycle == "wake":
            result = run_wake_cycle(session, settings, reason=f"discord_trace:{reason}")
        elif cycle == "review":
            result = run_review_cycle(session)
        elif cycle == "reflect":
            result = run_reflection_cycle(session)
        elif cycle == "eval":
            runs = run_replay_eval(session, prompt_id, settings=settings)
            result = {"replay_runs": len(runs), "replay_run_ids": [run.id for run in runs]}
        else:
            raise ValueError(f"unknown Discord trace cycle: {cycle}")
        post_results = controller.prepare_cycle_trace_posts(
            session,
            "replay" if cycle == "eval" else cycle,
            result,
            trigger=reason,
        )
    _print_kv(result)
    for post_result in post_results:
        status = "prepared" if post_result.allowed else f"skipped:{post_result.reason}"
        print(f"discord_trace_post: {status} channel_id={post_result.channel_id}")
    return 0 if all(post.allowed for post in post_results) else 1


def cmd_discord_run(settings: Settings, *, dry_run: bool = False) -> int:
    return run_discord_bot(settings, dry_run=dry_run)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.main")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Override project root for DB/world/workspace resolution.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("seed")
    wake = sub.add_parser("wake")
    wake.add_argument("--reason", default="manual")
    chat = sub.add_parser("chat")
    chat.add_argument("message")
    sub.add_parser("review")
    sub.add_parser("reflect")
    eval_parser = sub.add_parser("eval")
    eval_sub = eval_parser.add_subparsers(dest="eval_command", required=True)
    eval_run = eval_sub.add_parser("run")
    eval_run.add_argument("--prompt-id", type=int, default=None)
    eval_compare = eval_sub.add_parser("compare")
    eval_compare.add_argument("--prompt-id", type=int, required=True)
    llm = sub.add_parser("llm")
    llm_sub = llm.add_subparsers(dest="llm_command", required=True)
    llm_sub.add_parser("smoke")
    inspect = sub.add_parser("inspect")
    inspect.add_argument(
        "target",
        choices=[
            "concerns",
            "probes",
            "observations",
            "digest-decisions",
            "digest-proposals",
            "attention-policy",
            "actions",
            "outcomes",
            "wake-requests",
            "traces",
            "llm-provider",
            "observation-extractor",
        ],
    )
    discord = sub.add_parser("discord")
    discord_sub = discord.add_subparsers(dest="discord_command", required=True)
    discord_sub.add_parser("status")
    discord_doctor = discord_sub.add_parser("doctor")
    discord_doctor.add_argument(
        "--mode",
        choices=[mode.value for mode in DiscordRuntimeMode],
        default=None,
        help="Validate readiness for a specific Discord runtime mode.",
    )
    discord_doctor.add_argument(
        "--live",
        action="store_true",
        help="Treat missing live bot requirements as startup blockers.",
    )
    discord_run = discord_sub.add_parser("run")
    discord_run.add_argument(
        "--dry-run",
        action="store_true",
        help="Build discord.py bot commands/intents without connecting to Discord.",
    )
    discord_cmd = discord_sub.add_parser("command")
    discord_cmd.add_argument("name")
    discord_cmd.add_argument("--user-id", default="local-user")
    discord_cmd.add_argument("--channel-id", default=None)
    discord_cmd.add_argument(
        "--option",
        action="append",
        default=[],
        help="Command option as KEY=VALUE. Repeat for multiple options.",
    )
    discord_post = discord_sub.add_parser("post")
    discord_post.add_argument("--role", required=True)
    discord_post.add_argument("--message", required=True)
    discord_post.add_argument("--reason", default="manual CLI Discord post smoke")
    discord_post.add_argument("--autonomous", action="store_true")
    discord_cycle = discord_sub.add_parser("cycle")
    discord_cycle.add_argument("cycle", choices=["wake", "review", "reflect", "eval"])
    discord_cycle.add_argument("--reason", default="manual")
    discord_cycle.add_argument("--prompt-id", type=int, default=None)
    return parser


def settings_from_args(args: argparse.Namespace) -> Settings:
    base = Settings.load()
    if args.project_root is None:
        return base
    root = args.project_root.resolve()
    return replace(
        base,
        project_root=root,
        db_path=(root / "data" / "agent.db").resolve(),
        world_root=(root / "world").resolve(),
        workspace_root=(root / "agent_workspace").resolve(),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = settings_from_args(args)
    if args.command == "init":
        return cmd_init(settings)
    if args.command == "seed":
        return cmd_seed(settings)
    if args.command == "wake":
        return cmd_wake(settings, args.reason)
    if args.command == "chat":
        return cmd_chat(settings, args.message)
    if args.command == "review":
        return cmd_review(settings)
    if args.command == "reflect":
        return cmd_reflect(settings)
    if args.command == "eval" and args.eval_command == "run":
        return cmd_eval_run(settings, args.prompt_id)
    if args.command == "eval" and args.eval_command == "compare":
        return cmd_eval_compare(settings, args.prompt_id)
    if args.command == "llm" and args.llm_command == "smoke":
        return cmd_llm_smoke(settings)
    if args.command == "inspect":
        return cmd_inspect(settings, args.target)
    if args.command == "discord" and args.discord_command == "status":
        return cmd_discord_status(settings)
    if args.command == "discord" and args.discord_command == "doctor":
        return cmd_discord_doctor(settings, args.mode, args.live)
    if args.command == "discord" and args.discord_command == "run":
        return cmd_discord_run(settings, dry_run=args.dry_run)
    if args.command == "discord" and args.discord_command == "command":
        return cmd_discord_command(
            settings, args.name, args.user_id, args.channel_id, args.option
        )
    if args.command == "discord" and args.discord_command == "post":
        return cmd_discord_post(
            settings, args.role, args.message, args.reason, args.autonomous
        )
    if args.command == "discord" and args.discord_command == "cycle":
        return cmd_discord_cycle(settings, args.cycle, args.reason, args.prompt_id)
    parser.error("unreachable command")
    return 2
