from datetime import date, datetime
from uuid import UUID

import numpy as np

from src.config.loader import load_game_config
from src.generators.sessions import (
    SessionGenerator,
    SessionUser,
)


USER_ID = UUID(
    "00000000-0000-4000-8000-000000000001"
)


def make_generator(seed=42):
    config = load_game_config()["sessions"]

    return SessionGenerator(
        rng=np.random.default_rng(seed),
        session_config=config,
    )


def make_user(**overrides):
    values = {
        "user_id": USER_ID,
        "engagement_propensity": 0.5,
        "earliest_start_ts": None,
    }
    values.update(overrides)

    return SessionUser(**values)


def test_active_user_gets_between_one_and_five_sessions():
    generator = make_generator()

    sessions = generator.generate_for_user(
        make_user(),
        date(2026, 1, 1),
    )

    assert 1 <= len(sessions) <= 5


def test_session_ids_are_unique():
    generator = make_generator()

    sessions = generator.generate_for_user(
        make_user(engagement_propensity=0.99),
        date(2026, 1, 1),
    )

    ids = [session.session_id for session in sessions]

    assert len(ids) == len(set(ids))


def test_sessions_have_valid_timestamps():
    generator = make_generator()

    sessions = generator.generate_for_user(
        make_user(),
        date(2026, 1, 1),
    )

    for session in sessions:
        assert session.session_start_ts < session.session_end_ts
        assert session.session_start_ts.date() == date(2026, 1, 1)
        assert session.session_end_ts.date() == date(2026, 1, 1)


def test_new_user_session_starts_after_registration():
    generator = make_generator()

    registration_ts = datetime(
        2026,
        1,
        1,
        18,
        30,
    )

    sessions = generator.generate_for_user(
        make_user(
            earliest_start_ts=registration_ts,
        ),
        date(2026, 1, 1),
    )

    assert all(
        session.session_start_ts >= registration_ts
        for session in sessions
    )


def test_sessions_are_sorted_by_start_time():
    generator = make_generator()

    sessions = generator.generate_for_user(
        make_user(engagement_propensity=0.99),
        date(2026, 1, 1),
    )

    starts = [
        session.session_start_ts
        for session in sessions
    ]

    assert starts == sorted(starts)


def test_generation_is_reproducible():
    date_ = date(2026, 1, 1)
    user = make_user()

    sessions_1 = make_generator(42).generate_for_user(
        user,
        date_,
    )
    sessions_2 = make_generator(42).generate_for_user(
        user,
        date_,
    )

    assert sessions_1 == sessions_2


def test_sessions_do_not_overlap():
    generator = make_generator()

    sessions = generator.generate_for_user(
        make_user(engagement_propensity=0.99),
        date(2026, 1, 1),
    )

    for previous, current in zip(
        sessions,
        sessions[1:],
    ):
        assert (
            previous.session_end_ts
            <= current.session_start_ts
        )