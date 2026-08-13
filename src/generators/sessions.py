from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from uuid import UUID

import numpy as np


@dataclass(frozen=True)
class SessionUser:
    user_id: UUID
    engagement_propensity: float
    earliest_start_ts: datetime | None = None


@dataclass(frozen=True)
class SessionRecord:
    session_id: UUID
    user_id: UUID
    session_start_ts: datetime
    session_end_ts: datetime


class SessionGenerator:
    def __init__(
        self,
        rng: np.random.Generator,
        session_config: dict,
    ):
        self.rng = rng
        self.config = session_config

    def generate_for_user(
        self,
        user: SessionUser,
        simulation_date: date,
    ) -> list[SessionRecord]:
        sessions_count = self._sessions_count(
            user.engagement_propensity
        )

        day_start = datetime.combine(
            simulation_date,
            time.min,
        )

        next_day_start = datetime.combine(
            simulation_date + timedelta(days=1),
            time.min,
        )

        earliest_start = max(
            day_start,
            user.earliest_start_ts or day_start,
        )

        # Keep session_end inside the same calendar day.
        available_seconds = (
            int(
                (
                    next_day_start - earliest_start
                ).total_seconds()
            )
            - 1
        )

        min_duration_seconds = (
            self.config["min_duration_minutes"] * 60
        )

        if available_seconds < min_duration_seconds:
            return []

        durations = [
            self._duration_seconds()
            for _ in range(sessions_count)
        ]

        # A late registration may leave too little time
        # for all initially generated sessions.
        while (
            durations
            and sum(durations) > available_seconds
        ):
            durations.pop()

        if not durations:
            return []

        slack_seconds = (
            available_seconds - sum(durations)
        )

        if slack_seconds > 0:
            weights = self.rng.dirichlet(
                np.ones(len(durations) + 1)
            )

            gaps = np.floor(
                weights * slack_seconds
            ).astype(int)

            gaps[-1] += (
                slack_seconds - int(gaps.sum())
            )
        else:
            gaps = np.zeros(
                len(durations) + 1,
                dtype=int,
            )

        cursor = earliest_start + timedelta(
            seconds=int(gaps[0])
        )

        sessions: list[SessionRecord] = []

        for index, duration_seconds in enumerate(durations):
            session_start_ts = cursor
            session_end_ts = (
                session_start_ts
                + timedelta(seconds=duration_seconds)
            )

            sessions.append(
                SessionRecord(
                    session_id=self._generate_uuid(),
                    user_id=user.user_id,
                    session_start_ts=session_start_ts,
                    session_end_ts=session_end_ts,
                )
            )

            cursor = session_end_ts

            if index + 1 < len(durations):
                cursor += timedelta(
                    seconds=int(gaps[index + 1])
                )

        return sessions

    def _sessions_count(
        self,
        engagement_propensity: float,
    ) -> int:
        multiplier = self.config[
            "poisson_engagement_multiplier"
        ]

        count = 1 + int(
            self.rng.poisson(
                multiplier * engagement_propensity
            )
        )

        return min(
            count,
            self.config["max_sessions_per_day"],
        )

    def _duration_seconds(self) -> int:
        median_minutes = self.config[
            "duration_median_minutes"
        ]
        sigma = self.config["duration_sigma"]

        duration_minutes = self.rng.lognormal(
            mean=np.log(median_minutes),
            sigma=sigma,
        )

        duration_minutes = np.clip(
            duration_minutes,
            self.config["min_duration_minutes"],
            self.config["max_duration_minutes"],
        )

        return int(round(duration_minutes * 60))

    def _generate_uuid(self) -> UUID:
        return UUID(
            bytes=self.rng.bytes(16),
            version=4,
        )
