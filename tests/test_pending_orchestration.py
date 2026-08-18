from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, call

import pytest

import src.orchestration.pending as pending
from src.orchestration.pending import (
    PendingRunLockedError,
    PendingSimulationRunner,
    SimulationHistoryGapError,
    build_pending_dates,
    default_target_date,
)


START = date(2026, 1, 1)


def make_result(simulation_date):
    return SimpleNamespace(
        simulation_date=simulation_date,
        seed=42,
        users_created=10,
        returning_active_users=5,
        sessions_created=20,
        events_created=100,
    )


def test_default_target_is_yesterday():
    assert default_target_date(
        date(2026, 8, 18)
    ) == date(2026, 8, 17)


def test_no_history_starts_from_simulation_start():
    result = build_pending_dates(
        start_date=START,
        target_date=date(2026, 1, 3),
        successful_dates=[],
    )

    assert result == [
        date(2026, 1, 1),
        date(2026, 1, 2),
        date(2026, 1, 3),
    ]


def test_contiguous_history_builds_only_tail():
    result = build_pending_dates(
        start_date=START,
        target_date=date(2026, 1, 5),
        successful_dates=[
            date(2026, 1, 1),
            date(2026, 1, 2),
            date(2026, 1, 3),
        ],
    )

    assert result == [
        date(2026, 1, 4),
        date(2026, 1, 5),
    ]


def test_up_to_date_history_has_no_pending_days():
    result = build_pending_dates(
        start_date=START,
        target_date=date(2026, 1, 3),
        successful_dates=[
            date(2026, 1, 1),
            date(2026, 1, 2),
            date(2026, 1, 3),
        ],
    )

    assert result == []


def test_historical_gap_is_rejected():
    with pytest.raises(
        SimulationHistoryGapError
    ):
        build_pending_dates(
            start_date=START,
            target_date=date(2026, 1, 5),
            successful_dates=[
                date(2026, 1, 1),
                date(2026, 1, 3),
            ],
        )


def test_runner_persists_running_before_generation(
    monkeypatch,
):
    connection = MagicMock()

    simulation = MagicMock()
    simulation.start_date = START
    simulation.seed_for_date.return_value = 123
    simulation.run.return_value = (
        make_result(
            date(2026, 1, 2)
        )
    )

    repository = MagicMock()
    repository.fetch_success_dates.return_value = [
        date(2026, 1, 1),
    ]

    monkeypatch.setattr(
        pending,
        "try_advisory_lock",
        lambda connection: True,
    )

    monkeypatch.setattr(
        pending,
        "release_advisory_lock",
        MagicMock(),
    )

    runner = PendingSimulationRunner(
        connection=connection,
        simulation=simulation,
        run_repository=repository,
    )

    runner.run(
        date(2026, 1, 2)
    )

    repository.start.assert_called_once_with(
        simulation_date=date(2026, 1, 2),
        seed=123,
    )

    simulation.run.assert_called_once_with(
        date(2026, 1, 2)
    )

    assert connection.commit.call_count == 2


def test_runner_commits_each_successful_day(
    monkeypatch,
):
    connection = MagicMock()

    simulation = MagicMock()
    simulation.start_date = START

    simulation.seed_for_date.side_effect = [
        103,
        104,
    ]

    simulation.run.side_effect = [
        make_result(date(2026, 1, 3)),
        make_result(date(2026, 1, 4)),
    ]

    repository = MagicMock()
    repository.fetch_success_dates.return_value = [
        date(2026, 1, 1),
        date(2026, 1, 2),
    ]

    monkeypatch.setattr(
        pending,
        "try_advisory_lock",
        lambda connection: True,
    )

    monkeypatch.setattr(
        pending,
        "release_advisory_lock",
        MagicMock(),
    )

    runner = PendingSimulationRunner(
        connection=connection,
        simulation=simulation,
        run_repository=repository,
    )

    summary = runner.run(
        date(2026, 1, 4)
    )

    assert summary.pending_dates == (
        date(2026, 1, 3),
        date(2026, 1, 4),
    )

    assert repository.start.call_args_list == [
        call(
            simulation_date=date(
                2026, 1, 3
            ),
            seed=103,
        ),
        call(
            simulation_date=date(
                2026, 1, 4
            ),
            seed=104,
        ),
    ]

    assert connection.commit.call_count == 4

    repository.mark_failed.assert_not_called()


def test_runner_persists_failed_day(
    monkeypatch,
):
    connection = MagicMock()

    simulation = MagicMock()
    simulation.start_date = START
    simulation.seed_for_date.return_value = 102
    simulation.run.side_effect = RuntimeError(
        "boom"
    )

    repository = MagicMock()
    repository.fetch_success_dates.return_value = [
        date(2026, 1, 1),
    ]

    monkeypatch.setattr(
        pending,
        "try_advisory_lock",
        lambda connection: True,
    )

    monkeypatch.setattr(
        pending,
        "release_advisory_lock",
        MagicMock(),
    )

    runner = PendingSimulationRunner(
        connection=connection,
        simulation=simulation,
        run_repository=repository,
    )

    with pytest.raises(
        RuntimeError,
        match="boom",
    ):
        runner.run(
            date(2026, 1, 2)
        )

    repository.start.assert_called_once_with(
        simulation_date=date(2026, 1, 2),
        seed=102,
    )

    repository.mark_failed.assert_called_once_with(
        date(2026, 1, 2)
    )

    assert connection.commit.call_count == 2
    assert connection.rollback.call_count >= 2


def test_keyboard_interrupt_records_failure_before_unlock(
    monkeypatch,
):
    connection = MagicMock()
    order = []

    connection.rollback.side_effect = (
        lambda: order.append("rollback")
    )

    connection.commit.side_effect = (
        lambda: order.append("commit")
    )

    simulation = MagicMock()
    simulation.start_date = START
    simulation.seed_for_date.return_value = 102
    simulation.run.side_effect = KeyboardInterrupt()

    repository = MagicMock()
    repository.fetch_success_dates.return_value = [
        date(2026, 1, 1),
    ]

    repository.mark_failed.side_effect = (
        lambda simulation_date:
        order.append("failed")
    )

    monkeypatch.setattr(
        pending,
        "try_advisory_lock",
        lambda connection: True,
    )

    def unlock(connection):
        order.append("unlock")

    monkeypatch.setattr(
        pending,
        "release_advisory_lock",
        unlock,
    )

    runner = PendingSimulationRunner(
        connection=connection,
        simulation=simulation,
        run_repository=repository,
    )

    with pytest.raises(
        KeyboardInterrupt
    ):
        runner.run(
            date(2026, 1, 2)
        )

    assert "failed" in order
    assert order[-1] == "unlock"

    assert (
        order.index("rollback")
        < order.index("failed")
        < order.index(
            "unlock"
        )
    )


def test_runner_rejects_parallel_execution(
    monkeypatch,
):
    connection = MagicMock()
    simulation = MagicMock()
    simulation.start_date = START
    repository = MagicMock()

    monkeypatch.setattr(
        pending,
        "try_advisory_lock",
        lambda connection: False,
    )

    runner = PendingSimulationRunner(
        connection=connection,
        simulation=simulation,
        run_repository=repository,
    )

    with pytest.raises(
        PendingRunLockedError
    ):
        runner.run(
            date(2026, 1, 5)
        )

    repository.fetch_success_dates.assert_not_called()
    simulation.run.assert_not_called()
