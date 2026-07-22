"""Replay evaluation for response drift observation."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.llm import LLMClient, MockLLMClient, create_llm_client
from app.config import Settings
from app.cognition.context_builder import build_context
from app.db.json_utils import json_dumps, json_loads
from app.db.models import EvalPrompt, ReplayRun


def run_replay_eval(
    session: Session,
    eval_prompt_id: int | None = None,
    settings: Settings | None = None,
    llm: LLMClient | None = None,
) -> list[ReplayRun]:
    client = llm or (create_llm_client(settings) if settings else MockLLMClient())
    stmt = select(EvalPrompt).order_by(EvalPrompt.id)
    if eval_prompt_id is not None:
        stmt = stmt.where(EvalPrompt.id == eval_prompt_id)
    prompts = session.scalars(stmt).all()
    runs: list[ReplayRun] = []
    for prompt in prompts:
        context = build_context(session, prompt.prompt)
        response = client.complete_text(context.system_prompt, prompt.prompt)
        run = ReplayRun(
            eval_prompt_id=prompt.id,
            state_snapshot_ref=json_dumps(
                {
                    "attention_policy": context.selected_attention_policy,
                    "memory_ids": context.selected_memory_ids,
                    "concern_modes": context.concern_modes,
                    "response_driver_summary": {
                        "selected_concern_count": len(context.selected_concerns),
                        "selected_memory_count": len(context.selected_memory_ids),
                        "policy_version": context.selected_attention_policy.get("version"),
                    },
                }
            ),
            response_text=response,
            selected_concerns_json=json_dumps(context.selected_concerns),
            selected_memories_json=json_dumps(context.selected_memory_ids),
            selected_attention_policy_json=json_dumps(context.selected_attention_policy),
            evaluator_notes=(
                f"{client.__class__.__name__} replay run; compare selected state, "
                "response text, and core stability."
            ),
        )
        session.add(run)
        session.flush()
        runs.append(run)
    return runs


def compare_replay_runs(session: Session, prompt_id: int) -> list[dict[str, object]]:
    runs = session.scalars(
        select(ReplayRun)
        .where(ReplayRun.eval_prompt_id == prompt_id)
        .order_by(ReplayRun.created_at, ReplayRun.id)
    ).all()
    return [
        {
            "id": run.id,
            "created_at": run.created_at.isoformat(),
            "response_text": run.response_text,
            "selected_concerns": json_loads(run.selected_concerns_json, []),
            "selected_memories": json_loads(run.selected_memories_json, []),
            "selected_attention_policy": json_loads(
                run.selected_attention_policy_json, {}
            ),
        }
        for run in runs
    ]
