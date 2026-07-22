"""Compact text renderers for Discord-facing output."""

from __future__ import annotations

from collections.abc import Iterable
import re
from typing import Any

MAX_DISCORD_TEXT = 1900
SECRET_TEXT_PATTERNS = (
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\s*="),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\bAuthorization:\s*Bearer\s+"),
)


def looks_sensitive_text(text: str) -> bool:
    return any(pattern.search(text) for pattern in SECRET_TEXT_PATTERNS)


def clip_discord_text(text: str, limit: int = MAX_DISCORD_TEXT) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 28].rstrip() + "\n...(truncated for Discord)"


def bullet_lines(items: Iterable[str], empty: str = "- none") -> str:
    lines = [f"- {item}" for item in items]
    return "\n".join(lines) if lines else empty


def render_mapping(mapping: dict[str, Any], *, max_items: int = 6) -> str:
    if not mapping:
        return "{}"
    pieces = []
    for index, (key, value) in enumerate(sorted(mapping.items())):
        if index >= max_items:
            pieces.append("...")
            break
        pieces.append(f"{key}={value}")
    return ", ".join(pieces)
