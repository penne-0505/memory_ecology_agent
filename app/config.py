"""Runtime configuration for the local PoC."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path

from app.adapters.discord_config import DiscordSettings, load_discord_settings


@dataclass(frozen=True)
class Settings:
    project_root: Path
    db_path: Path
    world_root: Path
    workspace_root: Path
    max_probe_files: int = 3
    max_probe_chars: int = 12_000
    max_web_queries_per_cycle: int = 2
    observation_extractor: str = "deterministic"
    observation_extractor_fallback: str = "deterministic"
    digest_decider: str = "deterministic"
    digest_proposal_confidence_threshold: float = 0.75
    llm_provider: str = "mock"
    llm_model: str | None = None
    llm_timeout_seconds: float = 30.0
    llm_max_tokens: int = 1024
    discord: DiscordSettings = field(default_factory=DiscordSettings.disabled)

    @classmethod
    def load(cls) -> "Settings":
        root = Path(os.environ.get("AGENT_PROJECT_ROOT", Path.cwd())).resolve()
        db_path = Path(os.environ.get("AGENT_DB_PATH", root / "data" / "agent.db"))
        world_root = Path(os.environ.get("AGENT_WORLD_ROOT", root / "world"))
        workspace_root = Path(
            os.environ.get("AGENT_WORKSPACE_ROOT", root / "agent_workspace")
        )
        return cls(
            project_root=root,
            db_path=db_path.resolve(),
            world_root=world_root.resolve(),
            workspace_root=workspace_root.resolve(),
            max_probe_files=int(os.environ.get("AGENT_MAX_PROBE_FILES", "3")),
            max_probe_chars=int(os.environ.get("AGENT_MAX_PROBE_CHARS", "12000")),
            max_web_queries_per_cycle=int(
                os.environ.get("AGENT_MAX_WEB_QUERIES", "2")
            ),
            observation_extractor=os.environ.get(
                "AGENT_OBSERVATION_EXTRACTOR", "deterministic"
            )
            .strip()
            .lower(),
            observation_extractor_fallback=os.environ.get(
                "AGENT_OBSERVATION_EXTRACTOR_FALLBACK", "deterministic"
            )
            .strip()
            .lower(),
            digest_decider=os.environ.get("AGENT_DIGEST_DECIDER", "deterministic")
            .strip()
            .lower(),
            digest_proposal_confidence_threshold=float(
                os.environ.get("AGENT_DIGEST_PROPOSAL_CONFIDENCE_THRESHOLD", "0.75")
            ),
            llm_provider=os.environ.get("AGENT_LLM_PROVIDER", "mock").strip().lower(),
            llm_model=os.environ.get("AGENT_LLM_MODEL") or None,
            llm_timeout_seconds=float(
                os.environ.get("AGENT_LLM_TIMEOUT_SECONDS", "30")
            ),
            llm_max_tokens=int(os.environ.get("AGENT_LLM_MAX_TOKENS", "1024")),
            discord=load_discord_settings(os.environ),
        )

    @property
    def db_url(self) -> str:
        return f"sqlite:///{self.db_path}"

    def ensure_directories(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        for path in [
            self.world_root / "inbox",
            self.world_root / "notes",
            self.world_root / "articles",
            self.world_root / "projects",
            self.world_root / "logs",
            self.workspace_root / "notes",
            self.workspace_root / "scratch",
            self.workspace_root / "exports",
        ]:
            path.mkdir(parents=True, exist_ok=True)
