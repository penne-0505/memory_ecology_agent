"""Runtime mode helpers for feature-gated adapters."""

from __future__ import annotations

from enum import StrEnum


class DiscordRuntimeMode(StrEnum):
    OBSERVE_ONLY = "observe_only"
    INGEST_ENABLED = "ingest_enabled"
    COMMAND_ENABLED = "command_enabled"
    AUTONOMOUS_POSTING_ENABLED = "autonomous_posting_enabled"

    @classmethod
    def parse(cls, value: str | None) -> "DiscordRuntimeMode":
        normalized = (value or cls.OBSERVE_ONLY.value).strip().lower()
        for mode in cls:
            if mode.value == normalized:
                return mode
        allowed = ", ".join(mode.value for mode in cls)
        raise ValueError(f"unknown Discord runtime mode: {value!r}; expected one of {allowed}")

    @property
    def rank(self) -> int:
        return list(type(self)).index(self)

    def allows(self, capability: "DiscordRuntimeMode") -> bool:
        return self.rank >= capability.rank

    @property
    def can_ingest(self) -> bool:
        return self.allows(type(self).INGEST_ENABLED)

    @property
    def can_run_commands(self) -> bool:
        return self.allows(type(self).COMMAND_ENABLED)

    @property
    def can_post_autonomously(self) -> bool:
        return self.allows(type(self).AUTONOMOUS_POSTING_ENABLED)


def clamp_mode(
    requested: DiscordRuntimeMode,
    maximum: DiscordRuntimeMode,
) -> DiscordRuntimeMode:
    if requested.rank <= maximum.rank:
        return requested
    return maximum
