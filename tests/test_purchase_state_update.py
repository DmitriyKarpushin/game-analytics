from datetime import date, datetime
from unittest.mock import MagicMock
from uuid import UUID

from src.generators.events import EventRecord
from src.storage.repositories import UserRepository


USER_ID = UUID(
    "00000000-0000-4000-8000-000000000001"
)

EVENT_ID = UUID(
    "00000000-0000-4000-8000-000000000002"
)


def make_purchase_event():
    return EventRecord(
        event_id=EVENT_ID,
        event_ts=datetime(2026, 1, 1, 12, 0),
        event_date=date(2026, 1, 1),
        user_id=USER_ID,
        session_id=None,
        event_name="purchase",
        level_id=None,
        attempt_number=None,
        app_version="1.0",
        event_properties={
            "sku": "coins_standard",
            "price_usd": 4.99,
            "currency": "USD",
        },
    )


def test_update_purchase_spend():
    connection = MagicMock()
    cursor = (
        connection
        .cursor
        .return_value
        .__enter__
        .return_value
    )

    repository = UserRepository(connection)

    repository.update_purchase_spend(
        [make_purchase_event()]
    )

    cursor.executemany.assert_called_once()

    rows = cursor.executemany.call_args.args[1]

    assert rows == [
        (4.99, USER_ID)
    ]


def test_update_purchase_spend_ignores_empty_list():
    connection = MagicMock()

    repository = UserRepository(connection)

    repository.update_purchase_spend([])

    connection.cursor.assert_not_called()
