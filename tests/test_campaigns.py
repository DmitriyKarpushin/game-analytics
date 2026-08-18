from datetime import date, timedelta

import pytest

from src.config.loader import load_campaigns_config
from src.simulation.campaigns import CampaignResolver


START_DATE = date(2026, 1, 1)


def make_resolver():
    return CampaignResolver(
        start_date=START_DATE,
        config=load_campaigns_config(),
    )


def day(number: int) -> date:
    return START_DATE + timedelta(days=number - 1)


def test_no_campaign_before_tiktok():
    resolver = make_resolver()

    assert resolver.active_campaigns(day(34)) == []


def test_tiktok_campaign_boundaries():
    resolver = make_resolver()

    assert resolver.multiplier_for_channel(
        day(35),
        "tiktok",
    ) == pytest.approx(1.8)

    assert resolver.multiplier_for_channel(
        day(49),
        "tiktok",
    ) == pytest.approx(1.8)

    assert resolver.multiplier_for_channel(
        day(50),
        "tiktok",
    ) == pytest.approx(1.0)


def test_google_campaign_boundaries():
    resolver = make_resolver()

    assert resolver.multiplier_for_channel(
        day(80),
        "google_ads",
    ) == pytest.approx(1.5)

    assert resolver.multiplier_for_channel(
        day(94),
        "google_ads",
    ) == pytest.approx(1.5)

    assert resolver.multiplier_for_channel(
        day(95),
        "google_ads",
    ) == pytest.approx(1.0)


def test_campaign_does_not_affect_other_channel():
    resolver = make_resolver()

    assert resolver.multiplier_for_channel(
        day(40),
        "organic",
    ) == pytest.approx(1.0)


def test_campaign_id():
    resolver = make_resolver()

    assert resolver.campaign_id_for_channel(
        day(40),
        "tiktok",
    ) == "tiktok_growth_2026"

    assert resolver.campaign_id_for_channel(
        day(40),
        "google_ads",
    ) is None


def test_date_before_simulation_start_rejected():
    resolver = make_resolver()

    with pytest.raises(ValueError):
        resolver.active_campaigns(
            date(2025, 12, 31)
        )
