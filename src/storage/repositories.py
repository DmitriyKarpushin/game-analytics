from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from psycopg import Connection

from src.generators.users import UserRecord, UserStateRecord


@dataclass(frozen=True)
class ReturningUserCandidate:
    user_id: UUID
    registration_date: date
    last_active_date: date | None
    engagement_propensity: float
    frustration_score: float
    base_churn_propensity: float


class UserRepository:
    def __init__(self, connection: Connection):
        self.connection = connection

    def insert_users(self, users: Sequence[UserRecord]) -> None:
        if not users:
            return

        rows = [
            (
                user.user_id,
                user.registration_ts,
                user.country,
                user.platform,
                user.device_tier,
                user.acquisition_channel,
                user.campaign_id,
                user.initial_app_version,
            )
            for user in users
        ]

        with self.connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO raw_users (
                    user_id,
                    registration_ts,
                    country,
                    platform,
                    device_tier,
                    acquisition_channel,
                    campaign_id,
                    initial_app_version
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                rows,
            )

    def insert_states(self, states: Sequence[UserStateRecord]) -> None:
        if not states:
            return

        rows = [
            (
                state.user_id,
                state.skill,
                state.engagement_propensity,
                state.payer_propensity,
                state.ad_tolerance,
                state.base_churn_propensity,
                state.current_level,
                state.coins,
                state.gems,
                state.last_active_date,
                state.last_session_ts,
                state.total_sessions,
                state.total_levels_completed,
                state.total_levels_failed,
                state.total_spend,
                state.frustration_score,
                state.is_churned,
            )
            for state in states
        ]

        with self.connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO generator_user_state (
                    user_id,
                    skill,
                    engagement_propensity,
                    payer_propensity,
                    ad_tolerance,
                    base_churn_propensity,
                    current_level,
                    coins,
                    gems,
                    last_active_date,
                    last_session_ts,
                    total_sessions,
                    total_levels_completed,
                    total_levels_failed,
                    total_spend,
                    frustration_score,
                    is_churned
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                """,
                rows,
            )

    def fetch_returning_candidates(
        self,
        simulation_date: date,
    ) -> list[ReturningUserCandidate]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    u.user_id,
                    u.registration_ts::date,
                    s.last_active_date,
                    s.engagement_propensity,
                    s.frustration_score,
                    s.base_churn_propensity
                FROM raw_users u
                JOIN generator_user_state s
                    USING (user_id)
                WHERE
                    u.registration_ts::date < %s
                    AND s.is_churned = FALSE
                ORDER BY u.user_id
                """,
                (simulation_date,),
            )

            rows = cursor.fetchall()

        return [
            ReturningUserCandidate(
                user_id=row[0],
                registration_date=row[1],
                last_active_date=row[2],
                engagement_propensity=float(row[3]),
                frustration_score=float(row[4]),
                base_churn_propensity=float(row[5]),
            )
            for row in rows
        ]
