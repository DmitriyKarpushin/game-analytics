from dataclasses import dataclass
from datetime import date

import numpy as np

from src.config.loader import (
    load_acquisition_config,
    load_game_config,
)
from src.generators.users import UserGenerator
from src.simulation.user_state import (
    ReturningUserState,
    UserActivitySelector,
)
from src.storage.repositories import (
    ReturningUserCandidate,
    UserRepository,
)
from src.storage.simulation_runs import SimulationRunRepository


@dataclass(frozen=True)
class SimulationResult:
    simulation_date: date
    seed: int
    users_created: int
    returning_active_users: int
    events_created: int


class DailySimulation:
    def __init__(
        self,
        run_repository: SimulationRunRepository,
        user_repository: UserRepository,
        base_seed: int | None = None,
    ):
        self.run_repository = run_repository
        self.user_repository = user_repository

        self.game_config = load_game_config()
        self.acquisition_config = load_acquisition_config()

        simulation_config = self.game_config["simulation"]

        self.start_date = date.fromisoformat(
            simulation_config["start_date"]
        )

        self.base_seed = (
            simulation_config["base_seed"]
            if base_seed is None
            else base_seed
        )

    def run(self, simulation_date: date) -> SimulationResult:
        self.run_repository.ensure_date_can_run(simulation_date)

        seed = self._seed_for_date(simulation_date)
        rng = np.random.default_rng(seed)

        self.run_repository.start(
            simulation_date=simulation_date,
            seed=seed,
        )

        users_count = self._generate_new_users_count(
            simulation_date,
            rng,
        )

        user_generator = UserGenerator(rng)

        users, states = user_generator.generate(
            count=users_count,
            registration_date=simulation_date,
        )

        self.user_repository.insert_users(users)
        self.user_repository.insert_states(states)

        returning_candidates = (
            self.user_repository.fetch_returning_candidates(
                simulation_date
            )
        )

        active_returning_users = (
            self._select_returning_active_users(
                candidates=returning_candidates,
                simulation_date=simulation_date,
                rng=rng,
            )
        )

        events_created = 0

        self.run_repository.mark_success(
            simulation_date=simulation_date,
            users_created=len(users),
            events_created=events_created,
        )

        return SimulationResult(
            simulation_date=simulation_date,
            seed=seed,
            users_created=len(users),
            returning_active_users=len(active_returning_users),
            events_created=events_created,
        )

    def _select_returning_active_users(
        self,
        candidates: list[ReturningUserCandidate],
        simulation_date: date,
        rng: np.random.Generator,
    ) -> list[ReturningUserCandidate]:
        selector = UserActivitySelector(
            rng=rng,
            activity_config=self.game_config["activity"],
        )

        default_recent_success = self.game_config[
            "activity"
        ]["default_recent_success"]

        active_users: list[ReturningUserCandidate] = []

        for candidate in candidates:
            state = ReturningUserState(
                user_id=candidate.user_id,
                registration_date=candidate.registration_date,
                last_active_date=candidate.last_active_date,
                engagement_propensity=(
                    candidate.engagement_propensity
                ),
                frustration_score=candidate.frustration_score,
                base_churn_propensity=(
                    candidate.base_churn_propensity
                ),
                recent_success=default_recent_success,
            )

            if selector.is_active(state, simulation_date):
                active_users.append(candidate)

        return active_users

    def _lambda_for_date(self, simulation_date: date) -> float:
        day_number = (simulation_date - self.start_date).days

        if day_number < 0:
            raise ValueError(
                "Simulation date cannot be earlier than start date"
            )

        config = self.acquisition_config["new_users"]

        trend = 1.0 + day_number * config["daily_trend"]

        weekday_name = simulation_date.strftime("%A").lower()
        weekday_factor = config["weekday_factors"][weekday_name]

        return config["base_lambda"] * trend * weekday_factor

    def _generate_new_users_count(
        self,
        simulation_date: date,
        rng: np.random.Generator,
    ) -> int:
        lambda_day = self._lambda_for_date(simulation_date)

        return int(rng.poisson(lambda_day))

    def _seed_for_date(self, simulation_date: date) -> int:
        seed_sequence = np.random.SeedSequence(
            [self.base_seed, simulation_date.toordinal()]
        )

        return int(
            seed_sequence.generate_state(
                1,
                dtype=np.uint64,
            )[0]
            & ((1 << 63) - 1)
        )
