from dataclasses import dataclass
from datetime import date
from math import exp, log1p

import numpy as np


@dataclass(frozen=True)
class ReturningUserState:
    user_id: object
    registration_date: date
    last_active_date: date | None
    engagement_propensity: float
    frustration_score: float
    base_churn_propensity: float
    recent_success: float


class UserActivitySelector:
    def __init__(
        self,
        rng: np.random.Generator,
        activity_config: dict,
    ):
        self.rng = rng
        self.config = activity_config

    @staticmethod
    def _sigmoid(value: float) -> float:
        return 1.0 / (1.0 + exp(-value))

    def activity_probability(
        self,
        state: ReturningUserState,
        simulation_date: date,
    ) -> float:
        reference_date = (
            state.last_active_date
            or state.registration_date
        )

        days_since_last_session = max(
            (simulation_date - reference_date).days,
            0,
        )

        user_age_days = max(
            (
                simulation_date
                - state.registration_date
            ).days,
            0,
        )

        logit = (
            self.config["intercept"]
            + self.config["engagement_weight"]
            * state.engagement_propensity
            + self.config[
                "days_since_last_session_weight"
            ]
            * days_since_last_session
            + self.config["user_age_days_weight"]
            * log1p(user_age_days)
            + self.config["frustration_weight"]
            * state.frustration_score
            + self.config["base_churn_weight"]
            * state.base_churn_propensity
            + self.config["recent_success_weight"]
            * state.recent_success
        )

        probability = self._sigmoid(logit)

        return float(
            np.clip(
                probability,
                self.config["min_probability"],
                self.config["max_probability"],
            )
        )

    def is_active(
        self,
        state: ReturningUserState,
        simulation_date: date,
    ) -> bool:
        probability = self.activity_probability(
            state,
            simulation_date,
        )

        return bool(
            self.rng.random() < probability
        )
