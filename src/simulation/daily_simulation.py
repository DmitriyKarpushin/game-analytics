from dataclasses import dataclass
from datetime import date

import numpy as np

from src.storage.simulation_runs import SimulationRunRepository


@dataclass(frozen=True)
class SimulationResult:
    simulation_date: date
    seed: int
    users_created: int
    events_created: int


class DailySimulation:
    def __init__(
        self,
        run_repository: SimulationRunRepository,
        base_seed: int = 42,
    ):
        self.run_repository = run_repository
        self.base_seed = base_seed

    def run(self, simulation_date: date) -> SimulationResult:
        self.run_repository.ensure_date_can_run(simulation_date)

        seed = self._seed_for_date(simulation_date)

        self.run_repository.start(
            simulation_date=simulation_date,
            seed=seed,
        )

        # User/session/gameplay generation will be added next.
        users_created = 0
        events_created = 0

        self.run_repository.mark_success(
            simulation_date=simulation_date,
            users_created=users_created,
            events_created=events_created,
        )

        return SimulationResult(
            simulation_date=simulation_date,
            seed=seed,
            users_created=users_created,
            events_created=events_created,
        )

    def _seed_for_date(self, simulation_date: date) -> int:
        seed_sequence = np.random.SeedSequence(
            [self.base_seed, simulation_date.toordinal()]
        )

        # PostgreSQL BIGINT is signed, so keep the value within 63 bits.
        return int(seed_sequence.generate_state(1, dtype=np.uint64)[0] & ((1 << 63) - 1))
