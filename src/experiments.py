from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from uuid import UUID


@dataclass(frozen=True)
class ExperimentAssignment:
    experiment_id: str
    variant: str
    eligible_level: int
    difficulty_multiplier: float


class ExperimentResolver:
    def __init__(
        self,
        start_date: date,
        config: dict,
    ):
        self.start_date = start_date
        self.experiments = config["experiments"]

    def active_experiments(
        self,
        simulation_date: date,
    ) -> list[dict]:
        day_number = (
            simulation_date - self.start_date
        ).days + 1

        if day_number < 1:
            raise ValueError(
                "simulation_date cannot be before start_date"
            )

        return [
            experiment
            for experiment in self.experiments
            if (
                experiment["start_day"]
                <= day_number
                <= experiment["end_day"]
            )
        ]

    def assignment_for_user(
        self,
        user_id: UUID,
        simulation_date: date,
    ) -> ExperimentAssignment | None:
        active = self.active_experiments(
            simulation_date
        )

        if not active:
            return None

        if len(active) > 1:
            raise ValueError(
                "Multiple simultaneous gameplay experiments "
                "are not supported"
            )

        experiment = active[0]

        variant = self._variant_for_user(
            user_id=user_id,
            experiment=experiment,
        )

        variant_config = experiment[
            "variants"
        ][variant]

        return ExperimentAssignment(
            experiment_id=str(
                experiment["experiment_id"]
            ),
            variant=variant,
            eligible_level=int(
                experiment["eligible_level"]
            ),
            difficulty_multiplier=float(
                variant_config[
                    "difficulty_multiplier"
                ]
            ),
        )

    def _variant_for_user(
        self,
        user_id: UUID,
        experiment: dict,
    ) -> str:
        variants = experiment["variants"]

        weights = {
            name: float(config["weight"])
            for name, config in variants.items()
        }

        total_weight = sum(weights.values())

        if total_weight <= 0:
            raise ValueError(
                "Experiment variant weights must be positive"
            )

        key = (
            f"{experiment['experiment_id']}:{user_id}"
        )

        digest = sha256(
            key.encode("utf-8")
        ).digest()

        bucket = (
            int.from_bytes(
                digest[:8],
                byteorder="big",
            )
            / 2**64
        )

        cumulative = 0.0
        names = list(weights)

        for name in names:
            cumulative += (
                weights[name]
                / total_weight
            )

            if bucket < cumulative:
                return name

        return names[-1]
