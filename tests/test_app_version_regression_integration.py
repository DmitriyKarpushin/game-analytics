from datetime import date
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from src.simulation.daily_simulation import DailySimulation
from src.storage.repositories import ReturningUserCandidate


USER_ID = UUID(
    "00000000-0000-4000-8000-000000000001"
)


def test_version_1_2_regression_reaches_returning_session_pipeline(
    monkeypatch,
):
    captured_engagement = []

    class FakeActivitySelector:
        def __init__(self, rng, activity_config):
            pass

        def is_active(self, state, simulation_date):
            return True

    class FakeSessionGenerator:
        def __init__(self, rng, session_config):
            pass

        def generate_for_user(
            self,
            user,
            simulation_date,
        ):
            captured_engagement.append(
                user.engagement_propensity
            )
            return []

    monkeypatch.setattr(
        "src.simulation.daily_simulation.UserActivitySelector",
        FakeActivitySelector,
    )

    monkeypatch.setattr(
        "src.simulation.daily_simulation.SessionGenerator",
        FakeSessionGenerator,
    )

    run_repository = MagicMock()
    user_repository = MagicMock()
    event_repository = MagicMock()

    user_repository.fetch_returning_candidates.return_value = [
        ReturningUserCandidate(
            user_id=USER_ID,
            registration_date=date(2026, 1, 1),
            last_active_date=date(2026, 4, 29),
            engagement_propensity=0.80,
            frustration_score=0.10,
            base_churn_propensity=0.20,
            payer_propensity=0.10,
            ad_tolerance=0.50,
            total_spend=0.0,
            recent_success=0.60,
            skill=0.50,
            current_level=5,
            total_levels_completed=4,
            total_levels_failed=2,
            next_attempt_number=1,
            platform="android",
            device_tier="low",
        )
    ]

    simulation = DailySimulation(
        run_repository=run_repository,
        user_repository=user_repository,
        event_repository=event_repository,
        base_seed=42,
    )

    simulation._generate_new_users_count = (
        lambda simulation_date, rng: 0
    )

    # Day 120 -> version 1.2.
    simulation.run(
        date(2026, 4, 30)
    )

    assert captured_engagement == [
        pytest.approx(0.72)
    ]
