import argparse
from datetime import date

from src.orchestration.pending import (
    PendingSimulationRunner,
    default_target_date,
)
from src.simulation.daily_simulation import (
    DailySimulation,
)
from src.storage.postgres import get_connection
from src.storage.repositories import (
    EventRepository,
    UserRepository,
)
from src.storage.simulation_runs import (
    SimulationRunRepository,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate every missing simulation day "
            "after the latest successful run."
        )
    )

    parser.add_argument(
        "--target-date",
        type=date.fromisoformat,
        default=None,
        help=(
            "Last virtual date to generate "
            "(YYYY-MM-DD). Default: yesterday."
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    target_date = (
        args.target_date
        if args.target_date is not None
        else default_target_date()
    )

    with get_connection() as connection:
        run_repository = (
            SimulationRunRepository(
                connection
            )
        )

        simulation = DailySimulation(
            run_repository=run_repository,
            user_repository=UserRepository(
                connection
            ),
            event_repository=EventRepository(
                connection
            ),
        )

        runner = PendingSimulationRunner(
            connection=connection,
            simulation=simulation,
            run_repository=run_repository,
        )

        summary = runner.run(
            target_date=target_date
        )

    print(
        f"target={summary.target_date} "
        f"pending={len(summary.pending_dates)} "
        f"completed={len(summary.results)}"
    )

    for result in summary.results:
        print(
            f"date={result.simulation_date} "
            f"seed={result.seed} "
            f"users={result.users_created} "
            f"returning={result.returning_active_users} "
            f"sessions={result.sessions_created} "
            f"events={result.events_created}"
        )


if __name__ == "__main__":
    main()
