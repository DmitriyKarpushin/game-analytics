from datetime import date
from unittest.mock import MagicMock
from uuid import UUID

from src.simulation.daily_simulation import DailySimulation
from src.storage.repositories import ReturningUserCandidate


def test_missing_recent_success_uses_default(monkeypatch):
    captured_recent_success = []

    class FakeActivitySelector:
        def __init__(self, rng, activity_config):
            pass

        def is_active(self, state, simulation_date):
            captured_recent_success.append(
                state.recent_success
            )
            return True

    monkeypatch.setattr(
        "src.simulation.daily_simulation.UserActivitySelector",
        FakeActivitySelector,
    )

    simulation = DailySimulation(
        run_repository=MagicMock(),
        user_repository=MagicMock(),
        event_repository=MagicMock(),
    )

    candidate = ReturningUserCandidate(
        user_id=UUID(
            "00000000-0000-4000-8000-000000000001"
        ),
        registration_date=date(2026, 1, 1),
        last_active_date=date(2026, 1, 1),
        engagement_propensity=0.5,
        frustration_score=0.2,
        base_churn_propensity=0.3,
        recent_success=None,
    )

    active = simulation._select_returning_active_users(
        candidates=[candidate],
        simulation_date=date(2026, 1, 2),
        rng=MagicMock(),
        app_version="1.0",
    )

    assert active == [candidate]

    assert captured_recent_success == [
        simulation.game_config["activity"][
            "default_recent_success"
        ]
    ]
