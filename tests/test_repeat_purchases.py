from copy import deepcopy
from datetime import datetime
from uuid import UUID

import numpy as np

from src.config.loader import load_monetization_config
from src.generators.purchases import (
    PurchaseGenerator,
    PurchaseUser,
)
from src.generators.sessions import SessionRecord


USER_ID = UUID(
    "00000000-0000-4000-8000-000000000001"
)

SESSION_ID = UUID(
    "00000000-0000-4000-8000-000000000002"
)


def make_session():
    return SessionRecord(
        session_id=SESSION_ID,
        user_id=USER_ID,
        session_start_ts=datetime(
            2026, 1, 1, 10, 0
        ),
        session_end_ts=datetime(
            2026, 1, 1, 10, 30
        ),
    )


def make_generator(config=None):
    if config is None:
        config = deepcopy(
            load_monetization_config()["purchase"]
        )

    return PurchaseGenerator(
        rng=np.random.default_rng(42),
        purchase_config=config,
        app_version="1.0",
    )


def test_existing_payer_has_higher_daily_probability():
    generator = make_generator()

    first_purchase = generator.purchase_probability(
        payer_propensity=0.5,
        has_purchased=False,
    )

    repeat_purchase = generator.purchase_probability(
        payer_propensity=0.5,
        has_purchased=True,
    )

    assert repeat_purchase > first_purchase


def test_first_purchase_day_creates_only_one_purchase():
    config = deepcopy(
        load_monetization_config()["purchase"]
    )

    config["base_daily_probability"] = 1.0
    config["payer_propensity_weight"] = 0.0

    events = make_generator(config).generate_for_user(
        PurchaseUser(
            user_id=USER_ID,
            payer_propensity=1.0,
            total_spend=0.0,
        ),
        [make_session()],
    )

    assert len(events) == 1


def test_repeat_payer_can_make_multiple_purchases():
    config = deepcopy(
        load_monetization_config()["purchase"]
    )

    config["repeat_base_daily_probability"] = 1.0
    config["repeat_payer_propensity_weight"] = 0.0
    config["repeat_purchase_count_lambda"] = 100.0
    config["max_purchases_per_day"] = 3

    events = make_generator(config).generate_for_user(
        PurchaseUser(
            user_id=USER_ID,
            payer_propensity=1.0,
            total_spend=4.99,
        ),
        [make_session()],
    )

    assert len(events) == 3


def test_repeat_purchase_events_are_inside_sessions():
    config = deepcopy(
        load_monetization_config()["purchase"]
    )

    config["repeat_base_daily_probability"] = 1.0
    config["repeat_payer_propensity_weight"] = 0.0
    config["repeat_purchase_count_lambda"] = 100.0
    config["max_purchases_per_day"] = 3

    session = make_session()

    events = make_generator(config).generate_for_user(
        PurchaseUser(
            user_id=USER_ID,
            payer_propensity=1.0,
            total_spend=9.99,
        ),
        [session],
    )

    for event in events:
        assert (
            session.session_start_ts
            <= event.event_ts
            <= session.session_end_ts
        )
        assert event.user_id == USER_ID
        assert event.session_id == SESSION_ID
