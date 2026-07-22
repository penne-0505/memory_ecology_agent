"""Web search interface and non-network stub."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.schemas import RawEventInput


@dataclass(frozen=True)
class WebSearchQuery:
    query: str
    rationale: str


class WebSearchAdapter:
    def search(self, queries: list[WebSearchQuery], settings: Settings) -> list[RawEventInput]:
        if len(queries) > settings.max_web_queries_per_cycle:
            queries = queries[: settings.max_web_queries_per_cycle]
        events: list[RawEventInput] = []
        for query in queries:
            if not query.rationale.strip():
                continue
            events.append(
                RawEventInput(
                    source_type="web_search",
                    event_type="web_search_stub",
                    payload={"query": query.query, "rationale": query.rationale},
                    content_text=(
                        "Web search is stubbed in this PoC. "
                        f"query={query.query!r}; rationale={query.rationale!r}"
                    ),
                )
            )
        return events
