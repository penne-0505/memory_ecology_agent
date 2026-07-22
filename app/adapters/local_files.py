"""Read-only local file adapter constrained to world/."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path

from app.config import Settings
from app.db.json_utils import json_dict
from app.db.models import InputProbe
from app.schemas import RawEventInput

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


@dataclass(frozen=True)
class FileReadResult:
    path: Path
    relative_path: str
    content_text: str
    content_hash: str
    chars_read: int


def _is_secret_like(path: Path) -> bool:
    lowered = path.name.lower()
    return any(part in lowered for part in SECRET_NAME_PARTS)


def _is_binary(path: Path) -> bool:
    try:
        sample = path.read_bytes()[:2048]
    except OSError:
        return True
    if b"\x00" in sample:
        return True
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def _resolve_world_path(root: Path, candidate: Path) -> Path | None:
    root_resolved = root.resolve()
    try:
        resolved = candidate.resolve(strict=True)
    except (FileNotFoundError, RuntimeError, OSError):
        return None
    try:
        resolved.relative_to(root_resolved)
    except ValueError:
        return None
    return resolved


def list_candidate_files(root: Path, max_files: int) -> list[Path]:
    resolved_root = root.resolve()
    if not resolved_root.exists() or not resolved_root.is_dir():
        return []
    candidates: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(resolved_root, followlinks=False):
        dirnames[:] = [
            name for name in sorted(dirnames) if not (Path(dirpath) / name).is_symlink()
        ]
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            if len(candidates) >= max_files:
                return candidates
            if path.is_symlink() or _is_secret_like(path) or _is_binary(path):
                continue
            candidates.append(path)
    return candidates


def read_files(paths: list[Path], max_chars: int, world_root: Path | None = None) -> list[FileReadResult]:
    results: list[FileReadResult] = []
    remaining = max_chars
    root = world_root.resolve() if world_root else None
    for path in paths:
        if remaining <= 0:
            break
        if path.is_symlink() or _is_secret_like(path) or _is_binary(path):
            continue
        try:
            resolved = path.resolve(strict=True)
        except (FileNotFoundError, RuntimeError, OSError):
            continue
        if root is not None:
            try:
                relative = resolved.relative_to(root)
            except ValueError:
                continue
        else:
            relative = Path(resolved.name)
        try:
            text = resolved.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        clipped = text[:remaining]
        remaining -= len(clipped)
        digest = hashlib.sha256(clipped.encode("utf-8")).hexdigest()
        results.append(
            FileReadResult(
                path=resolved,
                relative_path=relative.as_posix(),
                content_text=clipped,
                content_hash=digest,
                chars_read=len(clipped),
            )
        )
    return results


def execute_local_probe(probe: InputProbe, config: Settings) -> list[RawEventInput]:
    budget = json_dict(probe.budget_json)
    max_files = int(budget.get("max_files", config.max_probe_files))
    max_chars = int(budget.get("max_chars", config.max_probe_chars))
    world_root = config.world_root.resolve()

    raw_query = Path(probe.query_or_path)
    if raw_query.is_absolute():
        requested = raw_query
    else:
        requested = (config.project_root / raw_query).resolve()
    resolved = _resolve_world_path(world_root, requested)
    if resolved is None:
        return []

    if resolved.is_dir():
        paths = list_candidate_files(resolved, max_files)
    elif resolved.is_file():
        paths = [resolved]
    else:
        paths = []

    results = read_files(paths[:max_files], max_chars=max_chars, world_root=world_root)
    return [
        RawEventInput(
            source_type="local_file",
            event_type="file_read",
            payload={
                "path": result.relative_path,
                "content_hash": result.content_hash,
                "chars_read": result.chars_read,
            },
            content_text=result.content_text,
        )
        for result in results
    ]
