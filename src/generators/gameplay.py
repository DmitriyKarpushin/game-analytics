from dataclasses import dataclass
from math import exp, log1p
from uuid import UUID

import numpy as np

from src.experiments import ExperimentAssignment
from src.generators.events import EventRecord
from src.generators.sessions import SessionRecord


@dataclass
class GameplayUserState:
    user_id: UUID
    skill: float
    current_level: int
    frustration_score: float
    total_levels_completed: int
    total_levels_failed: int
    next_attempt_number: int = 1


@dataclass(frozen=True)
class GameplayResult:
    events: list[EventRecord]
    current_level: int
    frustration_score: float
    total_levels_completed: int
    total_levels_failed: int
    next_attempt_number: int


class GameplayGenerator:
    def __init__(
        self,
        rng: np.random.Generator,
        gameplay_config: dict,
        levels_config: dict,
        app_version: str,
    ):
        self.rng = rng
        self.config = gameplay_config
        self.levels = levels_config
        self.max_level = max(
            int(level_id)
            for level_id in self.levels
        )
        self.app_version = app_version

    def generate(
        self,
        state: GameplayUserState,
        sessions: list[SessionRecord],
        experiment: ExperimentAssignment | None = None,
    ) -> GameplayResult:
        events: list[EventRecord] = []
        experiment_exposure_emitted = False

        frustration = float(
            np.clip(
                state.frustration_score
                * self.config["frustration"]["daily_decay"],
                0.0,
                1.0,
            )
        )

        current_level = state.current_level
        total_completed = state.total_levels_completed
        total_failed = state.total_levels_failed
        attempt_number = state.next_attempt_number

        for session in sorted(
            sessions,
            key=lambda item: item.session_start_ts,
        ):
            cursor = session.session_start_ts

            while current_level <= self.max_level:
                level_config = self.levels[current_level]

                duration = int(
                    level_config["base_duration_sec"]
                )

                result_ts = cursor + self._seconds(duration)

                if result_ts >= session.session_end_ts:
                    break

                if (
                    experiment is not None
                    and current_level
                    == experiment.eligible_level
                    and not experiment_exposure_emitted
                ):
                    events.append(
                        self._make_event(
                            event_ts=cursor,
                            user_id=state.user_id,
                            session_id=session.session_id,
                            event_name="experiment_exposure",
                            level_id=current_level,
                            attempt_number=None,
                            event_properties={
                                "experiment_id": (
                                    experiment.experiment_id
                                ),
                                "variant": experiment.variant,
                            },
                        )
                    )

                    experiment_exposure_emitted = True

                level_start = self._make_event(
                    event_ts=cursor,
                    user_id=state.user_id,
                    session_id=session.session_id,
                    event_name="level_start",
                    level_id=current_level,
                    attempt_number=attempt_number,
                )
                events.append(level_start)

                success_probability = (
                    self.success_probability(
                        skill=state.skill,
                        difficulty=(
                            self.difficulty_for_level(
                                level_id=current_level,
                                base_difficulty=float(
                                    level_config[
                                        "base_difficulty"
                                    ]
                                ),
                                experiment=experiment,
                            )
                        ),
                        attempt_number=attempt_number,
                    )
                )

                success = bool(
                    self.rng.random()
                    < success_probability
                )

                if success:
                    events.append(
                        self._make_event(
                            event_ts=result_ts,
                            user_id=state.user_id,
                            session_id=session.session_id,
                            event_name="level_complete",
                            level_id=current_level,
                            attempt_number=attempt_number,
                        )
                    )

                    total_completed += 1
                    frustration = max(
                        0.0,
                        frustration
                        - self.config["frustration"][
                            "success_decrease"
                        ],
                    )

                    current_level += 1
                    attempt_number = 1

                else:
                    events.append(
                        self._make_event(
                            event_ts=result_ts,
                            user_id=state.user_id,
                            session_id=session.session_id,
                            event_name="level_fail",
                            level_id=current_level,
                            attempt_number=attempt_number,
                        )
                    )

                    total_failed += 1

                    frustration = self._frustration_after_fail(
                        frustration=frustration,
                        level_id=current_level,
                        attempt_number=attempt_number,
                    )

                    attempt_number += 1

                cursor = (
                    result_ts
                    + self._seconds(
                        self.config[
                            "gap_between_attempts_sec"
                        ]
                    )
                )

        return GameplayResult(
            events=events,
            current_level=current_level,
            frustration_score=frustration,
            total_levels_completed=total_completed,
            total_levels_failed=total_failed,
            next_attempt_number=attempt_number,
        )

    def difficulty_for_level(
        self,
        level_id: int,
        base_difficulty: float,
        experiment: ExperimentAssignment | None = None,
    ) -> float:
        if (
            experiment is None
            or level_id != experiment.eligible_level
        ):
            return float(base_difficulty)

        return float(
            base_difficulty
            * experiment.difficulty_multiplier
        )

    def success_probability(
        self,
        skill: float,
        difficulty: float,
        attempt_number: int,
    ) -> float:
        logit = (
            self.config["skill_weight"] * skill
            - self.config["difficulty_weight"]
            * difficulty
            + self.config["attempt_weight"]
            * log1p(attempt_number)
        )

        probability = 1.0 / (1.0 + exp(-logit))

        return float(
            np.clip(
                probability,
                self.config["min_success_probability"],
                self.config["max_success_probability"],
            )
        )

    def _frustration_after_fail(
        self,
        frustration: float,
        level_id: int,
        attempt_number: int,
    ) -> float:
        config = self.config["frustration"]

        frustration += config["fail_increase"]

        if attempt_number == 3:
            frustration += config["third_fail_extra"]

        if attempt_number == 5:
            frustration += config["fifth_fail_extra"]

        if level_id == 17:
            frustration += config["level_17_fail_extra"]

        return float(
            np.clip(frustration, 0.0, 1.0)
        )

    def _make_event(
        self,
        event_ts,
        user_id,
        session_id,
        event_name,
        level_id,
        attempt_number,
        event_properties: dict | None = None,
    ) -> EventRecord:
        return EventRecord(
            event_id=UUID(
                bytes=self.rng.bytes(16),
                version=4,
            ),
            event_ts=event_ts,
            event_date=event_ts.date(),
            user_id=user_id,
            session_id=session_id,
            event_name=event_name,
            level_id=level_id,
            attempt_number=attempt_number,
            app_version=self.app_version,
            event_properties=(
                {}
                if event_properties is None
                else event_properties
            ),
        )

    @staticmethod
    def _seconds(value: int):
        from datetime import timedelta

        return timedelta(seconds=value)
