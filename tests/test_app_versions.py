from datetime import date, timedelta

import pytest

from src.config.loader import load_app_versions_config
from src.simulation.app_versions import AppVersionResolver


START_DATE = date(2026, 1, 1)


def make_resolver():
    return AppVersionResolver(
        start_date=START_DATE,
        config=load_app_versions_config(),
    )


def day(number: int) -> date:
    return START_DATE + timedelta(days=number - 1)


def test_version_schedule_boundaries():
    resolver = make_resolver()

    expected = {
        1: "1.0",
        59: "1.0",
        60: "1.1",
        119: "1.1",
        120: "1.2",
        159: "1.2",
        160: "1.3",
        250: "1.3",
    }

    for day_number, version in expected.items():
        assert (
            resolver.version_for_date(
                day(day_number)
            )
            == version
        )


def test_date_before_start_is_rejected():
    resolver = make_resolver()

    with pytest.raises(ValueError):
        resolver.version_for_date(
            START_DATE - timedelta(days=1)
        )


def test_android_low_tier_is_affected_on_1_2():
    resolver = make_resolver()

    assert resolver.engagement_multiplier(
        version="1.2",
        platform="android",
        device_tier="low",
    ) == pytest.approx(0.90)


def test_ios_low_tier_is_not_affected():
    resolver = make_resolver()

    assert resolver.engagement_multiplier(
        version="1.2",
        platform="ios",
        device_tier="low",
    ) == 1.0


def test_android_mid_tier_is_not_affected():
    resolver = make_resolver()

    assert resolver.engagement_multiplier(
        version="1.2",
        platform="android",
        device_tier="mid",
    ) == 1.0


def test_version_1_3_fixes_regression():
    resolver = make_resolver()

    assert resolver.engagement_multiplier(
        version="1.3",
        platform="android",
        device_tier="low",
    ) == 1.0
