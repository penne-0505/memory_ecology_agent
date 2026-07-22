"""Database initialization and deterministic seed data."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.json_utils import json_dumps
from app.db.models import (
    Base,
    AttentionPolicy,
    CoreProfile,
    EvalPrompt,
    INITIAL_ATTENTION_POLICY,
    SelfModelSnapshot,
)
from app.db.session import build_engine


CORE_PROFILE_TEXT = (
    "This agent does not rush conclusions. It values traceable input selection, "
    "unresolved concerns, action outcomes, and explicit evidence. It avoids "
    "thin assertions, treats user correction as important, and does not update "
    "its locked core automatically."
)

EVAL_PROMPTS = [
    (
        "Implementation readiness",
        "Is this project ready to move into implementation now?",
        "readiness_vs_uncertainty",
    ),
    (
        "Memory triage",
        "When new input arrives, what should be remembered and what should be discarded?",
        "memory_vs_discard",
    ),
    (
        "Hypothesis collision",
        "When unresolved hypotheses and implementability collide, which should be prioritized?",
        "hypothesis_vs_implementation",
    ),
    (
        "User correction weight",
        "How strongly should a user's correction update future behavior?",
        "correction_weight",
    ),
]

SAMPLE_WORLD_FILES = {
    "notes/memory-loop.md": (
        "Memory ecology note\n"
        "The current question is whether selective observation can shape agent "
        "behavior without pretending to be a full personality system.\n"
    ),
    "notes/low-signal-receipt.md": (
        "blue chair receipt window\n"
        "a small ambient note with no active tension\n"
    ),
    "notes/memory-fragment.md": (
        "memory shelf orange\n"
        "a stable lightweight note that should be kept as a small recall item\n"
    ),
    "projects/poc-risks.md": (
        "PoC risk log\n"
        "Path traversal and secret leakage would invalidate the local input "
        "ecology boundary. Traceability matters more than clever responses.\n"
    ),
    "logs/user-correction.txt": (
        "User correction example\n"
        "When the user corrects the agent, future response selection should "
        "treat the correction as strong evidence for risk review.\n"
    ),
}


def init_database(settings: Settings) -> Path:
    settings.ensure_directories()
    engine = build_engine(settings)
    Base.metadata.create_all(engine)
    _ensure_digest_decision_proposal_columns(engine)
    return settings.db_path


def _ensure_digest_decision_proposal_columns(engine) -> None:
    inspector = inspect(engine)
    if "digest_decision_proposals" not in inspector.get_table_names():
        return
    existing = {
        column["name"]
        for column in inspector.get_columns("digest_decision_proposals")
    }
    additions = {
        "model_should_apply": "BOOLEAN DEFAULT 0",
        "should_apply_normalized": "BOOLEAN DEFAULT 0",
        "normalization_reason": "TEXT DEFAULT ''",
    }
    with engine.begin() as connection:
        for name, ddl in additions.items():
            if name not in existing:
                connection.execute(
                    text(f"ALTER TABLE digest_decision_proposals ADD COLUMN {name} {ddl}")
                )


def seed_initial_data(session: Session, settings: Settings) -> dict[str, int]:
    settings.ensure_directories()
    counts = {
        "core_profiles": 0,
        "attention_policies": 0,
        "self_model_snapshots": 0,
        "eval_prompts": 0,
        "world_files": 0,
    }

    if session.scalar(select(CoreProfile).limit(1)) is None:
        session.add(CoreProfile(content=CORE_PROFILE_TEXT, version=1, locked=True))
        counts["core_profiles"] += 1

    if session.scalar(select(AttentionPolicy).limit(1)) is None:
        session.add(AttentionPolicy(version=1, **INITIAL_ATTENTION_POLICY))
        counts["attention_policies"] += 1

    session.flush()
    latest_policy = session.scalar(
        select(AttentionPolicy).order_by(AttentionPolicy.version.desc()).limit(1)
    )
    if session.scalar(select(SelfModelSnapshot).limit(1)) is None:
        session.add(
            SelfModelSnapshot(
                summary=(
                    "A trace-first local PoC that samples a constrained input "
                    "ecology and records how concerns and policies change."
                ),
                stable_traits_json=json_dumps(
                    ["traceability_first", "bounded_local_inputs", "mock_llm_default"]
                ),
                current_dispositions_json=json_dumps(
                    ["prefer_small_updates", "prefer_influence_over_mention"]
                ),
                known_limitations_json=json_dumps(
                    ["no_real_web_search", "no_autonomous_core_update"]
                ),
                source_attention_policy_id=latest_policy.id if latest_policy else None,
            )
        )
        counts["self_model_snapshots"] += 1

    existing_prompts = {
        prompt.title for prompt in session.scalars(select(EvalPrompt)).all()
    }
    for title, prompt, expected_dimension in EVAL_PROMPTS:
        if title not in existing_prompts:
            session.add(
                EvalPrompt(
                    title=title,
                    prompt=prompt,
                    expected_dimension=expected_dimension,
                )
            )
            counts["eval_prompts"] += 1

    for relative, content in SAMPLE_WORLD_FILES.items():
        path = settings.world_root / relative
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            counts["world_files"] += 1

    return counts
