"""Environment-backed Discord adapter configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from typing import Literal, Mapping

from app.runtime.modes import DiscordRuntimeMode

DISCORD_CHANNEL_ROLES = (
    "agent_chat",
    "agent_inbox",
    "agent_trace",
    "agent_concerns",
    "agent_policy",
    "agent_eval",
    "agent_admin",
)

DEFAULT_INGESTABLE_ROLES = {"agent_chat", "agent_inbox"}
DEFAULT_BOT_OUTPUT_ROLES = {
    "agent_chat",
    "agent_trace",
    "agent_concerns",
    "agent_policy",
    "agent_eval",
    "agent_admin",
}
DEFAULT_AUTONOMOUS_OUTPUT_ROLES = {
    "agent_chat",
    "agent_concerns",
    "agent_eval",
}
DEFAULT_ALLOWED_ATTACHMENT_TYPES = {
    "text/plain",
    "text/markdown",
    "text/x-markdown",
    "application/json",
}
SECRET_NAME_PARTS = (
    ".env",
    "secret",
    "credential",
    "credentials",
    "token",
    "private",
    "passwd",
    "password",
    "id_rsa",
    "api_key",
    "apikey",
)


def _env_bool(env: Mapping[str, str], key: str, default: bool = False) -> bool:
    raw = env.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(env: Mapping[str, str], key: str, default: int) -> int:
    raw = env.get(key)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _env_set(env: Mapping[str, str], key: str, default: set[str]) -> set[str]:
    raw = env.get(key)
    if raw is None:
        return set(default)
    return {part.strip() for part in raw.split(",") if part.strip()}


def _env_id_set(env: Mapping[str, str], key: str) -> set[str]:
    return {part.strip() for part in env.get(key, "").split(",") if part.strip()}


def is_secret_like_name(name: str) -> bool:
    lowered = name.lower()
    return any(part in lowered for part in SECRET_NAME_PARTS)


@dataclass(frozen=True)
class DiscordChannelConfig:
    role: str
    id: str | None = None
    ingestable: bool = False
    bot_output_allowed: bool = False

    @property
    def configured(self) -> bool:
        return bool(self.id)


DiscordConfigSeverity = Literal["ok", "warning", "error"]


@dataclass(frozen=True)
class DiscordConfigCheck:
    severity: DiscordConfigSeverity
    code: str
    message: str


@dataclass(frozen=True)
class DiscordReadinessReport:
    target_mode: DiscordRuntimeMode
    live_run: bool
    checks: tuple[DiscordConfigCheck, ...]

    @property
    def errors(self) -> list[DiscordConfigCheck]:
        return [check for check in self.checks if check.severity == "error"]

    @property
    def warnings(self) -> list[DiscordConfigCheck]:
        return [check for check in self.checks if check.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_lines(self) -> list[str]:
        labels = {"ok": "OK", "warning": "WARN", "error": "ERROR"}
        lines = [
            "Discord doctor: "
            f"target_mode={self.target_mode.value} "
            f"live_run={str(self.live_run).lower()}"
        ]
        lines.extend(
            f"{labels[check.severity]} {check.code}: {check.message}"
            for check in self.checks
        )
        lines.append(
            f"Summary: errors={len(self.errors)} warnings={len(self.warnings)}"
        )
        return lines


@dataclass(frozen=True)
class DiscordSettings:
    enabled: bool = False
    mode: DiscordRuntimeMode = DiscordRuntimeMode.OBSERVE_ONLY
    max_mode: DiscordRuntimeMode = DiscordRuntimeMode.OBSERVE_ONLY
    guild_id: str | None = None
    token_env_var: str = "DISCORD_BOT_TOKEN"
    channels: dict[str, DiscordChannelConfig] = field(default_factory=dict)
    admin_user_ids: set[str] = field(default_factory=set)
    allow_mode_command: bool = False
    create_observations_from_ingest: bool = False
    attachment_ingest_enabled: bool = False
    max_attachment_bytes: int = 64 * 1024
    allowed_attachment_content_types: set[str] = field(
        default_factory=lambda: set(DEFAULT_ALLOWED_ATTACHMENT_TYPES)
    )
    autonomous_output_roles: set[str] = field(
        default_factory=lambda: set(DEFAULT_AUTONOMOUS_OUTPUT_ROLES)
    )
    autonomous_rate_limit_seconds: int = 3600

    @classmethod
    def disabled(cls) -> "DiscordSettings":
        return cls(channels=default_channels())

    def channel_for_id(self, channel_id: str | None) -> DiscordChannelConfig | None:
        if channel_id is None:
            return None
        wanted = str(channel_id)
        for channel in self.channels.values():
            if channel.id == wanted:
                return channel
        return None

    def channel_for_role(self, role: str) -> DiscordChannelConfig | None:
        return self.channels.get(role)

    def token_present(self, env: Mapping[str, str] | None = None) -> bool:
        source = env if env is not None else os.environ
        return bool(source.get(self.token_env_var, "").strip())

    def public_status(self, env: Mapping[str, str] | None = None) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "mode": self.mode.value,
            "max_mode": self.max_mode.value,
            "guild_id_configured": bool(self.guild_id),
            "token_env_var": self.token_env_var,
            "token_present": self.token_present(env),
            "channels": {
                role: {
                    "configured": channel.configured,
                    "ingestable": channel.ingestable,
                    "bot_output_allowed": channel.bot_output_allowed,
                }
                for role, channel in sorted(self.channels.items())
            },
            "allow_mode_command": self.allow_mode_command,
            "attachment_ingest_enabled": self.attachment_ingest_enabled,
            "max_attachment_bytes": self.max_attachment_bytes,
            "autonomous_output_roles": sorted(self.autonomous_output_roles),
            "autonomous_rate_limit_seconds": self.autonomous_rate_limit_seconds,
        }


def diagnose_discord_settings(
    settings: DiscordSettings,
    *,
    env: Mapping[str, str] | None = None,
    target_mode: DiscordRuntimeMode | None = None,
    live_run: bool = False,
) -> DiscordReadinessReport:
    source = env if env is not None else os.environ
    mode = target_mode or settings.mode
    checks: list[DiscordConfigCheck] = []

    def add(severity: DiscordConfigSeverity, code: str, message: str) -> None:
        checks.append(DiscordConfigCheck(severity, code, message))

    if not settings.token_env_var:
        add("error", "token_env_var_blank", "AGENT_DISCORD_TOKEN_ENV_VAR is blank.")
    elif settings.token_present(source):
        add(
            "ok",
            "token_present",
            f"{settings.token_env_var} is set; token value is not displayed.",
        )
    elif live_run:
        add(
            "error",
            "token_missing",
            f"Set {settings.token_env_var} before starting the live Discord bot.",
        )
    else:
        add(
            "warning",
            "token_missing",
            f"{settings.token_env_var} is not set; live bot startup will fail.",
        )

    if settings.enabled:
        add("ok", "discord_enabled", "AGENT_DISCORD_ENABLED=true.")
    elif live_run or mode != DiscordRuntimeMode.OBSERVE_ONLY:
        add(
            "error",
            "discord_disabled",
            "Set AGENT_DISCORD_ENABLED=true before this target mode can run.",
        )
    else:
        add("ok", "discord_disabled", "Discord remains disabled by default.")

    if settings.mode.rank > settings.max_mode.rank:
        add(
            "error",
            "configured_mode_exceeds_max_mode",
            "AGENT_DISCORD_MODE will be clamped by AGENT_DISCORD_MAX_MODE.",
        )
    if mode.rank > settings.max_mode.rank:
        add(
            "error",
            "target_mode_exceeds_max_mode",
            f"target mode {mode.value} exceeds max mode {settings.max_mode.value}.",
        )
    else:
        add(
            "ok",
            "mode_within_max_mode",
            f"target mode {mode.value} is within max mode {settings.max_mode.value}.",
        )

    if settings.guild_id:
        add("ok", "guild_configured", "Guild ID is configured.")
    elif live_run:
        add(
            "warning",
            "guild_missing",
            "No guild ID is configured; command sync will use global propagation.",
        )
    else:
        add(
            "warning",
            "guild_missing",
            "No guild ID is configured for live guild smoke.",
        )

    channel_ids: dict[str, list[str]] = {}
    for role, channel in settings.channels.items():
        if channel.id:
            channel_ids.setdefault(channel.id, []).append(role)
    for roles in channel_ids.values():
        if len(roles) > 1:
            add(
                "error",
                "duplicate_channel_id",
                f"One Discord channel ID is assigned to multiple roles: {', '.join(sorted(roles))}.",
            )

    trace_channel = settings.channel_for_role("agent_trace")
    if trace_channel and trace_channel.configured and trace_channel.bot_output_allowed:
        add("ok", "trace_channel_ready", "agent_trace can receive trace output.")
    elif live_run or settings.enabled:
        add(
            "error",
            "trace_channel_not_ready",
            "Configure AGENT_DISCORD_CHANNEL_AGENT_TRACE_ID with bot output allowed for live trace smoke.",
        )
    else:
        add(
            "warning",
            "trace_channel_not_ready",
            "agent_trace is not configured; observe-only trace posting cannot be live-smoked.",
        )

    if mode.can_ingest:
        ingestable_roles = [
            channel.role
            for channel in settings.channels.values()
            if channel.configured and channel.ingestable
        ]
        if ingestable_roles:
            add(
                "ok",
                "ingest_channels_ready",
                f"Configured ingestable roles: {', '.join(sorted(ingestable_roles))}.",
            )
        else:
            add(
                "error",
                "ingest_channel_missing",
                "Configure at least one ingestable channel such as agent_chat or agent_inbox.",
            )
        add(
            "warning",
            "developer_portal_message_content_required",
            "Message Content intent must also be enabled in the Discord Developer Portal.",
        )

    if mode.can_run_commands:
        admin_channel = settings.channel_for_role("agent_admin")
        has_admin_channel = bool(admin_channel and admin_channel.configured)
        if settings.admin_user_ids or has_admin_channel:
            add(
                "ok",
                "command_control_ready",
                "Mutating commands have an admin user or agent_admin channel path.",
            )
        else:
            add(
                "error",
                "command_control_missing",
                "Configure AGENT_DISCORD_ADMIN_USER_IDS or AGENT_DISCORD_CHANNEL_AGENT_ADMIN_ID for mutating commands.",
            )
        if settings.allow_mode_command and not settings.admin_user_ids:
            add(
                "error",
                "mode_command_admin_missing",
                "/mode requires AGENT_DISCORD_ADMIN_USER_IDS; agent_admin channel alone is not enough.",
            )

    unknown_autonomous_roles = sorted(
        role for role in settings.autonomous_output_roles if role not in settings.channels
    )
    if unknown_autonomous_roles:
        add(
            "error",
            "unknown_autonomous_output_role",
            f"Unknown autonomous output role(s): {', '.join(unknown_autonomous_roles)}.",
        )

    if mode.can_post_autonomously:
        ready_roles = [
            role
            for role in settings.autonomous_output_roles
            if (
                (channel := settings.channel_for_role(role)) is not None
                and channel.configured
                and channel.bot_output_allowed
            )
        ]
        if ready_roles:
            add(
                "ok",
                "autonomous_output_ready",
                f"Configured autonomous output roles: {', '.join(sorted(ready_roles))}.",
            )
        else:
            add(
                "error",
                "autonomous_output_missing",
                "Configure at least one autonomous output role with a channel ID and bot output allowed.",
            )
        if settings.autonomous_rate_limit_seconds < 0:
            add(
                "error",
                "autonomous_rate_limit_invalid",
                "AGENT_DISCORD_AUTONOMOUS_RATE_LIMIT_SECONDS must be >= 0.",
            )

    if settings.attachment_ingest_enabled and settings.max_attachment_bytes <= 0:
        add(
            "error",
            "attachment_limit_invalid",
            "AGENT_DISCORD_MAX_ATTACHMENT_BYTES must be > 0 when attachment ingest is enabled.",
        )

    return DiscordReadinessReport(mode, live_run, tuple(checks))


def default_channels() -> dict[str, DiscordChannelConfig]:
    return {
        role: DiscordChannelConfig(
            role=role,
            ingestable=role in DEFAULT_INGESTABLE_ROLES,
            bot_output_allowed=role in DEFAULT_BOT_OUTPUT_ROLES,
        )
        for role in DISCORD_CHANNEL_ROLES
    }


def load_discord_settings(env: Mapping[str, str] | None = None) -> DiscordSettings:
    source = env if env is not None else os.environ
    enabled = _env_bool(source, "AGENT_DISCORD_ENABLED", False)
    mode = DiscordRuntimeMode.parse(source.get("AGENT_DISCORD_MODE", "observe_only"))
    max_mode = DiscordRuntimeMode.parse(source.get("AGENT_DISCORD_MAX_MODE", mode.value))
    channel_overrides: dict[str, DiscordChannelConfig] = {}
    for role in DISCORD_CHANNEL_ROLES:
        env_role = role.upper()
        channel_id = source.get(f"AGENT_DISCORD_CHANNEL_{env_role}_ID") or None
        ingestable = _env_bool(
            source,
            f"AGENT_DISCORD_CHANNEL_{env_role}_INGESTABLE",
            role in DEFAULT_INGESTABLE_ROLES,
        )
        bot_output_allowed = _env_bool(
            source,
            f"AGENT_DISCORD_CHANNEL_{env_role}_BOT_OUTPUT_ALLOWED",
            role in DEFAULT_BOT_OUTPUT_ROLES,
        )
        channel_overrides[role] = DiscordChannelConfig(
            role=role,
            id=channel_id.strip() if channel_id else None,
            ingestable=ingestable,
            bot_output_allowed=bot_output_allowed,
        )
    return DiscordSettings(
        enabled=enabled,
        mode=mode,
        max_mode=max_mode,
        guild_id=(source.get("AGENT_DISCORD_GUILD_ID") or "").strip() or None,
        token_env_var=(
            source.get("AGENT_DISCORD_TOKEN_ENV_VAR") or "DISCORD_BOT_TOKEN"
        ).strip(),
        channels=channel_overrides,
        admin_user_ids=_env_id_set(source, "AGENT_DISCORD_ADMIN_USER_IDS"),
        allow_mode_command=_env_bool(source, "AGENT_DISCORD_ALLOW_MODE_COMMAND", False),
        create_observations_from_ingest=_env_bool(
            source, "AGENT_DISCORD_CREATE_OBSERVATIONS", False
        ),
        attachment_ingest_enabled=_env_bool(
            source, "AGENT_DISCORD_ATTACHMENT_INGEST_ENABLED", False
        ),
        max_attachment_bytes=_env_int(
            source, "AGENT_DISCORD_MAX_ATTACHMENT_BYTES", 64 * 1024
        ),
        allowed_attachment_content_types=_env_set(
            source,
            "AGENT_DISCORD_ALLOWED_ATTACHMENT_CONTENT_TYPES",
            DEFAULT_ALLOWED_ATTACHMENT_TYPES,
        ),
        autonomous_output_roles=_env_set(
            source,
            "AGENT_DISCORD_AUTONOMOUS_OUTPUT_ROLES",
            DEFAULT_AUTONOMOUS_OUTPUT_ROLES,
        ),
        autonomous_rate_limit_seconds=_env_int(
            source, "AGENT_DISCORD_AUTONOMOUS_RATE_LIMIT_SECONDS", 3600
        ),
    )
