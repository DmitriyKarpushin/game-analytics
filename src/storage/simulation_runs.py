from datetime import date, datetime

from psycopg import Connection


class SimulationAlreadyCompletedError(RuntimeError):
    pass


class SimulationRunRepository:
    def __init__(self, connection: Connection):
        self.connection = connection

    def ensure_date_can_run(self, simulation_date: date) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT status
                FROM simulation_runs
                WHERE simulation_date = %s
                """,
                (simulation_date,),
            )
            row = cursor.fetchone()

        if row is not None and row[0] == "success":
            raise SimulationAlreadyCompletedError(
                f"Simulation already completed for {simulation_date}"
            )

    def fetch_success_dates(self) -> list[date]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT simulation_date
                FROM simulation_runs
                WHERE status = 'success'
                ORDER BY simulation_date
                """
            )

            rows = cursor.fetchall()

        return [
            row[0]
            for row in rows
        ]

    def start(self, simulation_date: date, seed: int) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO simulation_runs (
                    simulation_date,
                    started_at,
                    status,
                    seed,
                    users_created,
                    events_created
                )
                VALUES (%s, %s, 'running', %s, 0, 0)
                ON CONFLICT (simulation_date)
                DO UPDATE SET
                    started_at = EXCLUDED.started_at,
                    finished_at = NULL,
                    status = 'running',
                    seed = EXCLUDED.seed,
                    users_created = 0,
                    events_created = 0
                """,
                (
                    simulation_date,
                    datetime.now(),
                    seed,
                ),
            )

    def mark_success(
        self,
        simulation_date: date,
        users_created: int,
        events_created: int,
    ) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE simulation_runs
                SET
                    finished_at = %s,
                    status = 'success',
                    users_created = %s,
                    events_created = %s
                WHERE simulation_date = %s
                """,
                (
                    datetime.now(),
                    users_created,
                    events_created,
                    simulation_date,
                ),
            )

    def mark_failed(self, simulation_date: date) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE simulation_runs
                SET
                    finished_at = %s,
                    status = 'failed'
                WHERE simulation_date = %s
                """,
                (
                    datetime.now(),
                    simulation_date,
                ),
            )
