from unittest.mock import MagicMock

from src.storage.levels import LevelRecord, LevelRepository


def test_upsert_levels():
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value

    levels = [
        LevelRecord(
            level_id=1,
            base_difficulty=0.26,
            energy_cost=5,
            reward_coins=22,
            base_duration_sec=92,
        )
    ]

    repository = LevelRepository(connection)
    repository.upsert_levels(levels)

    cursor.executemany.assert_called_once()

    rows = cursor.executemany.call_args.args[1]

    assert rows == [
        (1, 0.26, 5, 22, 92)
    ]


def test_upsert_levels_ignores_empty_list():
    connection = MagicMock()

    repository = LevelRepository(connection)
    repository.upsert_levels([])

    connection.cursor.assert_not_called()
