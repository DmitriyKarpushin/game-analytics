from datetime import datetime
from unittest.mock import MagicMock
from uuid import UUID

from src.generators.events import EventRecord
from src.storage.repositories import EventRepository


def make_event():
    return EventRecord(
        event_id=UUID(
            "00000000-0000-4000-8000-000000000001"
        ),
        event_ts=datetime(2026, 1, 1, 10, 0),
        event_date=datetime(2026, 1, 1).date(),
        user_id=UUID(
            "00000000-0000-4000-8000-000000000002"
        ),
        session_id=UUID(
            "00000000-0000-4000-8000-000000000003"
        ),
        event_name="session_start",
        level_id=None,
        attempt_number=None,
        app_version="1.0",
        event_properties={},
    )


def test_insert_events_uses_executemany():
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value

    repository = EventRepository(connection)

    repository.insert_events([make_event()])

    cursor.executemany.assert_called_once()

    rows = cursor.executemany.call_args.args[1]

    assert len(rows) == 1
    assert rows[0][5] == "session_start"


def test_insert_events_does_nothing_for_empty_list():
    connection = MagicMock()

    repository = EventRepository(connection)

    repository.insert_events([])

    connection.cursor.assert_not_called()
