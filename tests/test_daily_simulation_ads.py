from datetime import date
from unittest.mock import MagicMock

from src.simulation.daily_simulation import DailySimulation


def test_daily_simulation_generates_ad_pairs():
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

    # Keep the test small and deterministic.
    simulation._generate_new_users_count = (
        lambda simulation_date, rng: 20
    )

    ads_config = simulation.monetization_config["ads"]

    # Force one rewarded + one interstitial
    # for every real session.
    ads_config["rewarded"]["base_probability"] = 1.0
    ads_config["rewarded"]["ad_tolerance_weight"] = 0.0
    ads_config["rewarded"]["engagement_weight"] = 0.0
    ads_config["rewarded"]["max_probability"] = 1.0

    ads_config["interstitial"]["base_probability"] = 1.0
    ads_config["interstitial"]["ad_tolerance_weight"] = 0.0
    ads_config["interstitial"]["min_probability"] = 0.0

    result = simulation.run(
        date(2026, 1, 1)
    )

    events = (
        event_repository
        .insert_events
        .call_args
        .args[0]
    )

    impressions = [
        event
        for event in events
        if event.event_name == "ad_impression"
    ]

    revenues = [
        event
        for event in events
        if event.event_name == "ad_revenue"
    ]

    session_starts = {
        (
            event.user_id,
            event.session_id,
        )
        for event in events
        if event.event_name == "session_start"
    }

    assert result.sessions_created > 0

    # Two formats per session:
    # rewarded + interstitial.
    assert len(impressions) == (
        result.sessions_created * 2
    )

    assert len(revenues) == (
        result.sessions_created * 2
    )

    assert {
        event.event_properties["ad_format"]
        for event in impressions
    } == {
        "rewarded",
        "interstitial",
    }

    for event in impressions + revenues:
        assert (
            event.user_id,
            event.session_id,
        ) in session_starts

        assert (
            event.event_properties["revenue_usd"]
            > 0
        )

    impression_keys = {
        (
            event.user_id,
            event.session_id,
            event.event_properties["ad_format"],
        )
        for event in impressions
    }

    revenue_keys = {
        (
            event.user_id,
            event.session_id,
            event.event_properties["ad_format"],
        )
        for event in revenues
    }

    assert impression_keys == revenue_keys
