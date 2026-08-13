from datetime import date
from unittest.mock import MagicMock
from uuid import UUID

import numpy as np
import pytest

from src.simulation.daily_simulation import DailySimulation
from src.storage.repositories import ReturningUserCandidate


def make_simulation(base_seed=42):
    run_repository = MagicMock()
    user_repository = MagicMock()
    user_repository.fetch_returning_candidates.return_value = []

    simulation = DailySimulation(
        run_repository=run_repository,
        user_repository=user_repository,
        base_seed=base_seed,
    )

    return simulation, run_repository, user_repository


def make_candidate(
    user_id: str,
    engagement: float = 0.5,
    frustration: float = 0.2,
    churn: float = 0.3,
):
    return ReturningUserCandidate(
        user_id=UUID(user_id),
        registration_date=date(2026, 1, 1),
        last_active_date=date(2026, 1, 1),
        engagement_propensity=engagement,
        frustration_score=frustration,
        base_churn_propensity=churn,
    )


def test_same_date_and_base_seed_produce_same_seed():
    simulation_1, _, _ = make_simulation()
    simulation_2, _, _ = make_simulation()

    date_ = date(2026, 1, 1)

    assert (
        simulation_1._seed_for_date(date_)
        == simulation_2._seed_for_date(date_)
    )


def test_different_dates_produce_different_seeds():
    simulation, _, _ = make_simulation()

    seed_1 = simulation._seed_for_date(date(2026, 1, 1))
    seed_2 = simulation._seed_for_date(date(2026, 1, 2))

    assert seed_1 != seed_2


def test_base_lambda_on_start_date():
    simulation, _, _ = make_simulation()

    lambda_day = simulation._lambda_for_date(
        date(2026, 1, 1)
    )

    assert lambda_day == pytest.approx(450.0)


def test_weekend_and_trend_affect_lambda():
    simulation, _, _ = make_simulation()

    lambda_day = simulation._lambda_for_date(
        date(2026, 1, 3)
    )

    expected = 450 * (1 + 2 * 0.0015) * 1.20

    assert lambda_day == pytest.approx(expected)


def test_date_before_start_date_is_rejected():
    simulation, _, _ = make_simulation()

    with pytest.raises(ValueError):
        simulation._lambda_for_date(date(2025, 12, 31))


def test_returning_selection_is_reproducible():
    simulation, _, _ = make_simulation()

    candidates = [
        make_candidate(
            "00000000-0000-4000-8000-000000000001"
        ),
        make_candidate(
            "00000000-0000-4000-8000-000000000002"
        ),
        make_candidate(
            "00000000-0000-4000-8000-000000000003"
        ),
    ]

    result_1 = simulation._select_returning_active_users(
        candidates,
        date(2026, 1, 2),
        np.random.default_rng(42),
    )

    result_2 = simulation._select_returning_active_users(
        candidates,
        date(2026, 1, 2),
        np.random.default_rng(42),
    )

    assert result_1 == result_2


def test_returning_selection_returns_subset():
    simulation, _, _ = make_simulation()

    candidates = [
        make_candidate(
            "00000000-0000-4000-8000-000000000001"
        ),
        make_candidate(
            "00000000-0000-4000-8000-000000000002"
        ),
    ]

    active = simulation._select_returning_active_users(
        candidates,
        date(2026, 1, 2),
        np.random.default_rng(42),
    )

    assert set(active).issubset(set(candidates))


def test_run_generates_users_and_checks_returning_users():
    simulation, run_repository, user_repository = (
        make_simulation()
    )

    date_ = date(2026, 1, 1)

    result = simulation.run(date_)

    run_repository.ensure_date_can_run.assert_called_once_with(
        date_
    )

    user_repository.fetch_returning_candidates.assert_called_once_with(
        date_
    )

    assert result.users_created > 0
    assert result.returning_active_users == 0
    assert result.events_created == 0

    user_repository.insert_users.assert_called_once()
    user_repository.insert_states.assert_called_once()

    users = user_repository.insert_users.call_args.args[0]
    states = user_repository.insert_states.call_args.args[0]

    assert len(users) == result.users_created
    assert len(states) == result.users_created

    run_repository.mark_success.assert_called_once_with(
        simulation_date=date_,
        users_created=result.users_created,
        events_created=0,
    )
