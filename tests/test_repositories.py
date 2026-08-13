from datetime import date
from unittest.mock import MagicMock
from uuid import UUID

from src.storage.repositories import UserRepository


def test_fetch_returning_candidates():
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value

    user_id = UUID("00000000-0000-4000-8000-000000000001")

    cursor.fetchall.return_value = [
        (
            user_id,
            date(2026, 1, 1),
            date(2026, 1, 2),
            0.65,
            0.20,
            0.30,
        )
    ]

    repository = UserRepository(connection)

    candidates = repository.fetch_returning_candidates(
        date(2026, 1, 3)
    )

    assert len(candidates) == 1

    candidate = candidates[0]

    assert candidate.user_id == user_id
    assert candidate.registration_date == date(2026, 1, 1)
    assert candidate.last_active_date == date(2026, 1, 2)
    assert candidate.engagement_propensity == 0.65
    assert candidate.frustration_score == 0.20
    assert candidate.base_churn_propensity == 0.30

    cursor.execute.assert_called_once()
    assert cursor.execute.call_args.args[1] == (
        date(2026, 1, 3),
    )


def test_fetch_returning_candidates_can_be_empty():
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = []

    repository = UserRepository(connection)

    candidates = repository.fetch_returning_candidates(
        date(2026, 1, 1)
    )

    assert candidates == []
