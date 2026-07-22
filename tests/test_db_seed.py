from __future__ import annotations

from sqlalchemy import func, select

from app.db.models import AttentionPolicy, CoreProfile, EvalPrompt, SelfModelSnapshot


def test_ac001_init_and_seed_create_initial_state(seeded_session, settings):
    assert settings.db_path.exists()
    assert seeded_session.scalar(select(func.count(CoreProfile.id))) == 1
    assert seeded_session.scalar(select(func.count(AttentionPolicy.id))) == 1
    assert seeded_session.scalar(select(func.count(SelfModelSnapshot.id))) == 1
    assert seeded_session.scalar(select(func.count(EvalPrompt.id))) == 4
    assert (settings.world_root / "notes" / "memory-loop.md").exists()


def test_inv006_core_profile_is_locked_initial_state(seeded_session):
    profile = seeded_session.scalar(select(CoreProfile).limit(1))
    assert profile is not None
    assert profile.locked is True
    assert profile.version == 1
