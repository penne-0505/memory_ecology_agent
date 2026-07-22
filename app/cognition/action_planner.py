"""Action planning and internal effects."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.adapters.clock import now_utc
from app.config import Settings
from app.db.json_utils import json_dumps
from app.db.models import Action, Concern, Outcome, WakeRequest


def _safe_workspace_path(settings: Settings, relative: str) -> Path:
    workspace = settings.workspace_root.resolve()
    path = (workspace / relative).resolve()
    path.relative_to(workspace)
    return path


def plan_wake_actions(
    session: Session,
    settings: Settings,
    concerns: list[Concern],
    probe_ids: list[int],
    observation_count: int,
) -> tuple[list[Action], list[Outcome], WakeRequest | None]:
    actions: list[Action] = []
    outcomes: list[Outcome] = []
    concern_ids = [concern.id for concern in concerns]

    if concerns:
        note_path = _safe_workspace_path(settings, "notes/latest-wake-summary.md")
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_text = (
            f"Wake summary at {now_utc().isoformat()}\n"
            f"observations={observation_count}\n"
            f"concerns={concern_ids}\n"
        )
        note_path.write_text(note_text, encoding="utf-8")
        action = Action(
            action_type="write_internal_note",
            rationale=(
                "Useful observations created or reinforced concerns, so an "
                "internal note records the trace summary."
            ),
            related_concern_ids_json=json_dumps(concern_ids),
            input_probe_ids_json=json_dumps(probe_ids),
            payload_json=json_dumps({"path": note_path.relative_to(settings.workspace_root).as_posix()}),
            external_effect="agent_workspace",
            status="completed",
        )
        session.add(action)
        session.flush()
        outcome = Outcome(
            action_id=action.id,
            observed_result="Internal note written under agent_workspace.",
            effect_on_concerns_json=json_dumps({"touched": concern_ids}),
            effect_on_attention_policy_json=json_dumps(
                {
                    "source_type": "local_file",
                    "result": "useful",
                    "probe_ids": probe_ids,
                    "concern_ids": concern_ids,
                }
            ),
        )
        session.add(outcome)
        actions.append(action)
        outcomes.append(outcome)

        wake_action = Action(
            action_type="request_wake",
            rationale="Schedule a follow-up wake to revisit unresolved concerns.",
            related_concern_ids_json=json_dumps(concern_ids),
            input_probe_ids_json=json_dumps(probe_ids),
            payload_json=json_dumps({"reason": "follow_up_unresolved_concern"}),
            external_effect="scheduler_request",
            status="completed",
        )
        session.add(wake_action)
        session.flush()
        request = WakeRequest(
            requested_by_action_id=wake_action.id,
            not_before=now_utc() + timedelta(minutes=15),
            preferred_at=now_utc() + timedelta(hours=1),
            urgency=min(1.0, max((c.activation_score for c in concerns), default=0.2) / 4),
            reason="Revisit unresolved concern after a bounded delay.",
            accepted_by_scheduler=True,
            scheduler_decision_reason="PoC scheduler accepts bounded internal wake requests.",
        )
        session.add(request)
        outcome2 = Outcome(
            action_id=wake_action.id,
            observed_result="Wake request accepted by the PoC scheduler model.",
            effect_on_concerns_json=json_dumps({"revisit": concern_ids}),
            effect_on_attention_policy_json=json_dumps({"direct_effect": "none"}),
        )
        session.add(outcome2)
        actions.append(wake_action)
        outcomes.append(outcome2)
        session.flush()
        return actions, outcomes, request

    action = Action(
        action_type="no_op",
        rationale="No observations were strong enough to justify a visible action.",
        related_concern_ids_json=json_dumps([]),
        input_probe_ids_json=json_dumps(probe_ids),
        payload_json=json_dumps({"observation_count": observation_count}),
        external_effect="none",
        status="completed",
    )
    session.add(action)
    session.flush()
    outcome = Outcome(
        action_id=action.id,
        observed_result="No action taken; trace kept as no_op outcome.",
        effect_on_concerns_json=json_dumps({}),
        effect_on_attention_policy_json=json_dumps({}),
    )
    session.add(outcome)
    session.flush()
    return [action], [outcome], None
