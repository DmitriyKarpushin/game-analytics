from datetime import date
from uuid import uuid4

import numpy as np

from src.config.loader import load_game_config
from src.simulation.user_state import (
    ReturningUserState,
    UserActivitySelector,
)


def make_user(**overrides):
    values = {
        "user_id": uuid4(),
        "registration_date": date(2026, 1, 1),
        "last_active_date": date(2026, 1, 1),
        "engagement_propensity": 0.5,
        "frustration_score": 0.2,
        "base_churn_propensity": 0.3,
        "recent_success": 0.5,
    }
    values.update(overrides)

    return ReturningUserState(**values)


def make_selector():
    config = load_game_config()["activity"]

    return UserActivitySelector(
        rng=np.random.default_rng(42),
        activity_config=config,
    )


def test_probability_is_between_configured_limits():
    selector = make_selector()

    probability = selector.activity_probability(
        make_user(),
        date(2026, 1, 2),
    )

    assert 0.001 <= probability <= 0.98


def test_higher_engagement_increases_activity_probability():
    selector = make_selector()

    low = make_user(engagement_propensity=0.2)
    high = make_user(engagement_propensity=0.8)

    assert (
        selector.activity_probability(high, date(2026, 1, 2))
        > selector.activity_probability(low, date(2026, 1, 2))
    )


def test_frustration_reduces_activity_probability():
    selector = make_selector()

    low = make_user(frustration_score=0.1)
    high = make_user(frustration_score=0.9)

    assert (
        selector.activity_probability(low, date(2026, 1, 2))
        > selector.activity_probability(high, date(2026, 1, 2))
    )


def test_inactivity_reduces_return_probability():
    selector = make_selector()

    user = make_user()

    day_1 = selector.activity_probability(
        user,
        date(2026, 1, 2),
    )
    day_7 = selector.activity_probability(
        user,
        date(2026, 1, 8),
    )

    assert day_1 > day_7


def test_activity_selection_is_reproducible():
    config = load_game_config()["activity"]
    user = make_user()

    selector_1 = UserActivitySelector(
        np.random.default_rng(42),
        config,
    )
    selector_2 = UserActivitySelector(
        np.random.default_rng(42),
        config,
    )

    result_1 = selector_1.is_active(user, date(2026, 1, 2))
    result_2 = selector_2.is_active(user, date(2026, 1, 2))

    assert result_1 == result_2
