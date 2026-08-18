from datetime import date
from unittest.mock import MagicMock

import pytest

from src.storage.simulation_runs import (
    SimulationAlreadyCompletedError,
    SimulationRunRepository,
)


def make_repository(fetchone_result):
    connection = MagicMock()
    cursor = (
        connection
        .cursor
        .return_value
        .__enter__
        .return_value
    )
    cursor.fetchone.return_value = fetchone_result

    return SimulationRunRepository(connection)


def test_date_without_existing_run_can_start():
    repository = make_repository(None)

    repository.ensure_date_can_run(
        date(2026, 1, 1)
    )


def test_successful_date_cannot_run_again():
    repository = make_repository(
        ("success",)
    )

    with pytest.raises(
        SimulationAlreadyCompletedError,
        match="2026-01-01",
    ):
        repository.ensure_date_can_run(
            date(2026, 1, 1)
        )


def test_failed_date_can_be_retried():
    repository = make_repository(
        ("failed",)
    )

    repository.ensure_date_can_run(
        date(2026, 1, 1)
    )


def test_fetch_success_dates():
    connection = MagicMock()
    cursor = (
        connection
        .cursor
        .return_value
        .__enter__
        .return_value
    )

    cursor.fetchall.return_value = [
        (date(2026, 1, 1),),
        (date(2026, 1, 2),),
        (date(2026, 1, 3),),
    ]

    repository = SimulationRunRepository(
        connection
    )

    assert repository.fetch_success_dates() == [
        date(2026, 1, 1),
        date(2026, 1, 2),
        date(2026, 1, 3),
    ]

    cursor.execute.assert_called_once()
