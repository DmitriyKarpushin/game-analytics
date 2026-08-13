from datetime import datetime
from uuid import UUID

import numpy as np

from src.generators.events import EventGenerator
from src.generators.sessions import SessionRecord


USER_ID = UUID(
    "00000000-0000-4000-8000-000000000001"
)

SESSION_ID = UUID(
    "00000000-0000-4000-8000-000000000002"
)


def make_session():
    return SessionRecord(
        session_id=SESSION_ID,
        user_id=USER_ID,
        session_start_ts=datetime(
            2026, 1, 1, 10, 0
        ),
        session_end_ts=datetime(
            2026, 1, 1, 10, 12
        ),
    )


def make_generator(seed=42):
    return EventGenerator(
        rng=np.random.default_rng(seed),
        app_version="1.0",
    )


def test_session_generates_start_and_end_events():
    events = make_generator().generate_session_events(
        [make_session()]
    )

    assert len(events) == 2
    assert [event.event_name for event in events] == [
        "session_start",
        "session_end",
    ]


def test_session_events_share_user_and_session():
    events = make_generator().generate_session_events(
        [make_session()]
    )

    for event in events:
        assert event.user_id == USER_ID
        assert event.session_id == SESSION_ID


def test_event_timestamps_match_session():
    session = make_session()

    events = make_generator().generate_session_events(
        [session]
    )

    assert events[0].event_ts == session.session_start_ts
    assert events[1].event_ts == session.session_end_ts

    assert events[0].event_date == session.session_start_ts.date()
    assert events[1].event_date == session.session_end_ts.date()


def test_session_events_have_no_level_data():
    events = make_generator().generate_session_events(
        [make_session()]
    )

    for event in events:
        assert event.level_id is None
        assert event.attempt_number is None


def test_event_ids_are_unique():
    events = make_generator().generate_session_events(
        [make_session()]
    )

    ids = [event.event_id for event in events]

    assert len(ids) == len(set(ids))


def test_generation_is_reproducible():
    session = make_session()

    events_1 = make_generator(42).generate_session_events(
        [session]
    )
    events_2 = make_generator(42).generate_session_events(
        [session]
    )

    assert events_1 == events_2
