from datetime import datetime
from uuid import UUID

import numpy as np
import pytest

from src.config.loader import (
    load_game_config,
    load_levels_config,
)
from src.experiments import ExperimentAssignment
from src.generators.gameplay import (
    GameplayGenerator,
    GameplayUserState,
)
from src.generators.sessions import SessionRecord


USER_ID = UUID(
    "00000000-0000-4000-8000-000000000101"
)

SESSION_ID = UUID(
    "00000000-0000-4000-8000-000000000102"
)


def make_generator():
    return GameplayGenerator(
        rng=np.random.default_rng(42),
        gameplay_config=(
            load_game_config()["gameplay"]
        ),
        levels_config=(
            load_levels_config()["levels"]
        ),
        app_version="1.3",
    )


def make_state(level=17):
    return GameplayUserState(
        user_id=USER_ID,
        skill=0.5,
        current_level=level,
        frustration_score=0.0,
        total_levels_completed=level - 1,
        total_levels_failed=0,
        next_attempt_number=1,
    )


def make_session(
    session_id=SESSION_ID,
    start_hour=10,
    duration_minutes=30,
):
    start = datetime(
        2026, 7, 15, start_hour, 0
    )

    from datetime import timedelta

    return SessionRecord(
        session_id=session_id,
        user_id=USER_ID,
        session_start_ts=start,
        session_end_ts=(
            start
            + timedelta(
                minutes=duration_minutes
            )
        ),
    )


def treatment():
    return ExperimentAssignment(
        experiment_id="level17_balance_v1",
        variant="treatment",
        eligible_level=17,
        difficulty_multiplier=0.82,
    )


def control():
    return ExperimentAssignment(
        experiment_id="level17_balance_v1",
        variant="control",
        eligible_level=17,
        difficulty_multiplier=1.0,
    )


def test_level17_emits_experiment_exposure():
    result = make_generator().generate(
        make_state(),
        [make_session()],
        experiment=treatment(),
    )

    exposures = [
        event
        for event in result.events
        if event.event_name
        == "experiment_exposure"
    ]

    assert len(exposures) == 1

    exposure = exposures[0]

    assert exposure.level_id == 17
    assert exposure.attempt_number is None
    assert exposure.app_version == "1.3"

    assert exposure.event_properties == {
        "experiment_id": "level17_balance_v1",
        "variant": "treatment",
    }


def test_exposure_is_emitted_at_most_once_per_user_day():
    second_session_id = UUID(
        "00000000-0000-4000-8000-000000000103"
    )

    result = make_generator().generate(
        make_state(),
        [
            make_session(),
            make_session(
                session_id=second_session_id,
                start_hour=15,
            ),
        ],
        experiment=treatment(),
    )

    assert sum(
        event.event_name
        == "experiment_exposure"
        for event in result.events
    ) == 1


def test_treatment_reduces_only_eligible_level_difficulty():
    generator = make_generator()

    base = 0.6755

    assert generator.difficulty_for_level(
        level_id=17,
        base_difficulty=base,
        experiment=treatment(),
    ) == pytest.approx(base * 0.82)

    assert generator.difficulty_for_level(
        level_id=17,
        base_difficulty=base,
        experiment=control(),
    ) == pytest.approx(base)

    assert generator.difficulty_for_level(
        level_id=18,
        base_difficulty=base,
        experiment=treatment(),
    ) == pytest.approx(base)


def test_no_experiment_preserves_existing_instrumentation():
    result = make_generator().generate(
        make_state(),
        [make_session()],
    )

    assert all(
        event.event_name
        != "experiment_exposure"
        for event in result.events
    )


def test_no_exposure_when_level_cannot_start():
    result = make_generator().generate(
        make_state(),
        [
            make_session(
                duration_minutes=1
            )
        ],
        experiment=treatment(),
    )

    assert result.events == []
