from copy import deepcopy
from datetime import datetime
from uuid import UUID

import numpy as np

from src.config.loader import load_monetization_config
from src.generators.ads import AdGenerator, AdUser
from src.generators.sessions import SessionRecord


USER_ID = UUID(
    "00000000-0000-4000-8000-000000000001"
)

SESSION_ID = UUID(
    "00000000-0000-4000-8000-000000000002"
)


def make_generator(seed=42, config=None):
    if config is None:
        config = deepcopy(
            load_monetization_config()["ads"]
        )

    return AdGenerator(
        rng=np.random.default_rng(seed),
        ads_config=config,
        app_version="1.0",
    )


def make_session():
    return SessionRecord(
        session_id=SESSION_ID,
        user_id=USER_ID,
        session_start_ts=datetime(
            2026, 1, 1, 10, 0
        ),
        session_end_ts=datetime(
            2026, 1, 1, 10, 15
        ),
    )


def test_rewarded_probability_increases_with_tolerance():
    generator = make_generator()

    low = generator.rewarded_probability(
        ad_tolerance=0.1,
        engagement_propensity=0.5,
    )

    high = generator.rewarded_probability(
        ad_tolerance=0.9,
        engagement_propensity=0.5,
    )

    assert high > low


def test_rewarded_probability_increases_with_engagement():
    generator = make_generator()

    low = generator.rewarded_probability(
        ad_tolerance=0.5,
        engagement_propensity=0.1,
    )

    high = generator.rewarded_probability(
        ad_tolerance=0.5,
        engagement_propensity=0.9,
    )

    assert high > low


def test_interstitial_probability_decreases_with_tolerance():
    generator = make_generator()

    low_tolerance = generator.interstitial_probability(
        ad_tolerance=0.1
    )

    high_tolerance = generator.interstitial_probability(
        ad_tolerance=0.9
    )

    assert low_tolerance > high_tolerance


def test_no_sessions_means_no_ads():
    generator = make_generator()

    events = generator.generate_for_user(
        AdUser(
            user_id=USER_ID,
            engagement_propensity=0.5,
            ad_tolerance=0.5,
        ),
        [],
    )

    assert events == []


def test_forced_ads_create_impression_revenue_pairs():
    config = deepcopy(
        load_monetization_config()["ads"]
    )

    config["rewarded"]["base_probability"] = 1.0
    config["rewarded"]["ad_tolerance_weight"] = 0.0
    config["rewarded"]["engagement_weight"] = 0.0
    config["rewarded"]["max_probability"] = 1.0

    config["interstitial"]["base_probability"] = 1.0
    config["interstitial"]["ad_tolerance_weight"] = 0.0
    config["interstitial"]["min_probability"] = 0.0

    events = make_generator(
        config=config
    ).generate_for_user(
        AdUser(
            user_id=USER_ID,
            engagement_propensity=0.5,
            ad_tolerance=0.5,
        ),
        [make_session()],
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

    assert len(impressions) == 2
    assert len(revenues) == 2

    assert {
        event.event_properties["ad_format"]
        for event in impressions
    } == {
        "rewarded",
        "interstitial",
    }


def test_ad_events_are_inside_session():
    config = deepcopy(
        load_monetization_config()["ads"]
    )

    config["rewarded"]["base_probability"] = 1.0
    config["rewarded"]["ad_tolerance_weight"] = 0.0
    config["rewarded"]["engagement_weight"] = 0.0
    config["rewarded"]["max_probability"] = 1.0

    config["interstitial"]["base_probability"] = 0.0
    config["interstitial"]["ad_tolerance_weight"] = 0.0
    config["interstitial"]["min_probability"] = 0.0

    session = make_session()

    events = make_generator(
        config=config
    ).generate_for_user(
        AdUser(
            user_id=USER_ID,
            engagement_propensity=0.5,
            ad_tolerance=0.5,
        ),
        [session],
    )

    for event in events:
        assert (
            session.session_start_ts
            <= event.event_ts
            <= session.session_end_ts
        )

        assert event.session_id == SESSION_ID
        assert event.user_id == USER_ID


def test_generation_is_reproducible():
    config = deepcopy(
        load_monetization_config()["ads"]
    )

    user = AdUser(
        user_id=USER_ID,
        engagement_propensity=0.8,
        ad_tolerance=0.8,
    )

    sessions = [make_session()]

    result_1 = make_generator(
        seed=42,
        config=config,
    ).generate_for_user(
        user,
        sessions,
    )

    result_2 = make_generator(
        seed=42,
        config=config,
    ).generate_for_user(
        user,
        sessions,
    )

    assert result_1 == result_2
