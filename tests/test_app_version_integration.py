from datetime import date
from unittest.mock import MagicMock

import numpy as np

from src.generators.users import UserGenerator
from src.simulation.daily_simulation import DailySimulation


def test_user_generator_uses_supplied_app_version():
    generator = UserGenerator(
        rng=np.random.default_rng(42),
        app_version="1.2",
    )

    users, _ = generator.generate(
        count=10,
        registration_date=date(2026, 4, 30),
    )

    assert {
        user.initial_app_version
        for user in users
    } == {"1.2"}


def test_daily_simulation_uses_current_version_for_users_and_events():
    run_repository = MagicMock()
    user_repository = MagicMock()
    event_repository = MagicMock()

    user_repository.fetch_returning_candidates.return_value = []

    simulation = DailySimulation(
        run_repository=run_repository,
        user_repository=user_repository,
        event_repository=event_repository,
        base_seed=42,
    )

    simulation._generate_new_users_count = (
        lambda simulation_date, rng: 20
    )

    # Day 120 of the simulation -> app version 1.2.
    simulation.run(
        date(2026, 4, 30)
    )

    users = (
        user_repository
        .insert_users
        .call_args
        .args[0]
    )

    events = (
        event_repository
        .insert_events
        .call_args
        .args[0]
    )

    assert {
        user.initial_app_version
        for user in users
    } == {"1.2"}

    assert len(events) > 0

    assert {
        event.app_version
        for event in events
    } == {"1.2"}
