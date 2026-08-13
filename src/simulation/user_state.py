from dataclasses import dataclass
from datetime import date
from math import exp

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


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + exp(-value))


class UserActivitySelector:
    def __init__(
        self,
        rng: np.random.Generator,
        activity_config: dict,
    ):
        self.rng = rng
        self.config = activity_config

    def activity_probability(
        self,
        user: ReturningUserState,
        simulation_date: date,
    ) -> float:
        reference_date = (
            user.last_active_date
            if user.last_active_date is not None
            else user.registration_date
        )

        days_since_last_session = max(
            (simulation_date - reference_date).days,
            0,
        )

        logit_p = (
            self.config["intercept"]
            + self.config["engagement_weight"]
            * user.engagement_propensity
            + self.config["days_since_last_session_weight"]
            * days_since_last_session
            + self.config["frustration_weight"]
            * user.frustration_score
            + self.config["base_churn_weight"]
            * user.base_churn_propensity
            + self.config["recent_success_weight"]
            * user.recent_success
        )

        probability = sigmoid(logit_p)

        return float(
            np.clip(
                probability,
                self.config["min_probability"],
                self.config["max_probability"],
            )
        )

    def is_active(
        self,
        user: ReturningUserState,
        simulation_date: date,
    ) -> bool:
        probability = self.activity_probability(
            user,
            simulation_date,
        )

        return bool(self.rng.random() < probability)
