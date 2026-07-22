"""Ablation hooks for future evaluation work."""

from __future__ import annotations


def describe_available_ablations() -> list[str]:
    return [
        "without_memories",
        "without_active_concerns",
        "without_attention_policy",
    ]
