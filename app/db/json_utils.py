"""Small JSON helpers for TEXT-backed JSON columns."""

from __future__ import annotations

import json
from typing import Any, TypeVar

T = TypeVar("T")


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def json_loads(value: str | None, default: T) -> Any | T:
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def json_list(value: str | None) -> list[Any]:
    loaded = json_loads(value, [])
    return loaded if isinstance(loaded, list) else []


def json_dict(value: str | None) -> dict[str, Any]:
    loaded = json_loads(value, {})
    return loaded if isinstance(loaded, dict) else {}
