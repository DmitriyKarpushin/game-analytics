from unittest.mock import MagicMock

import pytest

from src.simulation.daily_simulation import DailySimulation


def make_simulation():
    return DailySimulation(
        run_repository=MagicMock(),
        user_repository=MagicMock(),
        event_repository=MagicMock(),
    )


def test_version_1_2_reduces_android_low_engagement():
    simulation = make_simulation()

    result = simulation._effective_engagement(
        engagement=0.80,
        app_version="1.2",
        platform="android",
        device_tier="low",
    )

    assert result == pytest.approx(0.72)


def test_version_1_2_does_not_affect_android_mid():
    simulation = make_simulation()

    result = simulation._effective_engagement(
        engagement=0.80,
        app_version="1.2",
        platform="android",
        device_tier="mid",
    )

    assert result == pytest.approx(0.80)


def test_version_1_2_does_not_affect_ios_low():
    simulation = make_simulation()

    result = simulation._effective_engagement(
        engagement=0.80,
        app_version="1.2",
        platform="ios",
        device_tier="low",
    )

    assert result == pytest.approx(0.80)


def test_version_1_3_restores_android_low_engagement():
    simulation = make_simulation()

    result = simulation._effective_engagement(
        engagement=0.80,
        app_version="1.3",
        platform="android",
        device_tier="low",
    )

    assert result == pytest.approx(0.80)
