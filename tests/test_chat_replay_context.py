from __future__ import annotations

from sqlalchemy import func, select

from app.cognition.context_builder import build_context
from app.db.json_utils import json_dumps, json_loads
from app.db.models import Action, Concern, CoreProfile, ReplayRun, ResponseTrace
from app.eval.replay import compare_replay_runs, run_replay_eval
from app.runtime.chat_cycle import run_chat_cycle
from app.runtime.reflection_cycle import run_reflection_cycle
from app.runtime.wake_cycle import run_wake_cycle


def test_ac003_chat_cycle_saves_response_trace(seeded_session, settings):
    run_wake_cycle(seeded_session, settings, reason="cron")
    result = run_chat_cycle(seeded_session, "Should we implement now?")
    assert result["response_trace_id"]
    assert seeded_session.scalar(select(func.count(ResponseTrace.id))) == 1
    assert seeded_session.scalar(
        select(func.count(Action.id)).where(Action.action_type == "respond")
    ) == 1
    trace = seeded_session.scalar(select(ResponseTrace).limit(1))
    assert json_loads(trace.selected_attention_policy_json, {})["version"] >= 1
    assert json_loads(trace.concern_modes_json, {})


def test_ac004_inv008_replay_run_and_compare_save_selected_state(seeded_session, settings):
    run_wake_cycle(seeded_session, settings, reason="cron")
    runs = run_replay_eval(seeded_session, eval_prompt_id=1)
    assert len(runs) == 1
    assert seeded_session.scalar(select(func.count(ReplayRun.id))) == 1
    comparison = compare_replay_runs(seeded_session, prompt_id=1)
    assert len(comparison) == 1
    assert comparison[0]["selected_attention_policy"]["version"] >= 1
    assert "response_text" in comparison[0]


def test_inv007_context_builder_classifies_mention_influence_ignore(seeded_session):
    for index in range(6):
        seeded_session.add(
            Concern(
                title=f"Concern {index}",
                object_json=json_dumps({"index": index}),
                tension_json=json_dumps({"uncertainty": 0.5}),
                closure_hypothesis="close with evidence",
                state="active",
                activation_score=3.0 - index * 0.2,
                unresolvedness=0.5,
                recurrence_score=0.1,
                self_relevance=0.5,
                external_relevance=0.5,
                attempt_pressure=0.5,
                saturation_penalty=0.0,
                opened_reason="test",
                source_observation_ids_json="[]",
                closure_mode="test",
            )
        )
    seeded_session.flush()
    context = build_context(seeded_session, "hello")
    modes = set(context.concern_modes.values())
    assert "mention" in modes
    assert "influence" in modes
    assert "ignore" in modes
    assert len([m for m in context.concern_modes.values() if m == "mention"]) == 1


def test_inv006_wake_and_reflect_do_not_update_core_profile(seeded_session, settings):
    before = seeded_session.scalar(select(CoreProfile).limit(1))
    content = before.content
    created_at = before.created_at
    run_wake_cycle(seeded_session, settings, reason="cron")
    run_reflection_cycle(seeded_session)
    after = seeded_session.scalar(select(CoreProfile).limit(1))
    assert after.content == content
    assert after.created_at == created_at
