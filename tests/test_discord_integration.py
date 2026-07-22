from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.adapters.discord_config import (
    DiscordChannelConfig,
    DiscordSettings,
    default_channels,
    diagnose_discord_settings,
)
from app.adapters.discord_bot import run_discord_bot
from app.cli.commands import cmd_discord_doctor
from app.db.json_utils import json_loads
from app.db.models import (
    Action,
    AttentionPolicyEvent,
    Concern,
    CoreProfile,
    Observation,
    Outcome,
    RawEvent,
)
from app.runtime.discord_controller import (
    DiscordAttachmentInput,
    DiscordCommandContext,
    DiscordController,
    DiscordMessageInput,
    DiscordReactionInput,
)
from app.runtime.modes import DiscordRuntimeMode
from app.runtime.wake_cycle import run_wake_cycle


def _channels() -> dict[str, DiscordChannelConfig]:
    channels = default_channels()
    channels["agent_chat"] = DiscordChannelConfig(
        role="agent_chat", id="100", ingestable=True, bot_output_allowed=True
    )
    channels["agent_inbox"] = DiscordChannelConfig(
        role="agent_inbox", id="101", ingestable=True, bot_output_allowed=False
    )
    channels["agent_trace"] = DiscordChannelConfig(
        role="agent_trace", id="200", ingestable=False, bot_output_allowed=True
    )
    channels["agent_concerns"] = DiscordChannelConfig(
        role="agent_concerns", id="201", ingestable=False, bot_output_allowed=True
    )
    channels["agent_policy"] = DiscordChannelConfig(
        role="agent_policy", id="202", ingestable=False, bot_output_allowed=True
    )
    channels["agent_eval"] = DiscordChannelConfig(
        role="agent_eval", id="203", ingestable=False, bot_output_allowed=True
    )
    channels["agent_admin"] = DiscordChannelConfig(
        role="agent_admin", id="300", ingestable=False, bot_output_allowed=True
    )
    return channels


def _discord_settings(
    settings,
    mode: DiscordRuntimeMode,
    *,
    max_mode: DiscordRuntimeMode | None = None,
    allow_mode_command: bool = False,
    attachment_ingest_enabled: bool = False,
    create_observations: bool = False,
    rate_limit_seconds: int = 3600,
):
    return replace(
        settings,
        discord=DiscordSettings(
            enabled=True,
            mode=mode,
            max_mode=max_mode or mode,
            guild_id="999",
            token_env_var="DISCORD_BOT_TOKEN",
            channels=_channels(),
            admin_user_ids={"42"},
            allow_mode_command=allow_mode_command,
            create_observations_from_ingest=create_observations,
            attachment_ingest_enabled=attachment_ingest_enabled,
            autonomous_rate_limit_seconds=rate_limit_seconds,
        ),
    )


def _message(
    *,
    channel_id: str = "100",
    author_is_bot: bool = False,
    attachments: list[DiscordAttachmentInput] | None = None,
) -> DiscordMessageInput:
    return DiscordMessageInput(
        message_id="555",
        channel_id=channel_id,
        author_id="7",
        content_text="Discord user message about agent trace risk and policy uncertainty.",
        created_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
        author_is_bot=author_is_bot,
        attachments=attachments or [],
    )


def test_ac001_inv001_observe_only_does_not_ingest_messages(seeded_session, settings):
    settings = _discord_settings(settings, DiscordRuntimeMode.OBSERVE_ONLY)
    controller = DiscordController(settings)

    result = controller.ingest_message(seeded_session, _message())

    assert result.ingested is False
    assert result.reason == "mode_observe_only_does_not_ingest"
    assert seeded_session.scalar(select(func.count(RawEvent.id))) == 0
    assert "Mode: observe_only" in controller.render_status(seeded_session)


def test_ac002_ac003_inv002_rejects_bot_and_trace_channel_messages(
    seeded_session, settings
):
    settings = _discord_settings(settings, DiscordRuntimeMode.INGEST_ENABLED)
    controller = DiscordController(settings)

    bot_result = controller.ingest_message(seeded_session, _message(author_is_bot=True))
    trace_result = controller.ingest_message(
        seeded_session, _message(channel_id="200", author_is_bot=False)
    )

    assert bot_result.ingested is False
    assert bot_result.reason == "bot_author_not_ingestable"
    assert trace_result.ingested is False
    assert trace_result.reason == "channel_role_agent_trace_not_ingestable"
    assert seeded_session.scalar(select(func.count(RawEvent.id))) == 0


def test_ac004_inv003_ingest_enabled_creates_raw_event_with_metadata(
    seeded_session, settings
):
    settings = _discord_settings(
        settings,
        DiscordRuntimeMode.INGEST_ENABLED,
        attachment_ingest_enabled=True,
        create_observations=True,
    )
    controller = DiscordController(settings)
    attachment = DiscordAttachmentInput(
        filename="note.md",
        content_type="text/markdown",
        size=47,
        content_text="Attachment note about concern boundary.",
    )

    result = controller.ingest_message(
        seeded_session, _message(attachments=[attachment])
    )

    assert result.ingested is True
    assert result.raw_event_id is not None
    assert result.observation_ids
    raw_event = seeded_session.get(RawEvent, result.raw_event_id)
    payload = json_loads(raw_event.payload_json, {})
    assert payload["source"] == "discord_user_message"
    assert payload["author_type"] == "user"
    assert payload["discord_message_id"] == "555"
    assert payload["discord_channel_id"] == "100"
    assert payload["discord_channel_role"] == "agent_chat"
    assert payload["ingestable"] is True
    assert payload["attachments"][0]["ingested"] is True
    assert "Attachment note" in raw_event.content_text
    assert seeded_session.scalar(select(func.count(Observation.id))) >= 1


def test_ac006_inv005_autonomous_post_requires_mode_allowlist_rate_and_mute(
    seeded_session, settings
):
    settings = _discord_settings(
        settings,
        DiscordRuntimeMode.AUTONOMOUS_POSTING_ENABLED,
        rate_limit_seconds=3600,
    )
    controller = DiscordController(settings)

    first = controller.prepare_autonomous_post(
        seeded_session,
        "agent_chat",
        "Daily digest: active concerns changed.",
        reason="daily digest",
    )
    second = controller.prepare_autonomous_post(
        seeded_session,
        "agent_chat",
        "Another digest too soon.",
        reason="daily digest",
    )
    inbox = controller.prepare_autonomous_post(
        seeded_session,
        "agent_inbox",
        "Should not be posted here.",
        reason="wrong channel",
    )

    assert first.allowed is True
    assert first.action_id is not None
    assert second.allowed is False
    assert second.reason.startswith("rate_limited_")
    assert inbox.allowed is False
    assert inbox.reason == "bot_output_not_allowed"


def test_ac006_inv005_mute_blocks_autonomous_post(seeded_session, settings):
    settings = _discord_settings(
        settings,
        DiscordRuntimeMode.AUTONOMOUS_POSTING_ENABLED,
        rate_limit_seconds=0,
    )
    controller = DiscordController(settings)
    mute_result = controller.dispatch_command(
        seeded_session,
        DiscordCommandContext(
            command_name="mute",
            channel_id="300",
            user_id="42",
            options={"duration": "1h"},
        ),
    )

    post = controller.prepare_autonomous_post(
        seeded_session,
        "agent_chat",
        "Digest while muted.",
        reason="manual test",
    )

    assert mute_result.ok is True
    assert post.allowed is False
    assert post.reason.startswith("muted_until_")


def test_ac007_inv007_unsafe_attachment_and_sensitive_post_are_rejected(
    seeded_session, settings
):
    settings = _discord_settings(
        settings,
        DiscordRuntimeMode.INGEST_ENABLED,
        attachment_ingest_enabled=True,
    )
    controller = DiscordController(settings)
    attachment = DiscordAttachmentInput(
        filename=".env",
        content_type="text/plain",
        size=12,
        content_text="TOKEN=secret",
    )

    result = controller.ingest_message(
        seeded_session, _message(attachments=[attachment])
    )

    raw_event = seeded_session.get(RawEvent, result.raw_event_id)
    payload = json_loads(raw_event.payload_json, {})
    assert payload["attachments"][0]["ingested"] is False
    assert payload["attachments"][0]["rejected_reason"] == "secret_like_filename"

    autonomous_settings = _discord_settings(
        settings,
        DiscordRuntimeMode.AUTONOMOUS_POSTING_ENABLED,
        rate_limit_seconds=0,
    )
    sensitive = DiscordController(autonomous_settings).prepare_autonomous_post(
        seeded_session,
        "agent_chat",
        "TOKEN=do-not-post",
        reason="secret check",
    )
    assert sensitive.allowed is False
    assert sensitive.reason == "content_looks_sensitive"


def test_ac005_inv004_inv006_command_dispatch_traces_mutations_and_keeps_core_locked(
    seeded_session, settings
):
    settings = _discord_settings(settings, DiscordRuntimeMode.COMMAND_ENABLED)
    controller = DiscordController(settings)
    before = seeded_session.scalar(select(CoreProfile).limit(1)).content

    wake_result = controller.dispatch_command(
        seeded_session,
        DiscordCommandContext(
            command_name="wake",
            channel_id="300",
            user_id="42",
            options={"reason": "test"},
        ),
    )
    feedback_result = controller.dispatch_command(
        seeded_session,
        DiscordCommandContext(
            command_name="feedback",
            channel_id="300",
            user_id="42",
            options={
                "target_id": "act_1",
                "type": "useful",
                "note": "This was useful.",
            },
        ),
    )

    after = seeded_session.scalar(select(CoreProfile).limit(1)).content
    assert wake_result.ok is True
    assert wake_result.action_id is not None
    assert feedback_result.ok is True
    assert seeded_session.scalar(
        select(func.count(Action.id)).where(Action.action_type == "discord_command_wake")
    ) == 1
    assert seeded_session.scalar(
        select(func.count(Action.id)).where(Action.action_type == "discord_feedback")
    ) == 1
    assert seeded_session.scalar(select(func.count(Outcome.id))) >= 2
    assert after == before


def test_inject_always_runs_observation_pipeline(seeded_session, settings):
    settings = _discord_settings(settings, DiscordRuntimeMode.COMMAND_ENABLED)
    controller = DiscordController(settings)

    result = controller.dispatch_command(
        seeded_session,
        DiscordCommandContext(
            command_name="inject",
            channel_id="300",
            user_id="42",
            options={"note": "Injected correction about agent concern policy risk."},
        ),
    )

    assert result.ok is True
    raw_event = seeded_session.scalar(
        select(RawEvent).where(RawEvent.source_type == "discord_command")
    )
    assert raw_event is not None
    assert seeded_session.scalar(
        select(func.count(Observation.id)).where(Observation.source_event_id == raw_event.id)
    ) == 1
    action = seeded_session.get(Action, result.action_id)
    payload = json_loads(action.payload_json, {})
    assert payload["observation_ids"]


def test_feedback_correction_flows_through_review_without_core_profile_change(
    seeded_session, settings
):
    settings = _discord_settings(settings, DiscordRuntimeMode.COMMAND_ENABLED)
    controller = DiscordController(settings)
    before = seeded_session.scalar(select(CoreProfile).limit(1)).content

    result = controller.dispatch_command(
        seeded_session,
        DiscordCommandContext(
            command_name="feedback",
            channel_id="300",
            user_id="42",
            options={
                "target_id": "trace_1",
                "type": "correction",
                "note": "Correction: Discord feedback should influence policy carefully.",
            },
        ),
    )

    outcome = seeded_session.get(Outcome, result.outcome_id)
    effect = json_loads(outcome.effect_on_attention_policy_json, {})
    after = seeded_session.scalar(select(CoreProfile).limit(1)).content
    assert result.ok is True
    assert effect["raw_event_id"]
    assert effect["observation_ids"]
    assert after == before


def test_feedback_updates_attention_policy_with_outcome_evidence(seeded_session, settings):
    settings = _discord_settings(settings, DiscordRuntimeMode.COMMAND_ENABLED)
    controller = DiscordController(settings)

    result = controller.dispatch_command(
        seeded_session,
        DiscordCommandContext(
            command_name="feedback",
            channel_id="300",
            user_id="42",
            options={
                "target_id": "trace_1",
                "type": "too_much",
                "note": "Too much internal state in the response.",
            },
        ),
    )

    event = seeded_session.scalar(
        select(AttentionPolicyEvent)
        .where(AttentionPolicyEvent.evidence_outcome_ids_json != "[]")
        .order_by(AttentionPolicyEvent.id.desc())
        .limit(1)
    )
    assert result.ok is True
    assert event is not None
    assert str(result.outcome_id) in event.evidence_outcome_ids_json
    assert event.target_field == "response_preferences.mention_internal_state"


def test_concern_detail_includes_related_observations_and_actions(seeded_session, settings):
    settings = _discord_settings(settings, DiscordRuntimeMode.COMMAND_ENABLED)
    controller = DiscordController(settings)
    controller.dispatch_command(
        seeded_session,
        DiscordCommandContext(
            command_name="inject",
            channel_id="300",
            user_id="42",
            options={"note": "Concern detail should show related trace policy risk."},
        ),
    )
    concern = seeded_session.scalar(select(Concern).order_by(Concern.id.desc()).limit(1))

    result = controller.dispatch_command(
        seeded_session,
        DiscordCommandContext(
            command_name="concern",
            channel_id="300",
            user_id="42",
            options={"id": str(concern.id)},
        ),
    )

    assert result.ok is True
    assert "related observations:" in result.message
    assert "obs_" in result.message
    assert "related actions:" in result.message


def test_replay_summary_includes_selected_state(seeded_session, settings):
    settings = _discord_settings(settings, DiscordRuntimeMode.COMMAND_ENABLED)
    controller = DiscordController(settings)

    result = controller.dispatch_command(
        seeded_session,
        DiscordCommandContext(
            command_name="replay",
            channel_id="300",
            user_id="42",
            options={"prompt_id": "1"},
        ),
    )

    assert result.ok is True
    assert "replay summary" in result.message
    assert "concerns=" in result.message
    assert "memories=" in result.message
    assert "policy=" in result.message


def test_observe_only_can_prepare_cycle_trace_posts_without_ingesting_bot_output(
    seeded_session, settings
):
    settings = _discord_settings(settings, DiscordRuntimeMode.OBSERVE_ONLY)
    controller = DiscordController(settings)
    wake_result = run_wake_cycle(seeded_session, settings, reason="scheduled")

    posts = controller.prepare_cycle_trace_posts(
        seeded_session, "wake", wake_result, trigger="scheduled"
    )
    trace_actions = seeded_session.scalars(
        select(Action).where(Action.action_type.like("discord_%_trace_post"))
    ).all()

    assert len(posts) >= 1
    assert all(post.allowed for post in posts)
    assert {post.channel_id for post in posts} >= {"200"}
    assert any("wake_cycle" in post.message for post in posts)
    assert trace_actions
    assert seeded_session.scalar(
        select(func.count(RawEvent.id)).where(RawEvent.source_type == "discord_bot_trace")
    ) == 0


def test_eval_cycle_trace_posts_to_eval_channel(seeded_session, settings):
    settings = _discord_settings(settings, DiscordRuntimeMode.OBSERVE_ONLY)
    controller = DiscordController(settings)
    result = {"replay_runs": 1, "replay_run_ids": [1]}

    posts = controller.prepare_cycle_trace_posts(
        seeded_session, "replay", result, trigger="manual_eval"
    )

    assert len(posts) == 1
    assert posts[0].allowed is True
    assert posts[0].channel_id == "203"
    assert "replay_cycle" in posts[0].message


def test_user_reply_to_recorded_autonomous_post_becomes_outcome(
    seeded_session, settings
):
    settings = _discord_settings(
        settings,
        DiscordRuntimeMode.AUTONOMOUS_POSTING_ENABLED,
        rate_limit_seconds=0,
    )
    controller = DiscordController(settings)
    post = controller.prepare_autonomous_post(
        seeded_session,
        "agent_chat",
        "Question worth asking.",
        reason="ask user",
    )
    controller.record_post_delivery(
        seeded_session,
        post.action_id,
        discord_message_id="bot-message-1",
    )

    result = controller.ingest_message(
        seeded_session,
        _message(channel_id="100"),
    )
    no_parent_outcomes = seeded_session.scalar(
        select(func.count(Outcome.id)).where(Outcome.user_feedback.like("%Discord user%"))
    )
    reply = controller.ingest_message(
        seeded_session,
        DiscordMessageInput(
            message_id="reply-1",
            channel_id="100",
            author_id="7",
            content_text="Discord user reply to the autonomous question.",
            created_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
            parent_message_id="bot-message-1",
        ),
    )
    outcome = seeded_session.get(Outcome, reply.outcome_id)

    assert result.ingested is True
    assert no_parent_outcomes == 0
    assert reply.ingested is True
    assert reply.outcome_id is not None
    assert outcome.action_id == post.action_id
    assert "autonomous post" in outcome.observed_result


def test_user_reaction_to_recorded_autonomous_post_becomes_outcome(
    seeded_session, settings
):
    settings = _discord_settings(
        settings,
        DiscordRuntimeMode.AUTONOMOUS_POSTING_ENABLED,
        rate_limit_seconds=0,
    )
    controller = DiscordController(settings)
    post = controller.prepare_autonomous_post(
        seeded_session,
        "agent_chat",
        "React if this is useful.",
        reason="ask user",
    )
    controller.record_post_delivery(
        seeded_session,
        post.action_id,
        discord_message_id="bot-message-2",
    )

    result = controller.record_reaction(
        seeded_session,
        DiscordReactionInput(
            message_id="bot-message-2",
            channel_id="100",
            user_id="7",
            emoji="thumbs_up",
            created_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
        ),
    )

    outcome = seeded_session.get(Outcome, result.outcome_id)
    assert result.recorded is True
    assert outcome.action_id == post.action_id
    assert outcome.user_feedback == "reaction:thumbs_up"
    assert "reaction" in outcome.observed_result


def test_reaction_outcome_requires_ingest_enabled_channel(seeded_session, settings):
    settings = _discord_settings(settings, DiscordRuntimeMode.OBSERVE_ONLY)
    controller = DiscordController(settings)

    result = controller.record_reaction(
        seeded_session,
        DiscordReactionInput(
            message_id="bot-message-2",
            channel_id="100",
            user_id="7",
            emoji="thumbs_up",
            created_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
        ),
    )

    assert result.recorded is False
    assert result.reason == "mode_observe_only_does_not_ingest"


def test_mode_command_is_admin_only_and_cannot_exceed_max_mode(seeded_session, settings):
    settings = _discord_settings(
        settings,
        DiscordRuntimeMode.COMMAND_ENABLED,
        max_mode=DiscordRuntimeMode.AUTONOMOUS_POSTING_ENABLED,
        allow_mode_command=True,
    )
    controller = DiscordController(settings)

    rejected_user = controller.dispatch_command(
        seeded_session,
        DiscordCommandContext(
            command_name="mode",
            channel_id="300",
            user_id="7",
            options={"mode": "autonomous_posting_enabled"},
        ),
    )
    accepted = controller.dispatch_command(
        seeded_session,
        DiscordCommandContext(
            command_name="mode",
            channel_id="300",
            user_id="42",
            options={"mode": "autonomous_posting_enabled"},
        ),
    )

    assert rejected_user.ok is False
    assert accepted.ok is True
    assert controller.effective_mode(seeded_session) == DiscordRuntimeMode.AUTONOMOUS_POSTING_ENABLED


def test_live_bot_dry_run_builds_expected_command_tree(settings, capsys):
    settings = _discord_settings(settings, DiscordRuntimeMode.COMMAND_ENABLED)

    exit_code = run_discord_bot(settings, dry_run=True)
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "discord bot dry-run" in output
    assert "message_content_intent=True" in output
    for command in [
        "concern",
        "concerns",
        "feedback",
        "inject",
        "mode",
        "mute",
        "ping",
        "policy",
        "replay",
        "status",
        "trace",
        "wake",
    ]:
        assert command in output


def test_discord_doctor_reports_live_readiness_gaps_without_token_value(settings):
    settings = replace(
        settings,
        discord=DiscordSettings(
            enabled=True,
            mode=DiscordRuntimeMode.INGEST_ENABLED,
            max_mode=DiscordRuntimeMode.INGEST_ENABLED,
            channels=default_channels(),
            token_env_var="DISCORD_BOT_TOKEN",
        ),
    )

    report = diagnose_discord_settings(
        settings.discord,
        env={},
        target_mode=DiscordRuntimeMode.INGEST_ENABLED,
        live_run=True,
    )
    output = "\n".join(report.as_lines())
    codes = {check.code for check in report.checks}

    assert report.ok is False
    assert {"token_missing", "trace_channel_not_ready", "ingest_channel_missing"} <= codes
    assert "DISCORD_BOT_TOKEN" in output
    assert "secret" not in output.lower()


def test_discord_doctor_accepts_ready_autonomous_config_without_printing_token(
    settings,
):
    settings = _discord_settings(
        settings,
        DiscordRuntimeMode.AUTONOMOUS_POSTING_ENABLED,
        max_mode=DiscordRuntimeMode.AUTONOMOUS_POSTING_ENABLED,
        allow_mode_command=True,
    )

    report = diagnose_discord_settings(
        settings.discord,
        env={"DISCORD_BOT_TOKEN": "super-secret-token-value"},
        target_mode=DiscordRuntimeMode.AUTONOMOUS_POSTING_ENABLED,
        live_run=True,
    )
    output = "\n".join(report.as_lines())

    assert report.ok is True
    assert "autonomous_output_ready" in output
    assert "super-secret-token-value" not in output


def test_discord_doctor_cli_returns_nonzero_for_live_blockers(
    settings, capsys, monkeypatch
):
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
    settings = replace(
        settings,
        discord=DiscordSettings(
            enabled=True,
            mode=DiscordRuntimeMode.COMMAND_ENABLED,
            max_mode=DiscordRuntimeMode.COMMAND_ENABLED,
            channels=default_channels(),
            token_env_var="DISCORD_BOT_TOKEN",
        ),
    )

    exit_code = cmd_discord_doctor(settings, "command_enabled", live_run=True)
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "Discord doctor: target_mode=command_enabled live_run=true" in output
    assert "ERROR token_missing" in output
    assert "ERROR command_control_missing" in output
