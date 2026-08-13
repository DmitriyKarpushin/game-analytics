import argparse
from datetime import date

from src.simulation.daily_simulation import DailySimulation
from src.storage.postgres import get_connection
from src.storage.repositories import EventRepository, UserRepository
from src.storage.simulation_runs import SimulationRunRepository


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one virtual simulation day."
    )

    parser.add_argument(
        "simulation_date",
        type=date.fromisoformat,
        help="Virtual date in YYYY-MM-DD format.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    with get_connection() as connection:
        simulation = DailySimulation(
            run_repository=SimulationRunRepository(connection),
            user_repository=UserRepository(connection),
            event_repository=EventRepository(connection),
        )

        result = simulation.run(args.simulation_date)

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
