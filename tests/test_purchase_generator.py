from copy import deepcopy
from datetime import datetime
from uuid import UUID

import numpy as np
import pytest

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


def make_config(force_purchase=False):
    config = deepcopy(
        load_monetization_config()["purchase"]
    )

    if force_purchase:
        config["base_daily_probability"] = 1.0
        config["payer_propensity_weight"] = 0.0

    return config


def make_generator(seed=42, force_purchase=False):
    return PurchaseGenerator(
        rng=np.random.default_rng(seed),
        purchase_config=make_config(force_purchase),
        app_version="1.0",
    )


def make_user(payer_propensity=0.5):
    return PurchaseUser(
        user_id=USER_ID,
        payer_propensity=payer_propensity,
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


def test_purchase_probability_for_zero_propensity():
    generator = make_generator()

    assert generator.purchase_probability(
        0.0
    ) == pytest.approx(0.002)


def test_purchase_probability_for_max_propensity():
    generator = make_generator()

    assert generator.purchase_probability(
        1.0
    ) == pytest.approx(0.052)


def test_no_sessions_means_no_purchase():
    generator = make_generator(
        force_purchase=True
    )

    assert generator.generate_for_user(
        make_user(),
        [],
    ) == []


def test_forced_purchase_creates_one_event():
    generator = make_generator(
        force_purchase=True
    )

    events = generator.generate_for_user(
        make_user(),
        [make_session()],
    )

    assert len(events) == 1
    assert events[0].event_name == "purchase"


def test_purchase_event_is_inside_session():
    session = make_session()

    event = make_generator(
        force_purchase=True
    ).generate_for_user(
        make_user(),
        [session],
    )[0]

    assert (
        session.session_start_ts
        <= event.event_ts
        <= session.session_end_ts
    )

    assert event.session_id == session.session_id
    assert event.user_id == USER_ID


def test_purchase_has_valid_product_properties():
    config = make_config(
        force_purchase=True
    )

    event = PurchaseGenerator(
        rng=np.random.default_rng(42),
        purchase_config=config,
        app_version="1.0",
    ).generate_for_user(
        make_user(),
        [make_session()],
    )[0]

    prices = {
        float(product["price_usd"])
        for product in config["products"]
    }

    assert event.event_properties["sku"]
    assert event.event_properties["currency"] == "USD"
    assert event.event_properties["price_usd"] in prices


def test_generation_is_reproducible():
    user = make_user()
    sessions = [make_session()]

    result_1 = make_generator(
        seed=42,
        force_purchase=True,
    ).generate_for_user(
        user,
        sessions,
    )

    result_2 = make_generator(
        seed=42,
        force_purchase=True,
    ).generate_for_user(
        user,
        sessions,
    )

    assert result_1 == result_2
