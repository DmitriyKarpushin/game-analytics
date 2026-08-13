from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID

import numpy as np

from src.generators.sessions import SessionRecord


@dataclass(frozen=True)
class EventRecord:
    event_id: UUID
    event_ts: datetime
    event_date: date
    user_id: UUID
    session_id: UUID | None
    event_name: str
    level_id: int | None
    attempt_number: int | None
    app_version: str
    event_properties: dict = field(default_factory=dict)


class EventGenerator:
    def __init__(
        self,
        rng: np.random.Generator,
        app_version: str,
    ):
        self.rng = rng
        self.app_version = app_version

    def generate_session_events(
        self,
        sessions: list[SessionRecord],
    ) -> list[EventRecord]:
        events: list[EventRecord] = []

        for session in sessions:
            events.append(
                self._make_event(
                    event_ts=session.session_start_ts,
                    user_id=session.user_id,
                    session_id=session.session_id,
                    event_name="session_start",
                )
            )

            events.append(
                self._make_event(
                    event_ts=session.session_end_ts,
                    user_id=session.user_id,
                    session_id=session.session_id,
                    event_name="session_end",
                )
            )

        return sorted(
            events,
            key=lambda event: (
                event.event_ts,
                str(event.user_id),
                str(event.event_id),
            ),
        )

    def _make_event(
        self,
        event_ts: datetime,
        user_id: UUID,
        session_id: UUID | None,
        event_name: str,
    ) -> EventRecord:
        return EventRecord(
            event_id=self._generate_uuid(),
            event_ts=event_ts,
            event_date=event_ts.date(),
            user_id=user_id,
            session_id=session_id,
            event_name=event_name,
            level_id=None,
            attempt_number=None,
            app_version=self.app_version,
            event_properties={},
        )

    def _generate_uuid(self) -> UUID:
        return UUID(
            bytes=self.rng.bytes(16),
            version=4,
        )
