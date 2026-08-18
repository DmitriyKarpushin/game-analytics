from datetime import date, timedelta
from uuid import UUID

import pytest

from src.config.loader import load_experiments_config
from src.experiments import ExperimentResolver


START_DATE = date(2026, 1, 1)


def day(number: int) -> date:
    return START_DATE + timedelta(
        days=number - 1
    )


def make_resolver():
    return ExperimentResolver(
        start_date=START_DATE,
        config=load_experiments_config(),
    )


def test_experiment_window_boundaries():
    resolver = make_resolver()

    assert resolver.active_experiments(day(189)) == []
    assert len(resolver.active_experiments(day(190))) == 1
    assert len(resolver.active_experiments(day(219))) == 1
    assert resolver.active_experiments(day(220)) == []


def test_assignment_is_stable_inside_window():
    resolver = make_resolver()

    user_id = UUID(
        "00000000-0000-4000-8000-000000000001"
    )

    first = resolver.assignment_for_user(
        user_id,
        day(190),
    )

    later = resolver.assignment_for_user(
        user_id,
        day(219),
    )

    assert first == later


def test_no_assignment_outside_window():
    resolver = make_resolver()

    user_id = UUID(
        "00000000-0000-4000-8000-000000000001"
    )

    assert resolver.assignment_for_user(
        user_id,
        day(189),
    ) is None

    assert resolver.assignment_for_user(
        user_id,
        day(220),
    ) is None


def test_assignment_is_approximately_balanced():
    resolver = make_resolver()

    counts = {
        "control": 0,
        "treatment": 0,
    }

    for value in range(1, 5001):
        assignment = resolver.assignment_for_user(
            UUID(int=value),
            day(200),
        )

        counts[assignment.variant] += 1

    control_share = (
        counts["control"]
        / sum(counts.values())
    )

    assert 0.47 <= control_share <= 0.53


def test_treatment_has_lower_difficulty_multiplier():
    resolver = make_resolver()

    assignments = [
        resolver.assignment_for_user(
            UUID(int=value),
            day(200),
        )
        for value in range(1, 100)
    ]

    control = next(
        item
        for item in assignments
        if item.variant == "control"
    )

    treatment = next(
        item
        for item in assignments
        if item.variant == "treatment"
    )

    assert control.difficulty_multiplier == 1.0
    assert treatment.difficulty_multiplier == 0.82


def test_date_before_simulation_start_is_rejected():
    resolver = make_resolver()

    with pytest.raises(ValueError):
        resolver.active_experiments(
            date(2025, 12, 31)
        )
