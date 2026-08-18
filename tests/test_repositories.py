from datetime import date
from unittest.mock import MagicMock
from uuid import UUID

from src.storage.repositories import UserRepository


USER_ID = UUID(
    "00000000-0000-4000-8000-000000000001"
)


def test_fetch_returning_candidates():
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value

    cursor.fetchall.return_value = [
        (
            USER_ID,
            date(2026, 1, 1),
            date(2026, 1, 2),
            0.65,
            0.20,
            0.30,
            0.12,
            0.65,
            14.97,
            0.80,
            0.75,
            4,
            3,
            2,
            3,
        )
    ]

    repository = UserRepository(connection)

    candidates = repository.fetch_returning_candidates(
        date(2026, 1, 3)
    )

    assert len(candidates) == 1

    candidate = candidates[0]

    assert candidate.user_id == USER_ID
    assert candidate.registration_date == date(2026, 1, 1)
    assert candidate.last_active_date == date(2026, 1, 2)

    assert candidate.engagement_propensity == 0.65
    assert candidate.frustration_score == 0.20
    assert candidate.base_churn_propensity == 0.30
    assert candidate.payer_propensity == 0.12
    assert candidate.ad_tolerance == 0.65
    assert candidate.total_spend == 14.97
    assert candidate.recent_success == 0.80

    assert candidate.skill == 0.75
    assert candidate.current_level == 4
    assert candidate.total_levels_completed == 3
    assert candidate.total_levels_failed == 2
    assert candidate.next_attempt_number == 3

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
