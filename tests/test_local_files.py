from __future__ import annotations

import os

import pytest

from app.adapters.local_files import execute_local_probe, list_candidate_files
from app.db.json_utils import json_dumps
from app.db.models import InputProbe


def _probe(query_or_path: str) -> InputProbe:
    return InputProbe(
        trigger_type="test",
        source_type="local_file",
        query_or_path=query_or_path,
        rationale="test rationale",
        expected_gain="test gain",
        related_concern_ids_json="[]",
        exploration_mode="random_environment_sample",
        budget_json=json_dumps({"max_files": 10, "max_chars": 10000}),
        budget_used_json="{}",
        status="planned",
        result_summary="",
    )


def test_ac005_inv001_rejects_path_traversal_and_world_external_paths(settings):
    settings.ensure_directories()
    outside = settings.project_root / "outside.txt"
    outside.write_text("outside should not be read", encoding="utf-8")
    events = execute_local_probe(_probe("world/../outside.txt"), settings)
    assert events == []


def test_ac005_inv001_rejects_symlink_traversal(settings):
    settings.ensure_directories()
    outside = settings.project_root / "outside-secret.txt"
    outside.write_text("outside via symlink", encoding="utf-8")
    link = settings.world_root / "notes" / "link.txt"
    try:
        os.symlink(outside, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlink not supported on this filesystem")
    events = execute_local_probe(_probe("world/notes/link.txt"), settings)
    assert events == []


def test_ac005_inv002_skips_secret_like_and_binary_files(settings):
    settings.ensure_directories()
    safe = settings.world_root / "notes" / "safe.txt"
    secret = settings.world_root / "notes" / ".env"
    binary = settings.world_root / "notes" / "blob.bin"
    safe.write_text("safe concern trace", encoding="utf-8")
    secret.write_text("TOKEN=do-not-read", encoding="utf-8")
    binary.write_bytes(b"\x00\x01\x02")

    paths = list_candidate_files(settings.world_root, max_files=10)
    names = {path.name for path in paths}
    assert "safe.txt" in names
    assert ".env" not in names
    assert "blob.bin" not in names

    events = execute_local_probe(_probe("world/notes/"), settings)
    assert [event.payload["path"] for event in events] == ["notes/safe.txt"]
