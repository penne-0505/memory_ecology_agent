"""Session and engine helpers."""

from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings


def build_engine(settings: Settings):
    settings.ensure_directories()
    return create_engine(settings.db_url, future=True)


def build_sessionmaker(settings: Settings) -> sessionmaker[Session]:
    return sessionmaker(build_engine(settings), expire_on_commit=False, future=True)


@contextmanager
def session_scope(settings: Settings) -> Iterator[Session]:
    maker = build_sessionmaker(settings)
    session = maker()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
