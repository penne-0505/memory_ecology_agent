"""Discord adapter controller backed by the canonical runtime and DB."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import re
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adapters.clock import now_utc
from app.adapters.discord_config import (
    DiscordChannelConfig,
    DiscordSettings,
    is_secret_like_name,
)
from app.adapters.discord_renderers import (
    bullet_lines,
    clip_discord_text,
    looks_sensitive_text,
    render_mapping,
)
from app.cognition.attention_policy import (
    update_policy_from_observations,
    update_policy_from_outcomes,
)
from app.cognition.concern_manager import upsert_concern_from_observation
from app.cognition.digest_decider import create_digest_proposal, proposal_metadata
from app.cognition.digestor import digest_observation, persist_digest_decision
from app.cognition.memory_manager import create_memory_from_observation
from app.cognition.observation_extractor import draft_observation, persist_observation
from app.config import Settings
from app.db.json_utils import json_dict, json_dumps, json_list, json_loads
from app.db.models import (
    Action,
    AttentionPolicy,
    AttentionPolicyEvent,
    Concern,
    ConcernEvent,
    CoreChangeProposal,
    CoreProfile,
    InputProbe,
    Observation,
    Outcome,
    RawEvent,
    ReplayRun,
    ResponseTrace,
    WakeRequest,
)
from app.eval.replay import run_replay_eval
from app.runtime.events import persist_raw_event
from app.runtime.modes import DiscordRuntimeMode, clamp_mode
from app.runtime.wake_cycle import run_wake_cycle
from app.schemas import RawEventInput


@dataclass(frozen=True)
class DiscordAttachmentInput:
    filename: str
    content_type: str | None
    size: int
    content_text: str | None = None


@dataclass(frozen=True)
class DiscordMessageInput:
    message_id: str
    channel_id: str
    author_id: str
    content_text: str
    created_at: datetime
    author_is_bot: bool = False
    author_is_system: bool = False
    thread_id: str | None = None
    parent_message_id: str | None = None
    attachments: list[DiscordAttachmentInput] = field(default_factory=list)


@dataclass(frozen=True)
class DiscordIngestResult:
    ingested: bool
    reason: str
    raw_event_id: int | None = None
    observation_ids: list[int] = field(default_factory=list)
    outcome_id: int | None = None


@dataclass(frozen=True)
class DiscordReactionInput:
    message_id: str
    channel_id: str
    user_id: str
    emoji: str
    created_at: datetime
    user_is_bot: bool = False


@dataclass(frozen=True)
class DiscordReactionResult:
    recorded: bool
    reason: str
    outcome_id: int | None = None


@dataclass(frozen=True)
class DiscordCommandContext:
    command_name: str
    channel_id: str | None
    user_id: str
    options: dict[str, Any] = field(default_factory=dict)
    interaction_id: str | None = None
    created_at: datetime | None = None


@dataclass(frozen=True)
class DiscordCommandResult:
    ok: bool
    message: str
    action_id: int | None = None
    outcome_id: int | None = None
    post_channel_role: str | None = None


@dataclass(frozen=True)
class DiscordPostResult:
    allowed: bool
    reason: str
    message: str
    channel_id: str | None = None
    action_id: int | None = None
    outcome_id: int | None = None


TRACE_CHANNEL_BY_CYCLE = {
    "wake": "agent_trace",
    "review": "agent_trace",
    "reflection": "agent_trace",
    "replay": "agent_eval",
    "eval": "agent_eval",
}


MUTATING_COMMANDS = {"wake", "replay", "feedback", "inject", "mute", "mode"}
READ_ONLY_COMMANDS = {"ping", "status", "concerns", "concern", "policy", "trace"}
ALL_COMMANDS = READ_ONLY_COMMANDS | MUTATING_COMMANDS
_DURATION_PATTERN = re.compile(r"^\s*(\d+)\s*([mhd])?\s*$", re.IGNORECASE)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_duration(value: str) -> timedelta:
    raw = value.strip().lower()
    if raw in {"", "0", "off", "none", "unmute"}:
        return timedelta(seconds=0)
    match = _DURATION_PATTERN.match(raw)
    if not match:
        raise ValueError("duration must look like 15m, 2h, 1d, or 0")
    amount = int(match.group(1))
    suffix = match.group(2) or "m"
    if suffix == "m":
        return timedelta(minutes=amount)
    if suffix == "h":
        return timedelta(hours=amount)
    return timedelta(days=amount)


def _parse_prefixed_id(value: str, *prefixes: str) -> int | None:
    raw = value.strip()
    for prefix in prefixes:
        if raw.startswith(prefix):
            raw = raw[len(prefix) :]
            break
    return int(raw) if raw.isdigit() else None


class DiscordController:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.discord = settings.discord

    def effective_mode(self, session: Session) -> DiscordRuntimeMode:
        if not self.discord.enabled:
            return DiscordRuntimeMode.OBSERVE_ONLY
        if not self.discord.allow_mode_command:
            return clamp_mode(self.discord.mode, self.discord.max_mode)
        action = session.scalar(
            select(Action)
            .where(Action.action_type == "discord_mode_change")
            .where(Action.status == "completed")
            .order_by(Action.created_at.desc(), Action.id.desc())
            .limit(1)
        )
        if action is None:
            return clamp_mode(self.discord.mode, self.discord.max_mode)
        requested = json_dict(action.payload_json).get("mode")
        try:
            return clamp_mode(DiscordRuntimeMode.parse(str(requested)), self.discord.max_mode)
        except ValueError:
            return clamp_mode(self.discord.mode, self.discord.max_mode)

    def channel_for_message(
        self, message: DiscordMessageInput
    ) -> DiscordChannelConfig | None:
        return self.discord.channel_for_id(message.channel_id)

    def can_ingest_message(
        self, session: Session, message: DiscordMessageInput
    ) -> tuple[bool, str, DiscordChannelConfig | None]:
        if not self.discord.enabled:
            return False, "discord_disabled", None
        mode = self.effective_mode(session)
        if not mode.can_ingest:
            return False, f"mode_{mode.value}_does_not_ingest", None
        channel = self.channel_for_message(message)
        if channel is None:
            return False, "channel_not_configured", None
        if message.author_is_bot:
            return False, "bot_author_not_ingestable", channel
        if message.author_is_system:
            return False, "system_author_not_ingestable", channel
        if not channel.ingestable:
            return False, f"channel_role_{channel.role}_not_ingestable", channel
        return True, "ingestable", channel

    def ingest_message(
        self,
        session: Session,
        message: DiscordMessageInput,
        *,
        create_observations: bool | None = None,
    ) -> DiscordIngestResult:
        allowed, reason, channel = self.can_ingest_message(session, message)
        if not allowed:
            return DiscordIngestResult(ingested=False, reason=reason)

        attachment_texts, attachment_metadata = self._prepare_attachments(message.attachments)
        if not message.content_text.strip() and not attachment_texts:
            return DiscordIngestResult(ingested=False, reason="empty_message")

        created_at = _aware_utc(message.created_at)
        content_parts = [message.content_text.strip()]
        content_parts.extend(attachment_texts)
        raw_event = persist_raw_event(
            session,
            RawEventInput(
                source_type="discord_user_message",
                event_type="user_message",
                payload={
                    "source": "discord_user_message",
                    "author_type": "user",
                    "discord_author_id": message.author_id,
                    "discord_message_id": message.message_id,
                    "discord_channel_id": message.channel_id,
                    "discord_channel_role": channel.role if channel else None,
                    "discord_thread_id": message.thread_id,
                    "discord_parent_message_id": message.parent_message_id,
                    "ingestable": True,
                    "created_at": created_at.isoformat(),
                    "attachments": attachment_metadata,
                },
                content_text="\n\n".join(part for part in content_parts if part),
                happened_at=created_at,
            ),
        )
        reply_outcome = self._record_autonomous_reply_outcome(
            session, message, raw_event.id
        )
        observations: list[Observation] = []
        should_create = (
            self.discord.create_observations_from_ingest
            if create_observations is None
            else create_observations
        )
        if should_create:
            observations = self._create_observations_from_raw_event(session, raw_event)
        return DiscordIngestResult(
            ingested=True,
            reason="ingested",
            raw_event_id=raw_event.id,
            observation_ids=[observation.id for observation in observations],
            outcome_id=reply_outcome.id if reply_outcome else None,
        )

    def _prepare_attachments(
        self, attachments: list[DiscordAttachmentInput]
    ) -> tuple[list[str], list[dict[str, object]]]:
        texts: list[str] = []
        metadata: list[dict[str, object]] = []
        for attachment in attachments:
            reason = self._attachment_rejection_reason(attachment)
            accepted = reason is None
            metadata.append(
                {
                    "filename": attachment.filename,
                    "content_type": attachment.content_type,
                    "size": attachment.size,
                    "ingested": accepted,
                    "rejected_reason": reason,
                }
            )
            if accepted and attachment.content_text:
                texts.append(
                    f"[attachment:{attachment.filename}]\n"
                    f"{attachment.content_text[: self.discord.max_attachment_bytes]}"
                )
        return texts, metadata

    def _attachment_rejection_reason(
        self, attachment: DiscordAttachmentInput
    ) -> str | None:
        if not self.discord.attachment_ingest_enabled:
            return "attachment_ingest_disabled"
        if is_secret_like_name(attachment.filename):
            return "secret_like_filename"
        if attachment.size > self.discord.max_attachment_bytes:
            return "attachment_too_large"
        content_type = attachment.content_type or ""
        if content_type not in self.discord.allowed_attachment_content_types:
            return "content_type_not_allowed"
        if attachment.content_text is None:
            return "attachment_text_unavailable"
        if looks_sensitive_text(attachment.content_text):
            return "attachment_text_looks_sensitive"
        return None

    def _create_observations_from_raw_event(
        self, session: Session, raw_event: RawEvent
    ) -> list[Observation]:
        draft = draft_observation(raw_event, source_probe_id=None)
        observation = persist_observation(session, draft)
        decision = digest_observation(observation)
        proposal_result = create_digest_proposal(
            session, observation, decision, self.settings
        )
        related_concern_ids: list[int] = []
        if decision.disposition == "concern_candidate":
            concern = upsert_concern_from_observation(session, observation)
            related_concern_ids = [concern.id]
            create_memory_from_observation(session, observation, [concern.id])
        elif decision.disposition == "memory_candidate":
            create_memory_from_observation(session, observation, [])
        trace = persist_digest_decision(
            session,
            observation,
            decision,
            run_id="discord_ingest",
            related_concern_ids=related_concern_ids,
            metadata={
                "source": "discord",
                **proposal_metadata(proposal_result, self.settings),
            },
        )
        if proposal_result.proposal is not None:
            proposal_result.proposal.deterministic_digest_decision_id = trace.id
            proposal_result.proposal.final_digest_decision_id = trace.id
        update_policy_from_observations(session, [observation], "conversation")
        return [observation]

    def _record_autonomous_reply_outcome(
        self, session: Session, message: DiscordMessageInput, raw_event_id: int
    ) -> Outcome | None:
        if not message.parent_message_id:
            return None
        action = self._find_discord_post_action_by_message_id(
            session, message.parent_message_id
        )
        if action is None or action.action_type != "discord_autonomous_post":
            return None
        return self._add_outcome(
            session,
            action.id,
            "User reply to Discord autonomous post ingested as outcome evidence.",
            {
                "discord_reply_message_id": message.message_id,
                "raw_event_id": raw_event_id,
                "source": "discord_user_reply_to_autonomous_post",
            },
            user_feedback=message.content_text,
        )

    def record_reaction(
        self, session: Session, reaction: DiscordReactionInput
    ) -> DiscordReactionResult:
        if not self.discord.enabled:
            return DiscordReactionResult(False, "discord_disabled")
        mode = self.effective_mode(session)
        if not mode.can_ingest:
            return DiscordReactionResult(False, f"mode_{mode.value}_does_not_ingest")
        channel = self.discord.channel_for_id(reaction.channel_id)
        if channel is None:
            return DiscordReactionResult(False, "channel_not_configured")
        if not channel.ingestable:
            return DiscordReactionResult(False, f"channel_role_{channel.role}_not_ingestable")
        if reaction.user_is_bot:
            return DiscordReactionResult(False, "bot_user_not_recorded")
        action = self._find_discord_post_action_by_message_id(
            session, reaction.message_id
        )
        if action is None or action.action_type != "discord_autonomous_post":
            return DiscordReactionResult(False, "autonomous_post_action_not_found")
        outcome = self._add_outcome(
            session,
            action.id,
            "User reaction to Discord autonomous post recorded as outcome evidence.",
            {
                "source": "discord_user_reaction_to_autonomous_post",
                "discord_message_id": reaction.message_id,
                "discord_channel_id": reaction.channel_id,
                "discord_user_id": reaction.user_id,
                "emoji": reaction.emoji,
                "created_at": _aware_utc(reaction.created_at).isoformat(),
            },
            user_feedback=f"reaction:{reaction.emoji}",
        )
        return DiscordReactionResult(True, "recorded", outcome.id)

    def _find_discord_post_action_by_message_id(
        self, session: Session, message_id: str
    ) -> Action | None:
        actions = session.scalars(
            select(Action)
            .where(Action.action_type.in_(["discord_autonomous_post", "discord_trace_post"]))
            .order_by(Action.created_at.desc(), Action.id.desc())
            .limit(50)
        ).all()
        for action in actions:
            payload = json_dict(action.payload_json)
            if str(payload.get("discord_message_id") or "") == str(message_id):
                return action
        return None

    def dispatch_command(
        self, session: Session, context: DiscordCommandContext
    ) -> DiscordCommandResult:
        name = context.command_name.removeprefix("/").strip().lower()
        if name not in ALL_COMMANDS:
            return DiscordCommandResult(False, f"Unknown command: /{name}")
        if not self.discord.enabled and name not in {"status", "ping"}:
            return DiscordCommandResult(False, "Discord integration is disabled.")
        mode = self.effective_mode(session)
        if name in READ_ONLY_COMMANDS and name not in {"status", "ping"} and not mode.can_run_commands:
            return DiscordCommandResult(False, f"/{name} requires command_enabled mode.")
        if name in MUTATING_COMMANDS:
            if not mode.can_run_commands and name != "mode":
                return DiscordCommandResult(False, f"/{name} requires command_enabled mode.")
            if not self._can_mutate_from_context(context, name):
                return DiscordCommandResult(False, f"/{name} is restricted to admin users or agent_admin.")

        handler = getattr(self, f"_cmd_{name}")
        return handler(session, context)

    def _can_mutate_from_context(
        self, context: DiscordCommandContext, command_name: str
    ) -> bool:
        if context.user_id in self.discord.admin_user_ids:
            return True
        if command_name == "mode":
            return False
        channel = self.discord.channel_for_id(context.channel_id)
        return channel is not None and channel.role == "agent_admin"

    def _cmd_ping(self, session: Session, context: DiscordCommandContext) -> DiscordCommandResult:
        return DiscordCommandResult(True, "pong")

    def _cmd_status(
        self, session: Session, context: DiscordCommandContext
    ) -> DiscordCommandResult:
        return DiscordCommandResult(True, self.render_status(session))

    def render_status(self, session: Session) -> str:
        mode = self.effective_mode(session)
        concerns = session.scalars(
            select(Concern)
            .where(Concern.state.in_(["seed", "active"]))
            .order_by(Concern.activation_score.desc(), Concern.id)
            .limit(3)
        ).all()
        policy = session.scalar(
            select(AttentionPolicy).order_by(AttentionPolicy.version.desc()).limit(1)
        )
        last_wake = session.scalar(
            select(Action)
            .where(Action.action_type.in_(["request_wake", "discord_command_wake"]))
            .order_by(Action.created_at.desc(), Action.id.desc())
            .limit(1)
        )
        last_review = session.scalar(
            select(Action)
            .where(Action.rationale.like("Review cycle%"))
            .order_by(Action.created_at.desc(), Action.id.desc())
            .limit(1)
        )
        last_reflection = session.scalar(
            select(CoreChangeProposal)
            .order_by(CoreChangeProposal.created_at.desc(), CoreChangeProposal.id.desc())
            .limit(1)
        )
        next_wake = session.scalar(
            select(WakeRequest)
            .where(WakeRequest.accepted_by_scheduler.is_(True))
            .order_by(WakeRequest.not_before, WakeRequest.id)
            .limit(1)
        )
        last_action = session.scalar(select(Action).order_by(Action.id.desc()).limit(1))
        mute_until = self.current_mute_until(session)
        lines = [
            "Discord adapter status",
            f"Mode: {mode.value}",
            f"Enabled: {self.discord.enabled}",
            f"Autonomous posting: {'enabled' if mode.can_post_autonomously else 'disabled'}",
            f"Mute: {mute_until.isoformat() if mute_until else 'off'}",
            f"Last action: #{last_action.id} {last_action.action_type}" if last_action else "Last action: none",
            f"Last wake: act_{last_wake.id} {last_wake.action_type}" if last_wake else "Last wake: none",
            f"Last review: act_{last_review.id}" if last_review else "Last review: none",
            f"Last reflection proposal: core_change_{last_reflection.id}" if last_reflection else "Last reflection proposal: none",
            f"Next scheduled wake: {next_wake.not_before or next_wake.preferred_at}" if next_wake else "Next scheduled wake: none",
            "Active concerns:",
            bullet_lines(
                [
                    f"con_{concern.id} [{concern.state}] {concern.title} ({concern.activation_score:.2f})"
                    for concern in concerns
                ]
            ),
        ]
        if policy:
            lines.extend(
                [
                    f"Attention policy: v{policy.version}",
                    f"source_preferences: {render_mapping(json_dict(policy.source_preferences_json))}",
                    f"response_preferences: {render_mapping(json_dict(policy.response_preferences_json))}",
                ]
            )
        return clip_discord_text("\n".join(lines))

    def _cmd_concerns(
        self, session: Session, context: DiscordCommandContext
    ) -> DiscordCommandResult:
        active = session.scalars(
            select(Concern)
            .where(Concern.state.in_(["seed", "active"]))
            .order_by(Concern.activation_score.desc(), Concern.id)
            .limit(8)
        ).all()
        dormant_count = session.scalar(
            select(func.count(Concern.id)).where(Concern.state == "dormant")
        ) or 0
        resolved = session.scalars(
            select(Concern)
            .where(Concern.state.in_(["resolved", "archived"]))
            .order_by(Concern.updated_at.desc(), Concern.id.desc())
            .limit(5)
        ).all()
        reactivated = session.scalars(
            select(ConcernEvent)
            .where(ConcernEvent.event_type == "reinforced")
            .order_by(ConcernEvent.created_at.desc(), ConcernEvent.id.desc())
            .limit(5)
        ).all()
        lines = [
            "Concerns",
            "Active:",
            bullet_lines([f"con_{c.id} [{c.state}] {c.title}" for c in active]),
            "Recently reactivated:",
            bullet_lines(
                [f"con_{event.concern_id} via evt_{event.id}" for event in reactivated]
            ),
            "Recently resolved/archived:",
            bullet_lines([f"con_{c.id} [{c.state}] {c.title}" for c in resolved]),
            f"Dormant count: {dormant_count}",
        ]
        return DiscordCommandResult(True, clip_discord_text("\n".join(lines)))

    def _cmd_concern(
        self, session: Session, context: DiscordCommandContext
    ) -> DiscordCommandResult:
        concern_id = int(context.options.get("id", 0))
        concern = session.get(Concern, concern_id)
        if concern is None:
            return DiscordCommandResult(False, f"Concern not found: con_{concern_id}")
        events = session.scalars(
            select(ConcernEvent)
            .where(ConcernEvent.concern_id == concern.id)
            .order_by(ConcernEvent.created_at.desc(), ConcernEvent.id.desc())
            .limit(5)
        ).all()
        source_observation_ids = [
            int(value)
            for value in json_list(concern.source_observation_ids_json)
            if isinstance(value, int) or str(value).isdigit()
        ][:8]
        related_observations = (
            session.scalars(
                select(Observation)
                .where(Observation.id.in_(source_observation_ids))
                .order_by(Observation.id.desc())
                .limit(5)
            ).all()
            if source_observation_ids
            else []
        )
        related_actions = [
            action
            for action in session.scalars(
                select(Action).order_by(Action.created_at.desc(), Action.id.desc()).limit(30)
            ).all()
            if concern.id in [int(value) for value in json_list(action.related_concern_ids_json) if str(value).isdigit()]
        ][:5]
        lines = [
            f"con_{concern.id}: {concern.title}",
            f"state: {concern.state}",
            f"activation_score: {concern.activation_score:.2f}",
            f"closure_hypothesis: {concern.closure_hypothesis}",
            f"tension: {render_mapping(json_dict(concern.tension_json))}",
            "recent events:",
            bullet_lines([f"evt_{event.id} {event.event_type}: {event.reason}" for event in events]),
            "related observations:",
            bullet_lines([f"obs_{obs.id}: {obs.summary}" for obs in related_observations]),
            "related actions:",
            bullet_lines([f"act_{action.id}: {action.action_type}" for action in related_actions]),
        ]
        return DiscordCommandResult(True, clip_discord_text("\n".join(lines)))

    def _cmd_policy(
        self, session: Session, context: DiscordCommandContext
    ) -> DiscordCommandResult:
        policy = session.scalar(
            select(AttentionPolicy).order_by(AttentionPolicy.version.desc()).limit(1)
        )
        if policy is None:
            return DiscordCommandResult(False, "No attention policy exists.")
        events = session.scalars(
            select(AttentionPolicyEvent)
            .order_by(AttentionPolicyEvent.created_at.desc(), AttentionPolicyEvent.id.desc())
            .limit(5)
        ).all()
        lines = [
            f"attention_policy v{policy.version}",
            f"source_preferences: {render_mapping(json_dict(policy.source_preferences_json))}",
            f"salience_preferences: {render_mapping(json_dict(policy.salience_preferences_json))}",
            f"action_preferences: {render_mapping(json_dict(policy.action_preferences_json))}",
            f"response_preferences: {render_mapping(json_dict(policy.response_preferences_json))}",
            "recent events:",
            bullet_lines([f"ape_{event.id} {event.target_field}: {event.reason}" for event in events]),
        ]
        return DiscordCommandResult(True, clip_discord_text("\n".join(lines)))

    def _cmd_trace(
        self, session: Session, context: DiscordCommandContext
    ) -> DiscordCommandResult:
        run_id = str(context.options.get("run_id") or "latest")
        return DiscordCommandResult(True, self.render_trace_summary(session, run_id))

    def render_trace_summary(self, session: Session, run_id: str = "latest") -> str:
        parsed_trace_id = _parse_prefixed_id(run_id, "trace_", "response_trace_", "run_")
        if parsed_trace_id is not None:
            trace = session.get(ResponseTrace, parsed_trace_id)
            if trace is not None:
                return clip_discord_text(
                    "\n".join(
                        [
                            f"response_trace #{trace.id}",
                            f"action: act_{trace.response_action_id}",
                            f"memories: {json_loads(trace.selected_memory_ids_json, [])}",
                            f"concerns: {json_loads(trace.selected_concerns_json, [])}",
                            f"modes: {json_loads(trace.concern_modes_json, {})}",
                            f"prompt: {trace.prompt_summary}",
                        ]
                    )
                )
        latest_probes = session.scalars(
            select(InputProbe).order_by(InputProbe.created_at.desc(), InputProbe.id.desc()).limit(3)
        ).all()
        latest_observations = session.scalars(
            select(Observation)
            .order_by(Observation.created_at.desc(), Observation.id.desc())
            .limit(5)
        ).all()
        latest_concern_events = session.scalars(
            select(ConcernEvent)
            .order_by(ConcernEvent.created_at.desc(), ConcernEvent.id.desc())
            .limit(5)
        ).all()
        latest_policy_events = session.scalars(
            select(AttentionPolicyEvent)
            .order_by(AttentionPolicyEvent.created_at.desc(), AttentionPolicyEvent.id.desc())
            .limit(5)
        ).all()
        latest_actions = session.scalars(
            select(Action).order_by(Action.created_at.desc(), Action.id.desc()).limit(5)
        ).all()
        latest_outcomes = session.scalars(
            select(Outcome).order_by(Outcome.created_at.desc(), Outcome.id.desc()).limit(5)
        ).all()
        return clip_discord_text(
            "\n".join(
                [
                    "latest trace summary",
                    "Probes:",
                    bullet_lines(
                        [
                            f"probe_{probe.id} {probe.source_type} {probe.query_or_path}: {probe.result_summary or probe.status}"
                            for probe in latest_probes
                        ]
                    ),
                    "Observations:",
                    bullet_lines(
                        [f"obs_{obs.id}: {obs.summary}" for obs in latest_observations]
                    ),
                    "Concern updates:",
                    bullet_lines(
                        [
                            f"evt_{event.id} con_{event.concern_id} {event.event_type}: {event.reason}"
                            for event in latest_concern_events
                        ]
                    ),
                    "Attention policy:",
                    bullet_lines(
                        [
                            f"ape_{event.id} {event.target_field}: {event.reason}"
                            for event in latest_policy_events
                        ]
                    ),
                    "recent actions:",
                    bullet_lines(
                        [
                            f"act_{action.id} {action.action_type} [{action.status}]"
                            for action in latest_actions
                        ]
                    ),
                    "recent outcomes:",
                    bullet_lines(
                        [
                            f"out_{outcome.id} act_{outcome.action_id}: {outcome.observed_result}"
                            for outcome in latest_outcomes
                        ]
                    ),
                ]
            )
        )

    def _cmd_wake(
        self, session: Session, context: DiscordCommandContext
    ) -> DiscordCommandResult:
        reason = str(context.options.get("reason") or "discord_manual")
        action = self._add_action(
            session,
            "discord_command_wake",
            f"Discord /wake requested by user {context.user_id}.",
            {
                "source": "discord_command",
                "command": "wake",
                "reason": reason,
                "discord_user_id": context.user_id,
                "discord_channel_id": context.channel_id,
                "discord_interaction_id": context.interaction_id,
            },
            external_effect="scheduler_request",
        )
        result = run_wake_cycle(session, self.settings, reason=f"discord:{reason}")
        outcome = self._add_outcome(
            session,
            action.id,
            "Discord /wake completed through normal wake_cycle.",
            {"wake_result": result},
        )
        message = "wake_cycle completed\n" + "\n".join(f"{k}: {v}" for k, v in result.items())
        return DiscordCommandResult(
            True,
            clip_discord_text(message),
            action_id=action.id,
            outcome_id=outcome.id,
            post_channel_role="agent_trace",
        )

    def _cmd_replay(
        self, session: Session, context: DiscordCommandContext
    ) -> DiscordCommandResult:
        prompt_id_raw = context.options.get("prompt_id")
        prompt_id = int(prompt_id_raw) if prompt_id_raw not in (None, "") else None
        action = self._add_action(
            session,
            "discord_command_replay",
            f"Discord /replay requested by user {context.user_id}.",
            {
                "source": "discord_command",
                "command": "replay",
                "prompt_id": prompt_id,
                "discord_user_id": context.user_id,
                "discord_channel_id": context.channel_id,
            },
            external_effect="eval",
        )
        runs = run_replay_eval(session, prompt_id, settings=self.settings)
        run_lines = []
        for run in runs[:5]:
            run_lines.append(
                " ".join(
                    [
                        f"run_{run.id}",
                        f"prompt_{run.eval_prompt_id}",
                        f"concerns={json_loads(run.selected_concerns_json, [])}",
                        f"memories={json_loads(run.selected_memories_json, [])}",
                        f"policy={render_mapping(json_loads(run.selected_attention_policy_json, {}))}",
                    ]
                )
            )
        outcome = self._add_outcome(
            session,
            action.id,
            "Replay eval completed from Discord command.",
            {"replay_run_ids": [run.id for run in runs]},
        )
        return DiscordCommandResult(
            True,
            clip_discord_text(
                "replay summary\n" + bullet_lines(run_lines, empty="- no runs")
            ),
            action_id=action.id,
            outcome_id=outcome.id,
            post_channel_role="agent_eval",
        )

    def _cmd_feedback(
        self, session: Session, context: DiscordCommandContext
    ) -> DiscordCommandResult:
        target_id = str(context.options.get("target_id") or "")
        feedback_type = str(context.options.get("type") or "")
        note = str(context.options.get("note") or "")
        if feedback_type not in {"positive", "negative", "correction", "noise", "too_much", "useful"}:
            return DiscordCommandResult(False, "feedback type is invalid.")
        action = self._add_action(
            session,
            "discord_feedback",
            f"Discord feedback for {target_id} recorded as outcome evidence.",
            {
                "source": "discord_command",
                "command": "feedback",
                "target_id": target_id,
                "feedback_type": feedback_type,
                "note": note,
                "discord_user_id": context.user_id,
                "discord_channel_id": context.channel_id,
            },
            external_effect="feedback",
        )
        outcome = self._add_outcome(
            session,
            action.id,
            f"Feedback {feedback_type} recorded for {target_id}.",
            {"feedback_type": feedback_type, "target_id": target_id},
            user_feedback=note,
        )
        if feedback_type == "correction" and note.strip():
            raw_event = persist_raw_event(
                session,
                RawEventInput(
                    source_type="discord_command",
                    event_type="feedback_correction",
                    payload={
                        "source": "discord_command",
                        "command": "feedback",
                        "target_id": target_id,
                        "feedback_type": feedback_type,
                        "discord_user_id": context.user_id,
                        "discord_channel_id": context.channel_id,
                    },
                    content_text=note,
                    happened_at=context.created_at or now_utc(),
                ),
            )
            observations = self._create_observations_from_raw_event(session, raw_event)
            outcome.effect_on_attention_policy_json = json_dumps(
                {
                    "feedback_type": feedback_type,
                    "target_id": target_id,
                    "raw_event_id": raw_event.id,
                    "observation_ids": [obs.id for obs in observations],
                }
            )
        update_policy_from_outcomes(session, [outcome])
        return DiscordCommandResult(True, f"feedback recorded: outcome_{outcome.id}", action.id, outcome.id)

    def _cmd_inject(
        self, session: Session, context: DiscordCommandContext
    ) -> DiscordCommandResult:
        note = str(context.options.get("note") or "").strip()
        if not note:
            return DiscordCommandResult(False, "inject note is required.")
        if looks_sensitive_text(note):
            return DiscordCommandResult(False, "inject note looks like it may contain a secret.")
        raw_event = persist_raw_event(
            session,
            RawEventInput(
                source_type="discord_command",
                event_type="inject",
                payload={
                    "source": "discord_command",
                    "command": "inject",
                    "discord_user_id": context.user_id,
                    "discord_channel_id": context.channel_id,
                    "discord_interaction_id": context.interaction_id,
                    "created_at": (context.created_at or now_utc()).isoformat(),
                },
                content_text=note,
                happened_at=context.created_at or now_utc(),
            ),
        )
        observations = self._create_observations_from_raw_event(session, raw_event)
        action = self._add_action(
            session,
            "discord_command_inject",
            "Discord /inject created an explicit raw_event.",
            {
                "raw_event_id": raw_event.id,
                "observation_ids": [obs.id for obs in observations],
                "discord_user_id": context.user_id,
            },
            external_effect="raw_event",
        )
        outcome = self._add_outcome(
            session,
            action.id,
            "Explicit Discord injection persisted as raw_event.",
            {"raw_event_id": raw_event.id, "observation_ids": [obs.id for obs in observations]},
        )
        return DiscordCommandResult(
            True,
            f"injected raw_event_{raw_event.id}",
            action.id,
            outcome.id,
            post_channel_role="agent_trace",
        )

    def _cmd_mute(
        self, session: Session, context: DiscordCommandContext
    ) -> DiscordCommandResult:
        duration_text = str(context.options.get("duration") or "1h")
        try:
            duration = _parse_duration(duration_text)
        except ValueError as exc:
            return DiscordCommandResult(False, str(exc))
        if duration.total_seconds() <= 0:
            mute_until = None
            rationale = "Discord /mute cleared autonomous posting mute."
        else:
            mute_until = now_utc() + duration
            rationale = "Discord /mute temporarily disabled autonomous posting."
        action = self._add_action(
            session,
            "discord_mute",
            rationale,
            {
                "source": "discord_command",
                "command": "mute",
                "discord_user_id": context.user_id,
                "duration": duration_text,
                "mute_until": mute_until.isoformat() if mute_until else None,
                "muted": mute_until is not None,
            },
            external_effect="discord_runtime",
        )
        outcome = self._add_outcome(
            session,
            action.id,
            "Autonomous posting mute updated.",
            {"mute_until": mute_until.isoformat() if mute_until else None},
        )
        message = f"mute_until: {mute_until.isoformat() if mute_until else 'off'}"
        return DiscordCommandResult(True, message, action.id, outcome.id)

    def _cmd_mode(
        self, session: Session, context: DiscordCommandContext
    ) -> DiscordCommandResult:
        if not self.discord.allow_mode_command:
            return DiscordCommandResult(False, "/mode is disabled by config.")
        if context.user_id not in self.discord.admin_user_ids:
            return DiscordCommandResult(False, "/mode requires configured admin user.")
        requested_raw = str(context.options.get("mode") or "")
        try:
            requested = DiscordRuntimeMode.parse(requested_raw)
        except ValueError as exc:
            return DiscordCommandResult(False, str(exc))
        if requested.rank > self.discord.max_mode.rank:
            return DiscordCommandResult(
                False,
                f"requested mode exceeds AGENT_DISCORD_MAX_MODE={self.discord.max_mode.value}",
            )
        action = self._add_action(
            session,
            "discord_mode_change",
            "Discord runtime mode changed through restricted command.",
            {
                "source": "discord_command",
                "command": "mode",
                "discord_user_id": context.user_id,
                "mode": requested.value,
            },
            external_effect="discord_runtime",
        )
        outcome = self._add_outcome(
            session,
            action.id,
            f"Runtime mode set to {requested.value}.",
            {"mode": requested.value},
        )
        return DiscordCommandResult(True, f"mode: {requested.value}", action.id, outcome.id, "agent_admin")

    def current_mute_until(self, session: Session) -> datetime | None:
        action = session.scalar(
            select(Action)
            .where(Action.action_type == "discord_mute")
            .where(Action.status == "completed")
            .order_by(Action.created_at.desc(), Action.id.desc())
            .limit(1)
        )
        if action is None:
            return None
        payload = json_dict(action.payload_json)
        if not payload.get("muted", False):
            return None
        raw_until = payload.get("mute_until")
        if not raw_until:
            return None
        try:
            until = datetime.fromisoformat(str(raw_until))
        except ValueError:
            return None
        until = _aware_utc(until)
        return until if until > now_utc() else None

    def prepare_trace_post(
        self,
        session: Session,
        channel_role: str,
        content: str,
        *,
        action_type: str = "discord_trace_post",
        rationale: str = "Post compact Discord trace output.",
    ) -> DiscordPostResult:
        return self._prepare_post(
            session,
            channel_role,
            content,
            action_type=action_type,
            rationale=rationale,
            require_autonomous_mode=False,
        )

    def prepare_cycle_trace_posts(
        self,
        session: Session,
        cycle_type: str,
        result: dict[str, Any],
        *,
        trigger: str,
    ) -> list[DiscordPostResult]:
        normalized = cycle_type.strip().lower()
        base_role = TRACE_CHANNEL_BY_CYCLE.get(normalized, "agent_trace")
        content = self.render_cycle_summary(
            session, normalized, result, trigger=trigger
        )
        posts = [
            self.prepare_trace_post(
                session,
                base_role,
                content,
                action_type=f"discord_{normalized}_trace_post",
                rationale=f"Post compact {normalized} cycle summary to Discord.",
            )
        ]
        if normalized == "wake":
            if result.get("concerns", 0):
                posts.append(
                    self.prepare_trace_post(
                        session,
                        "agent_concerns",
                        self.render_recent_concern_summary(session, trigger=trigger),
                        action_type="discord_concern_trace_post",
                        rationale="Post compact concern lifecycle update to Discord.",
                    )
                )
            if result.get("attention_policy_version"):
                posts.append(
                    self.prepare_trace_post(
                        session,
                        "agent_policy",
                        self.render_recent_policy_summary(session, trigger=trigger),
                        action_type="discord_policy_trace_post",
                        rationale="Post compact attention policy update to Discord.",
                    )
                )
        return posts

    def render_cycle_summary(
        self,
        session: Session,
        cycle_type: str,
        result: dict[str, Any],
        *,
        trigger: str,
    ) -> str:
        mode = self.effective_mode(session)
        latest_actions = session.scalars(
            select(Action).order_by(Action.created_at.desc(), Action.id.desc()).limit(5)
        ).all()
        lines = [
            f"{cycle_type}_cycle",
            f"Mode: {mode.value}",
            f"Trigger: {trigger}",
            f"Result: {render_mapping(result, max_items=12)}",
            "Actions:",
            bullet_lines(
                [
                    f"act_{action.id} {action.action_type} [{action.status}]"
                    for action in latest_actions
                ]
            ),
        ]
        return clip_discord_text("\n".join(lines))

    def render_recent_concern_summary(self, session: Session, *, trigger: str) -> str:
        events = session.scalars(
            select(ConcernEvent)
            .order_by(ConcernEvent.created_at.desc(), ConcernEvent.id.desc())
            .limit(8)
        ).all()
        return clip_discord_text(
            "\n".join(
                [
                    "concern updates",
                    f"Trigger: {trigger}",
                    bullet_lines(
                        [
                            f"evt_{event.id} con_{event.concern_id} {event.event_type}: {event.reason}"
                            for event in events
                        ]
                    ),
                ]
            )
        )

    def render_recent_policy_summary(self, session: Session, *, trigger: str) -> str:
        events = session.scalars(
            select(AttentionPolicyEvent)
            .order_by(AttentionPolicyEvent.created_at.desc(), AttentionPolicyEvent.id.desc())
            .limit(8)
        ).all()
        policy = session.scalar(
            select(AttentionPolicy).order_by(AttentionPolicy.version.desc()).limit(1)
        )
        lines = [
            "attention_policy updates",
            f"Trigger: {trigger}",
            f"Policy: v{policy.version}" if policy else "Policy: none",
            bullet_lines(
                [
                    f"ape_{event.id} {event.target_field}: {event.reason}"
                    for event in events
                ]
            ),
        ]
        return clip_discord_text("\n".join(lines))

    def prepare_autonomous_post(
        self, session: Session, channel_role: str, content: str, *, reason: str
    ) -> DiscordPostResult:
        return self._prepare_post(
            session,
            channel_role,
            content,
            action_type="discord_autonomous_post",
            rationale=reason,
            require_autonomous_mode=True,
        )

    def _prepare_post(
        self,
        session: Session,
        channel_role: str,
        content: str,
        *,
        action_type: str,
        rationale: str,
        require_autonomous_mode: bool,
    ) -> DiscordPostResult:
        if not self.discord.enabled:
            return DiscordPostResult(False, "discord_disabled", "")
        mode = self.effective_mode(session)
        if require_autonomous_mode and not mode.can_post_autonomously:
            return DiscordPostResult(False, f"mode_{mode.value}_cannot_post_autonomously", "")
        channel = self.discord.channel_for_role(channel_role)
        if channel is None or not channel.configured:
            return DiscordPostResult(False, "channel_not_configured", "")
        if not channel.bot_output_allowed:
            return DiscordPostResult(False, "bot_output_not_allowed", "")
        if require_autonomous_mode:
            if channel_role not in self.discord.autonomous_output_roles:
                return DiscordPostResult(False, "channel_not_in_autonomous_allowlist", "")
            mute_until = self.current_mute_until(session)
            if mute_until is not None:
                return DiscordPostResult(False, f"muted_until_{mute_until.isoformat()}", "")
            wait = self._autonomous_rate_limit_remaining(session)
            if wait > 0:
                return DiscordPostResult(False, f"rate_limited_{wait}s", "")
        if looks_sensitive_text(content):
            return DiscordPostResult(False, "content_looks_sensitive", "")
        rendered = clip_discord_text(content)
        action = self._add_action(
            session,
            action_type,
            rationale,
            {
                "source": "discord_autonomous_post" if require_autonomous_mode else "discord_bot_trace",
                "discord_channel_id": channel.id,
                "discord_channel_role": channel.role,
                "content_text": rendered,
            },
            external_effect="discord",
        )
        outcome = self._add_outcome(
            session,
            action.id,
            "Discord post prepared for adapter delivery.",
            {"discord_channel_id": channel.id, "discord_channel_role": channel.role},
        )
        return DiscordPostResult(True, "allowed", rendered, channel.id, action.id, outcome.id)

    def record_post_delivery(
        self,
        session: Session,
        action_id: int,
        *,
        discord_message_id: str,
    ) -> Action | None:
        action = session.get(Action, action_id)
        if action is None or not action.action_type.startswith("discord_"):
            return None
        payload = json_dict(action.payload_json)
        payload["discord_message_id"] = str(discord_message_id)
        action.payload_json = json_dumps(payload)
        self._add_outcome(
            session,
            action.id,
            "Discord post delivered and message ID recorded.",
            {"discord_message_id": str(discord_message_id)},
        )
        session.flush()
        return action

    def _autonomous_rate_limit_remaining(self, session: Session) -> int:
        last = session.scalar(
            select(Action)
            .where(Action.action_type == "discord_autonomous_post")
            .where(Action.status == "completed")
            .order_by(Action.created_at.desc(), Action.id.desc())
            .limit(1)
        )
        if last is None:
            return 0
        elapsed = (now_utc() - _aware_utc(last.created_at)).total_seconds()
        remaining = self.discord.autonomous_rate_limit_seconds - int(elapsed)
        return max(0, remaining)

    def _add_action(
        self,
        session: Session,
        action_type: str,
        rationale: str,
        payload: dict[str, Any],
        *,
        external_effect: str,
    ) -> Action:
        action = Action(
            action_type=action_type,
            rationale=rationale,
            related_concern_ids_json=json_dumps([]),
            input_probe_ids_json=json_dumps([]),
            payload_json=json_dumps(payload),
            external_effect=external_effect,
            status="completed",
        )
        session.add(action)
        session.flush()
        return action

    def _add_outcome(
        self,
        session: Session,
        action_id: int,
        observed_result: str,
        effect: dict[str, Any],
        *,
        user_feedback: str = "",
    ) -> Outcome:
        outcome = Outcome(
            action_id=action_id,
            observed_result=observed_result,
            user_feedback=user_feedback,
            effect_on_concerns_json=json_dumps(effect.get("concerns", {})),
            effect_on_attention_policy_json=json_dumps(effect),
        )
        session.add(outcome)
        session.flush()
        return outcome

    def core_profile_snapshot(self, session: Session) -> str | None:
        profile = session.scalar(select(CoreProfile).order_by(CoreProfile.id).limit(1))
        return profile.content if profile else None
