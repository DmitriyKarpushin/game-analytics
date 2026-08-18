from dataclasses import dataclass
from datetime import date, timedelta

from psycopg import Connection

from src.simulation.daily_simulation import (
    DailySimulation,
    SimulationResult,
)
from src.storage.simulation_runs import (
    SimulationRunRepository,
)


LOCK_NAME = "game_analytics_run_pending"


class SimulationHistoryGapError(RuntimeError):
    pass


class PendingRunLockedError(RuntimeError):
    pass


@dataclass(frozen=True)
class PendingRunSummary:
    target_date: date
    pending_dates: tuple[date, ...]
    results: tuple[SimulationResult, ...]


def default_target_date(
    today: date | None = None,
) -> date:
    resolved_today = (
        date.today()
        if today is None
        else today
    )

    return resolved_today - timedelta(days=1)


def build_pending_dates(
    start_date: date,
    target_date: date,
    successful_dates: list[date],
) -> list[date]:
    successful = sorted(
        set(successful_dates)
    )

    relevant = [
        simulation_date
        for simulation_date in successful
        if simulation_date >= start_date
    ]

    if relevant:
        latest_success = relevant[-1]

        expected_history = set(
            _date_range(
                start_date,
                latest_success,
            )
        )

        actual_history = set(relevant)

        missing_history = sorted(
            expected_history - actual_history
        )

        if missing_history:
            preview = ", ".join(
                value.isoformat()
                for value in missing_history[:5]
            )

            raise SimulationHistoryGapError(
                "Successful simulation history contains "
                "a gap before the latest completed day. "
                f"First missing dates: {preview}"
            )

        next_date = (
            latest_success
            + timedelta(days=1)
        )

    else:
        next_date = start_date

    if target_date < next_date:
        return []

    return _date_range(
        next_date,
        target_date,
    )


class PendingSimulationRunner:
    def __init__(
        self,
        connection: Connection,
        simulation: DailySimulation,
        run_repository: SimulationRunRepository,
    ):
        self.connection = connection
        self.simulation = simulation
        self.run_repository = run_repository

    def run(
        self,
        target_date: date,
    ) -> PendingRunSummary:
        if not try_advisory_lock(
            self.connection
        ):
            raise PendingRunLockedError(
                "Another run_pending process "
                "already holds the orchestration lock"
            )

        try:
            successful_dates = (
                self.run_repository
                .fetch_success_dates()
            )

            pending_dates = (
                build_pending_dates(
                    start_date=(
                        self.simulation.start_date
                    ),
                    target_date=target_date,
                    successful_dates=successful_dates,
                )
            )

            results: list[SimulationResult] = []

            for simulation_date in pending_dates:
                try:
                    result = self.simulation.run(
                        simulation_date
                    )

                    self.connection.commit()

                except Exception:
                    self.connection.rollback()
                    raise

                results.append(result)

            return PendingRunSummary(
                target_date=target_date,
                pending_dates=tuple(
                    pending_dates
                ),
                results=tuple(results),
            )

        finally:
            release_advisory_lock(
                self.connection
            )


def try_advisory_lock(
    connection: Connection,
) -> bool:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT pg_try_advisory_lock(
                hashtext(%s)
            )
            """,
            (LOCK_NAME,),
        )

        row = cursor.fetchone()

    return bool(
        row is not None
        and row[0]
    )


def release_advisory_lock(
    connection: Connection,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT pg_advisory_unlock(
                hashtext(%s)
            )
            """,
            (LOCK_NAME,),
        )


def _date_range(
    start_date: date,
    end_date: date,
) -> list[date]:
    result: list[date] = []

    current = start_date

    while current <= end_date:
        result.append(current)
        current += timedelta(days=1)

    return result
