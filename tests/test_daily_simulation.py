from datetime import date
from unittest.mock import MagicMock

from src.simulation.daily_simulation import DailySimulation


def test_same_date_and_base_seed_produce_same_seed():
    repository = MagicMock()

    simulation_1 = DailySimulation(repository, base_seed=42)
    simulation_2 = DailySimulation(repository, base_seed=42)

    date_ = date(2026, 1, 1)

    assert simulation_1._seed_for_date(date_) == simulation_2._seed_for_date(date_)


def test_different_dates_produce_different_seeds():
    repository = MagicMock()
    simulation = DailySimulation(repository, base_seed=42)

    seed_1 = simulation._seed_for_date(date(2026, 1, 1))
    seed_2 = simulation._seed_for_date(date(2026, 1, 2))

    assert seed_1 != seed_2


def test_run_tracks_simulation():
    repository = MagicMock()
    simulation = DailySimulation(repository, base_seed=42)

    date_ = date(2026, 1, 1)

    result = simulation.run(date_)

    repository.ensure_date_can_run.assert_called_once_with(date_)
    repository.start.assert_called_once_with(
        simulation_date=date_,
        seed=result.seed,
    )
    repository.mark_success.assert_called_once_with(
        simulation_date=date_,
        users_created=0,
        events_created=0,
    )

    assert result.simulation_date == date_
    assert result.users_created == 0
    assert result.events_created == 0
