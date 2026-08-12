from datetime import date

import numpy as np

from src.generators.users import UserGenerator


def test_generate_returns_requested_count():
    generator = UserGenerator(np.random.default_rng(42))

    users, states = generator.generate(
        count=10,
        registration_date=date(2026, 1, 1),
    )

    assert len(users) == 10
    assert len(states) == 10


def test_user_and_state_ids_match():
    generator = UserGenerator(np.random.default_rng(42))

    users, states = generator.generate(
        count=10,
        registration_date=date(2026, 1, 1),
    )

    for user, state in zip(users, states):
        assert user.user_id == state.user_id


def test_registration_date_is_correct():
    simulation_date = date(2026, 1, 1)
    generator = UserGenerator(np.random.default_rng(42))

    users, _ = generator.generate(
        count=50,
        registration_date=simulation_date,
    )

    assert all(
        user.registration_ts.date() == simulation_date
        for user in users
    )


def test_latent_parameters_are_in_valid_range():
    generator = UserGenerator(np.random.default_rng(42))

    _, states = generator.generate(
        count=1000,
        registration_date=date(2026, 1, 1),
    )

    for state in states:
        assert 0 <= state.skill <= 1
        assert 0 <= state.engagement_propensity <= 1
        assert 0 <= state.payer_propensity <= 1
        assert 0 <= state.ad_tolerance <= 1
        assert 0 <= state.base_churn_propensity <= 1
        assert 0 <= state.frustration_score <= 1


def test_initial_state():
    generator = UserGenerator(np.random.default_rng(42))

    _, states = generator.generate(
        count=10,
        registration_date=date(2026, 1, 1),
    )

    for state in states:
        assert state.current_level == 1
        assert state.total_sessions == 0
        assert state.total_levels_completed == 0
        assert state.total_levels_failed == 0
        assert state.total_spend == 0
        assert state.is_churned is False


def test_generation_is_reproducible():
    date_ = date(2026, 1, 1)

    generator_1 = UserGenerator(np.random.default_rng(42))
    generator_2 = UserGenerator(np.random.default_rng(42))

    users_1, states_1 = generator_1.generate(20, date_)
    users_2, states_2 = generator_2.generate(20, date_)

    assert users_1 == users_2
    assert states_1 == states_2
