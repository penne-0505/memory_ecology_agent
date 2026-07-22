"""Chat cycle."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.adapters.llm import LLMClient, MockLLMClient, create_llm_client
from app.config import Settings
from app.cognition.context_builder import build_context
from app.db.json_utils import json_dumps
from app.db.models import Action, ResponseTrace
from app.runtime.events import persist_raw_event
from app.schemas import RawEventInput


def run_chat_cycle(
    session: Session,
    user_message: str,
    settings: Settings | None = None,
    llm: LLMClient | None = None,
) -> dict[str, object]:
    client = llm or (create_llm_client(settings) if settings else MockLLMClient())
    user_event = persist_raw_event(
        session,
        RawEventInput(
            source_type="conversation",
            event_type="user_message",
            payload={"role": "user"},
            content_text=user_message,
        ),
    )
    context = build_context(session, user_message)
    response_text = client.complete_text(context.system_prompt, user_message)
    action = Action(
        action_type="respond",
        rationale="Respond using selected memory, concern, and attention policy context.",
        related_concern_ids_json=json_dumps(
            [item["id"] for item in context.selected_concerns]
        ),
        input_probe_ids_json=json_dumps([]),
        payload_json=json_dumps({"response_text": response_text}),
        external_effect="conversation",
        status="completed",
    )
    session.add(action)
    session.flush()
    trace = ResponseTrace(
        user_message_event_id=user_event.id,
        response_action_id=action.id,
        selected_memory_ids_json=json_dumps(context.selected_memory_ids),
        selected_concerns_json=json_dumps(context.selected_concerns),
        selected_attention_policy_json=json_dumps(context.selected_attention_policy),
        concern_modes_json=json_dumps(context.concern_modes),
        prompt_summary=context.prompt_summary,
    )
    session.add(trace)
    session.flush()
    return {
        "response_text": response_text,
        "response_action_id": action.id,
        "response_trace_id": trace.id,
        "selected_concern_count": len(context.selected_concerns),
    }
