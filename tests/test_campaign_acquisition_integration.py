from datetime import date

import numpy as np
import pytest

from src.generators.users import UserGenerator
from src.simulation.daily_simulation import DailySimulation
from unittest.mock import MagicMock


def make_simulation():
    return DailySimulation(
        run_repository=MagicMock(),
        user_repository=MagicMock(),
        event_repository=MagicMock(),
        base_seed=42,
    )


def test_tiktok_campaign_increases_total_lambda():
    simulation = make_simulation()

    simulation_date = date(2026, 2, 9)  # Day 40.

    config = simulation.acquisition_config["new_users"]

    day_number = 39
    trend = 1.0 + day_number * config["daily_trend"]

    weekday_factor = config[
        "weekday_factors"
    ][simulation_date.strftime("%A").lower()]

    baseline = (
        config["base_lambda"]
        * trend
        * weekday_factor
    )

    # TikTok base share 0.20, campaign multiplier 1.8:
    # 0.80 * 1.0 + 0.20 * 1.8 = 1.16.
    expected = baseline * 1.16

    assert simulation._lambda_for_date(
        simulation_date
    ) == pytest.approx(expected)


def test_google_campaign_increases_total_lambda():
    simulation = make_simulation()

    # Day 85.
    simulation_date = date(2026, 3, 26)

    assert simulation._campaign_factor_for_date(
        simulation_date
    ) == pytest.approx(1.125)


def test_no_campaign_has_factor_one():
    simulation = make_simulation()

    assert simulation._campaign_factor_for_date(
        date(2026, 1, 20)
    ) == pytest.approx(1.0)


def test_tiktok_campaign_changes_channel_weight():
    simulation = make_simulation()

    weights = simulation._channel_weights_for_date(
        date(2026, 2, 9)
    )

    assert weights["tiktok"] == pytest.approx(
        0.20 * 1.8
    )

    assert sum(weights.values()) == pytest.approx(
        1.16
    )


def test_user_generator_assigns_campaign_id():
    generator = UserGenerator(
        rng=np.random.default_rng(42),
        channel_weights={
            "tiktok": 1.0,
        },
        campaign_by_channel={
            "tiktok": "tiktok_growth_2026",
        },
    )

    users, _ = generator.generate(
        count=20,
        registration_date=date(2026, 2, 9),
    )

    assert {
        user.acquisition_channel
        for user in users
    } == {"tiktok"}

    assert {
        user.campaign_id
        for user in users
    } == {"tiktok_growth_2026"}


def test_user_generator_normalizes_dynamic_weights():
    generator = UserGenerator(
        rng=np.random.default_rng(42),
        channel_weights={
            "organic": 0.30,
            "tiktok": 0.36,
        },
    )

    users, _ = generator.generate(
        count=100,
        registration_date=date(2026, 2, 9),
    )

    assert len(users) == 100

    assert {
        user.acquisition_channel
        for user in users
    }.issubset(
        {"organic", "tiktok"}
    )
