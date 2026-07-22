"""Simple scheduler representation for wake requests."""

from __future__ import annotations

from app.adapters.clock import now_utc
from app.db.models import WakeRequest


def should_run_wake(request: WakeRequest) -> bool:
    if request.not_before is None:
        return True
    return request.not_before <= now_utc()
