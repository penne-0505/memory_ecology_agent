"""Persistence helpers for event-like records."""

from __future__ import annotations

import hashlib

from sqlalchemy.orm import Session

from app.adapters.clock import now_utc
from app.db.json_utils import json_dumps
from app.db.models import RawEvent
from app.schemas import RawEventInput


def persist_raw_event(session: Session, event_input: RawEventInput) -> RawEvent:
    happened_at = event_input.happened_at or now_utc()
    content_hash = hashlib.sha256(event_input.content_text.encode("utf-8")).hexdigest()
    raw_event = RawEvent(
        source_type=event_input.source_type,
        event_type=event_input.event_type,
        payload_json=json_dumps(event_input.payload),
        content_text=event_input.content_text,
        content_hash=content_hash,
        happened_at=happened_at,
    )
    session.add(raw_event)
    session.flush()
    return raw_event
