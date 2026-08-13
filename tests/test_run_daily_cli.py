from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import src.cli.run_daily as run_daily


class FakeConnectionContext:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def test_main_runs_requested_simulation_date(
    monkeypatch,
    capsys,
):
    simulation_date = date(2026, 1, 5)

    monkeypatch.setattr(
        run_daily,
        "parse_args",
        lambda: SimpleNamespace(
            simulation_date=simulation_date
        ),
    )

    connection = MagicMock()

    monkeypatch.setattr(
        run_daily,
        "get_connection",
        lambda: FakeConnectionContext(connection),
    )

    simulation = MagicMock()

    simulation.run.return_value = SimpleNamespace(
        simulation_date=simulation_date,
        seed=123456,
        users_created=450,
        returning_active_users=120,
        sessions_created=900,
        events_created=10000,
    )

    monkeypatch.setattr(
        run_daily,
        "DailySimulation",
        MagicMock(return_value=simulation),
    )

    run_daily.main()

    simulation.run.assert_called_once_with(
        simulation_date
    )

    output = capsys.readouterr().out.strip()

    assert output == (
        "date=2026-01-05 "
        "seed=123456 "
        "users=450 "
        "returning=120 "
        "sessions=900 "
        "events=10000"
    )
