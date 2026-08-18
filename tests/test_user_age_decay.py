from datetime import date
from uuid import UUID

import numpy as np

from src.config.loader import load_game_config
from src.simulation.user_state import (
    ReturningUserState,
    UserActivitySelector,
)


USER_ID = UUID(
    "00000000-0000-4000-8000-000000000001"
)


def make_state(registration_date):
    return ReturningUserState(
        user_id=USER_ID,
        registration_date=registration_date,
        last_active_date=date(2026, 1, 9),
        engagement_propensity=0.5,
        frustration_score=0.1,
        base_churn_propensity=0.2,
        recent_success=0.6,
    )


def test_older_user_has_lower_activity_probability():
    selector = UserActivitySelector(
        rng=np.random.default_rng(42),
        activity_config=load_game_config()["activity"],
    )

    simulation_date = date(2026, 1, 10)

    young_user = make_state(
        registration_date=date(2026, 1, 9)
    )

    older_user = make_state(
        registration_date=date(2026, 1, 2)
    )

    young_probability = selector.activity_probability(
        young_user,
        simulation_date,
    )

    older_probability = selector.activity_probability(
        older_user,
        simulation_date,
    )

    assert older_probability < young_probability
