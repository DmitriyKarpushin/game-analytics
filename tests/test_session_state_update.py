from datetime import date, datetime
from unittest.mock import MagicMock
from uuid import UUID

from src.generators.sessions import SessionRecord
from src.storage.repositories import UserRepository


USER_ID = UUID(
    "00000000-0000-4000-8000-000000000001"
)


def test_update_session_activity_aggregates_sessions():
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value

    sessions = [
        SessionRecord(
            session_id=UUID(
                "00000000-0000-4000-8000-000000000011"
            ),
            user_id=USER_ID,
            session_start_ts=datetime(2026, 1, 1, 10, 0),
            session_end_ts=datetime(2026, 1, 1, 10, 10),
        ),
        SessionRecord(
            session_id=UUID(
                "00000000-0000-4000-8000-000000000012"
            ),
            user_id=USER_ID,
            session_start_ts=datetime(2026, 1, 1, 18, 0),
            session_end_ts=datetime(2026, 1, 1, 18, 20),
        ),
    ]

    repository = UserRepository(connection)

    repository.update_session_activity(
        sessions,
        date(2026, 1, 1),
    )

    cursor.executemany.assert_called_once()

    rows = cursor.executemany.call_args.args[1]

    assert rows == [
        (
            date(2026, 1, 1),
            datetime(2026, 1, 1, 18, 20),
            2,
            USER_ID,
        )
    ]


def test_update_session_activity_ignores_empty_sessions():
    connection = MagicMock()

    repository = UserRepository(connection)

    repository.update_session_activity(
        [],
        date(2026, 1, 1),
    )

    connection.cursor.assert_not_called()
