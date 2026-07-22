"""Minimal Discord command dispatch facade."""

from __future__ import annotations

from app.runtime.discord_controller import (
    ALL_COMMANDS,
    DiscordCommandContext,
    DiscordCommandResult,
    DiscordController,
)

__all__ = [
    "ALL_COMMANDS",
    "DiscordCommandContext",
    "DiscordCommandResult",
    "DiscordController",
]
