"""Optional live Discord bot runner.

The business logic lives in :mod:`app.runtime.discord_controller`; this module is
only the discord.py I/O shell.
"""

from __future__ import annotations

from datetime import timezone
import os
from typing import Any

from app.config import Settings
from app.db.init_db import init_database
from app.db.session import session_scope
from app.runtime.discord_controller import (
    DiscordAttachmentInput,
    DiscordCommandContext,
    DiscordCommandResult,
    DiscordController,
    DiscordMessageInput,
    DiscordReactionInput,
)


async def _build_attachment_input(
    attachment: Any, settings: Settings
) -> DiscordAttachmentInput:
    content_text: str | None = None
    if settings.discord.attachment_ingest_enabled:
        content_type = attachment.content_type or ""
        if (
            attachment.size <= settings.discord.max_attachment_bytes
            and content_type in settings.discord.allowed_attachment_content_types
        ):
            data = await attachment.read()
            try:
                content_text = data.decode("utf-8")
            except UnicodeDecodeError:
                content_text = None
    return DiscordAttachmentInput(
        filename=attachment.filename,
        content_type=attachment.content_type,
        size=int(attachment.size),
        content_text=content_text,
    )


def run_discord_bot(settings: Settings, *, dry_run: bool = False) -> int:
    try:
        import discord
        from discord import app_commands
        from discord.ext import commands
    except ImportError as exc:  # pragma: no cover - exercised only without dependency.
        raise RuntimeError("discord.py is required for `discord run`.") from exc

    if not settings.discord.enabled and not dry_run:
        raise RuntimeError("Set AGENT_DISCORD_ENABLED=true before running the bot.")
    token = os.environ.get(settings.discord.token_env_var, "").strip()
    if not token and not dry_run:
        raise RuntimeError(
            f"Set {settings.discord.token_env_var} before running the Discord bot."
        )

    if not dry_run:
        init_database(settings)
    intents = discord.Intents.default()
    intents.guilds = True
    intents.messages = True
    intents.message_content = settings.discord.max_mode.can_ingest
    bot = commands.Bot(command_prefix="!", intents=intents)
    controller = DiscordController(settings)

    def command_context(interaction: discord.Interaction, **options: Any) -> DiscordCommandContext:
        return DiscordCommandContext(
            command_name=interaction.command.name if interaction.command else "",
            channel_id=str(interaction.channel_id) if interaction.channel_id else None,
            user_id=str(interaction.user.id),
            options=options,
            interaction_id=str(interaction.id),
            created_at=interaction.created_at.astimezone(timezone.utc),
        )

    async def maybe_post_role(result: DiscordCommandResult) -> None:
        if not result.post_channel_role:
            return
        channel_config = settings.discord.channel_for_role(result.post_channel_role)
        if not channel_config or not channel_config.id or not channel_config.bot_output_allowed:
            return
        channel = bot.get_channel(int(channel_config.id)) or await bot.fetch_channel(
            int(channel_config.id)
        )
        sent = await channel.send(result.message)
        if result.action_id is not None:
            with session_scope(settings) as session:
                controller.record_post_delivery(
                    session,
                    result.action_id,
                    discord_message_id=str(sent.id),
                )

    async def respond(interaction: discord.Interaction, result: DiscordCommandResult) -> None:
        message = result.message
        if not interaction.response.is_done():
            await interaction.response.send_message(message, ephemeral=True)
        else:
            await interaction.followup.send(message, ephemeral=True)
        await maybe_post_role(result)

    @bot.event
    async def on_ready() -> None:
        guild = (
            discord.Object(id=int(settings.discord.guild_id))
            if settings.discord.guild_id
            else None
        )
        if guild:
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
        else:
            synced = await bot.tree.sync()
        print(
            "discord bot ready: "
            f"user={bot.user} mode={settings.discord.mode.value} "
            f"max_mode={settings.discord.max_mode.value} commands={len(synced)}"
        )

    @bot.event
    async def on_message(message: discord.Message) -> None:
        attachments = [
            await _build_attachment_input(attachment, settings)
            for attachment in message.attachments
        ]
        payload = DiscordMessageInput(
            message_id=str(message.id),
            channel_id=str(message.channel.id),
            author_id=str(message.author.id),
            content_text=message.content or "",
            created_at=message.created_at.astimezone(timezone.utc),
            author_is_bot=bool(message.author.bot),
            author_is_system=bool(getattr(message, "is_system", lambda: False)()),
            thread_id=str(message.channel.id)
            if isinstance(message.channel, discord.Thread)
            else None,
            parent_message_id=str(message.reference.message_id)
            if message.reference and message.reference.message_id
            else None,
            attachments=attachments,
        )
        with session_scope(settings) as session:
            result = controller.ingest_message(session, payload)
        if result.ingested:
            print(f"discord message ingested: raw_event_id={result.raw_event_id}")

    @bot.event
    async def on_raw_reaction_add(payload: discord.RawReactionActionEvent) -> None:
        if bot.user and payload.user_id == bot.user.id:
            return
        reaction = DiscordReactionInput(
            message_id=str(payload.message_id),
            channel_id=str(payload.channel_id),
            user_id=str(payload.user_id),
            emoji=str(payload.emoji),
            created_at=discord.utils.utcnow(),
            user_is_bot=bool(payload.member.bot) if payload.member else False,
        )
        with session_scope(settings) as session:
            result = controller.record_reaction(session, reaction)
        if result.recorded:
            print(f"discord reaction recorded: outcome_id={result.outcome_id}")

    @bot.tree.command(name="ping", description="Read-only Discord adapter ping.")
    async def ping(interaction: discord.Interaction) -> None:
        with session_scope(settings) as session:
            result = controller.dispatch_command(session, command_context(interaction))
        await respond(interaction, result)

    @bot.tree.command(name="status", description="Show adapter/runtime status.")
    async def status(interaction: discord.Interaction) -> None:
        with session_scope(settings) as session:
            result = controller.dispatch_command(session, command_context(interaction))
        await respond(interaction, result)

    @bot.tree.command(name="wake", description="Request a bounded wake cycle.")
    async def wake(interaction: discord.Interaction, reason: str = "discord_manual") -> None:
        await interaction.response.defer(ephemeral=True)
        with session_scope(settings) as session:
            result = controller.dispatch_command(
                session, command_context(interaction, reason=reason)
            )
        await respond(interaction, result)

    @bot.tree.command(name="concerns", description="Show active concern summary.")
    async def concerns(interaction: discord.Interaction) -> None:
        with session_scope(settings) as session:
            result = controller.dispatch_command(session, command_context(interaction))
        await respond(interaction, result)

    @bot.tree.command(name="concern", description="Show one concern.")
    async def concern(interaction: discord.Interaction, id: int) -> None:
        with session_scope(settings) as session:
            result = controller.dispatch_command(session, command_context(interaction, id=id))
        await respond(interaction, result)

    @bot.tree.command(name="policy", description="Show current attention policy.")
    async def policy(interaction: discord.Interaction) -> None:
        with session_scope(settings) as session:
            result = controller.dispatch_command(session, command_context(interaction))
        await respond(interaction, result)

    @bot.tree.command(name="trace", description="Show compact trace summary.")
    async def trace(interaction: discord.Interaction, run_id: str = "latest") -> None:
        with session_scope(settings) as session:
            result = controller.dispatch_command(
                session, command_context(interaction, run_id=run_id)
            )
        await respond(interaction, result)

    @bot.tree.command(name="replay", description="Run replay eval.")
    async def replay(interaction: discord.Interaction, prompt_id: int | None = None) -> None:
        await interaction.response.defer(ephemeral=True)
        with session_scope(settings) as session:
            result = controller.dispatch_command(
                session, command_context(interaction, prompt_id=prompt_id)
            )
        await respond(interaction, result)

    @bot.tree.command(name="feedback", description="Record feedback as outcome evidence.")
    @app_commands.rename(feedback_type="type")
    async def feedback(
        interaction: discord.Interaction,
        target_id: str,
        feedback_type: str,
        note: str = "",
    ) -> None:
        with session_scope(settings) as session:
            result = controller.dispatch_command(
                session,
                command_context(
                    interaction, target_id=target_id, type=feedback_type, note=note
                ),
            )
        await respond(interaction, result)

    @bot.tree.command(name="inject", description="Create an explicit Discord raw_event.")
    async def inject(interaction: discord.Interaction, note: str) -> None:
        with session_scope(settings) as session:
            result = controller.dispatch_command(
                session, command_context(interaction, note=note)
            )
        await respond(interaction, result)

    @bot.tree.command(name="mute", description="Mute autonomous posting for a duration.")
    async def mute(interaction: discord.Interaction, duration: str = "1h") -> None:
        with session_scope(settings) as session:
            result = controller.dispatch_command(
                session, command_context(interaction, duration=duration)
            )
        await respond(interaction, result)

    @bot.tree.command(name="mode", description="Restricted runtime mode change.")
    async def mode(interaction: discord.Interaction, mode: str) -> None:
        with session_scope(settings) as session:
            result = controller.dispatch_command(
                session, command_context(interaction, mode=mode)
            )
        await respond(interaction, result)

    if dry_run:
        command_names = sorted(command.name for command in bot.tree.get_commands())
        print(
            "discord bot dry-run: "
            f"mode={settings.discord.mode.value} "
            f"max_mode={settings.discord.max_mode.value} "
            f"message_content_intent={intents.message_content} "
            f"commands={','.join(command_names)}"
        )
        return 0

    bot.run(token)
    return 0
