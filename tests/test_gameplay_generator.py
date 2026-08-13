from datetime import datetime
from uuid import UUID

import numpy as np

from src.config.loader import (
    load_game_config,
    load_levels_config,
)
from src.generators.gameplay import (
    GameplayGenerator,
    GameplayUserState,
)
from src.generators.sessions import SessionRecord


USER_ID = UUID(
    "00000000-0000-4000-8000-000000000001"
)

SESSION_ID = UUID(
    "00000000-0000-4000-8000-000000000002"
)


def make_generator(seed=42):
    game_config = load_game_config()

    return GameplayGenerator(
        rng=np.random.default_rng(seed),
        gameplay_config=game_config["gameplay"],
        levels_config=load_levels_config()["levels"],
        app_version="1.0",
    )


def make_state(**overrides):
    values = {
        "user_id": USER_ID,
        "skill": 0.5,
        "current_level": 1,
        "frustration_score": 0.0,
        "total_levels_completed": 0,
        "total_levels_failed": 0,
        "next_attempt_number": 1,
    }
    values.update(overrides)

    return GameplayUserState(**values)


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


def test_higher_skill_increases_success_probability():
    generator = make_generator()

    low = generator.success_probability(
        skill=0.2,
        difficulty=0.4,
        attempt_number=1,
    )

    high = generator.success_probability(
        skill=0.8,
        difficulty=0.4,
        attempt_number=1,
    )

    assert high > low


def test_higher_difficulty_reduces_success_probability():
    generator = make_generator()

    easy = generator.success_probability(
        skill=0.5,
        difficulty=0.3,
        attempt_number=1,
    )

    hard = generator.success_probability(
        skill=0.5,
        difficulty=0.7,
        attempt_number=1,
    )

    assert easy > hard


def test_repeated_attempts_increase_success_probability():
    generator = make_generator()

    first = generator.success_probability(
        skill=0.5,
        difficulty=0.5,
        attempt_number=1,
    )

    fifth = generator.success_probability(
        skill=0.5,
        difficulty=0.5,
        attempt_number=5,
    )

    assert fifth > first


def test_gameplay_events_are_start_result_pairs():
    result = make_generator().generate(
        make_state(),
        [make_session()],
    )

    assert len(result.events) > 0
    assert len(result.events) % 2 == 0

    for index in range(0, len(result.events), 2):
        start = result.events[index]
        outcome = result.events[index + 1]

        assert start.event_name == "level_start"
        assert outcome.event_name in {
            "level_fail",
            "level_complete",
        }

        assert start.session_id == outcome.session_id
        assert start.level_id == outcome.level_id
        assert (
            start.attempt_number
            == outcome.attempt_number
        )

        assert start.event_ts < outcome.event_ts


def test_gameplay_stays_inside_session():
    session = make_session()

    result = make_generator().generate(
        make_state(),
        [session],
    )

    for event in result.events:
        assert (
            session.session_start_ts
            <= event.event_ts
            <= session.session_end_ts
        )


def test_level_17_failure_has_extra_frustration():
    generator = make_generator()

    normal = generator._frustration_after_fail(
        frustration=0.0,
        level_id=16,
        attempt_number=1,
    )

    level_17 = generator._frustration_after_fail(
        frustration=0.0,
        level_id=17,
        attempt_number=1,
    )

    assert level_17 > normal


def test_third_and_fifth_fail_have_extra_penalty():
    generator = make_generator()

    first = generator._frustration_after_fail(
        frustration=0.0,
        level_id=10,
        attempt_number=1,
    )

    third = generator._frustration_after_fail(
        frustration=0.0,
        level_id=10,
        attempt_number=3,
    )

    fifth = generator._frustration_after_fail(
        frustration=0.0,
        level_id=10,
        attempt_number=5,
    )

    assert third > first
    assert fifth > third


def test_generation_is_reproducible():
    state = make_state()
    sessions = [make_session()]

    result_1 = make_generator(42).generate(
        state,
        sessions,
    )

    result_2 = make_generator(42).generate(
        state,
        sessions,
    )

    assert result_1 == result_2
