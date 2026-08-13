from unittest.mock import MagicMock
from uuid import UUID

from src.storage.repositories import (
    GameplayStateUpdate,
    UserRepository,
)


USER_ID = UUID(
    "00000000-0000-4000-8000-000000000001"
)


def test_update_gameplay_state():
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value

    repository = UserRepository(connection)

    repository.update_gameplay_state(
        [
            GameplayStateUpdate(
                user_id=USER_ID,
                current_level=5,
                frustration_score=0.25,
                total_levels_completed=4,
                total_levels_failed=3,
            )
        ]
    )

    cursor.executemany.assert_called_once()

    rows = cursor.executemany.call_args.args[1]

    assert rows == [
        (
            5,
            0.25,
            4,
            3,
            USER_ID,
        )
    ]


def test_update_gameplay_state_ignores_empty_list():
    connection = MagicMock()

    repository = UserRepository(connection)

    repository.update_gameplay_state([])

    connection.cursor.assert_not_called()
