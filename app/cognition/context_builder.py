"""Build chat and replay context from current state."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.json_utils import json_dict
from app.db.models import AttentionPolicy, Concern, CoreProfile, Memory, SelfModelSnapshot
from app.schemas import ContextBundle


def build_context(session: Session, user_message: str) -> ContextBundle:
    core = session.scalar(select(CoreProfile).order_by(CoreProfile.version.desc()).limit(1))
    self_model = session.scalar(
        select(SelfModelSnapshot).order_by(SelfModelSnapshot.created_at.desc()).limit(1)
    )
    policy = session.scalar(
        select(AttentionPolicy).order_by(AttentionPolicy.version.desc()).limit(1)
    )
    memories = session.scalars(select(Memory).order_by(Memory.updated_at.desc()).limit(5)).all()
    concerns = session.scalars(
        select(Concern)
        .where(Concern.state.in_(["seed", "active", "dormant"]))
        .order_by(Concern.activation_score.desc(), Concern.updated_at.desc())
        .limit(6)
    ).all()

    selected_concerns: list[dict[str, object]] = []
    concern_modes: dict[str, str] = {}
    for index, concern in enumerate(concerns):
        if index == 0 and concern.activation_score >= 2.0:
            mode = "mention"
        elif index < 4:
            mode = "influence"
        else:
            mode = "ignore"
        concern_modes[str(concern.id)] = mode
        if mode != "ignore":
            selected_concerns.append(
                {
                    "id": concern.id,
                    "title": concern.title,
                    "state": concern.state,
                    "activation_score": concern.activation_score,
                    "mode": mode,
                }
            )

    policy_payload = {
        "id": policy.id if policy else None,
        "version": policy.version if policy else None,
        "source_preferences": json_dict(policy.source_preferences_json) if policy else {},
        "response_preferences": json_dict(policy.response_preferences_json) if policy else {},
        "exploration_randomness": policy.exploration_randomness if policy else None,
    }
    memory_lines = [f"- memory#{memory.id}: {memory.content}" for memory in memories]
    concern_lines = [
        f"- concern#{item['id']} ({item['mode']}): {item['title']}"
        for item in selected_concerns
    ]
    system_prompt = "\n".join(
        [
            "Trace-first Memory Ecology Agent context.",
            f"Core: {core.content if core else '(missing core profile)'}",
            f"Self model: {self_model.summary if self_model else '(missing self model)'}",
            f"Policy: {policy_payload}",
            "Selected memories:",
            *memory_lines,
            "Selected concerns:",
            *concern_lines,
            "Use influence more than explicit self-talk; mention only the most relevant concern.",
        ]
    )
    prompt_summary = (
        f"memories={len(memories)} concerns={len(selected_concerns)} "
        f"policy_version={policy_payload['version']} user={user_message[:80]!r}"
    )
    return ContextBundle(
        system_prompt=system_prompt,
        prompt_summary=prompt_summary,
        selected_memory_ids=[memory.id for memory in memories],
        selected_concerns=selected_concerns,
        selected_attention_policy=policy_payload,
        concern_modes=concern_modes,
    )
