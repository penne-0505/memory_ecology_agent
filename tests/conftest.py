from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.init_db import init_database, seed_initial_data
from app.db.session import session_scope


@pytest.fixture()
def settings(tmp_path) -> Settings:
    root = tmp_path
    return Settings(
        project_root=root,
        db_path=(root / "data" / "agent.db").resolve(),
        world_root=(root / "world").resolve(),
        workspace_root=(root / "agent_workspace").resolve(),
    )


@pytest.fixture()
def seeded_session(settings: Settings) -> Iterator[Session]:
    init_database(settings)
    with session_scope(settings) as session:
        seed_initial_data(session, settings)
        yield session
