"""Self-model helpers."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import SelfModelSnapshot


def latest_self_model(session: Session) -> SelfModelSnapshot | None:
    return session.scalar(
        select(SelfModelSnapshot).order_by(SelfModelSnapshot.created_at.desc()).limit(1)
    )
