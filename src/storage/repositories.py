from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from psycopg import Connection
from psycopg.types.json import Jsonb

from src.generators.events import EventRecord
from src.generators.sessions import SessionRecord
from src.generators.users import UserRecord, UserStateRecord


@dataclass(frozen=True)
class ReturningUserCandidate:
    user_id: UUID
    registration_date: date
    last_active_date: date | None
    engagement_propensity: float
    frustration_score: float
    base_churn_propensity: float
    payer_propensity: float = 0.0
    ad_tolerance: float = 0.5
    total_spend: float = 0.0
    recent_success: float | None = None
    skill: float = 0.5
    current_level: int = 1
    total_levels_completed: int = 0
    total_levels_failed: int = 0
    next_attempt_number: int = 1


@dataclass(frozen=True)
class GameplayStateUpdate:
    user_id: UUID
    current_level: int
    frustration_score: float
    total_levels_completed: int
    total_levels_failed: int


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
                    s.base_churn_propensity,
                    s.payer_propensity,
                    s.ad_tolerance,
                    s.total_spend,
                    (
                        SELECT AVG(
                            CASE
                                WHEN recent.event_name = 'level_complete'
                                THEN 1.0
                                ELSE 0.0
                            END
                        )
                        FROM (
                            SELECT e.event_name
                            FROM raw_events e
                            WHERE
                                e.user_id = u.user_id
                                AND e.event_name IN (
                                    'level_complete',
                                    'level_fail'
                                )
                            ORDER BY
                                e.event_ts DESC,
                                e.event_id DESC
                            LIMIT 5
                        ) AS recent
                    ) AS recent_success,
                    s.skill,
                    s.current_level,
                    s.total_levels_completed,
                    s.total_levels_failed,
                    CASE
                        WHEN s.current_level BETWEEN 1 AND 50
                        THEN COALESCE(
                            (
                                SELECT MAX(e.attempt_number) + 1
                                FROM raw_events e
                                WHERE
                                    e.user_id = u.user_id
                                    AND e.level_id = s.current_level
                                    AND e.event_name = 'level_fail'
                            ),
                            1
                        )
                        ELSE 1
                    END AS next_attempt_number
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
                payer_propensity=float(row[6]),
                ad_tolerance=float(row[7]),
                total_spend=float(row[8]),
                recent_success=(
                    None
                    if row[9] is None
                    else float(row[9])
                ),
                skill=float(row[10]),
                current_level=int(row[11]),
                total_levels_completed=int(row[12]),
                total_levels_failed=int(row[13]),
                next_attempt_number=int(row[14]),
            )
            for row in rows
        ]

    def update_session_activity(
        self,
        sessions: Sequence[SessionRecord],
        simulation_date: date,
    ) -> None:
        if not sessions:
            return

        summary: dict[UUID, dict] = {}

        for session in sessions:
            user_summary = summary.setdefault(
                session.user_id,
                {
                    "sessions_count": 0,
                    "last_session_ts": session.session_end_ts,
                },
            )

            user_summary["sessions_count"] += 1

            if (
                session.session_end_ts
                > user_summary["last_session_ts"]
            ):
                user_summary["last_session_ts"] = (
                    session.session_end_ts
                )

        rows = [
            (
                simulation_date,
                values["last_session_ts"],
                values["sessions_count"],
                user_id,
            )
            for user_id, values in summary.items()
        ]

        with self.connection.cursor() as cursor:
            cursor.executemany(
                """
                UPDATE generator_user_state
                SET
                    last_active_date = %s,
                    last_session_ts = %s,
                    total_sessions = total_sessions + %s
                WHERE user_id = %s
                """,
                rows,
            )

    def update_purchase_spend(
        self,
        events: Sequence[EventRecord],
    ) -> None:
        purchases = [
            event
            for event in events
            if event.event_name == "purchase"
        ]

        if not purchases:
            return

        spend_by_user: dict[UUID, float] = {}

        for event in purchases:
            price_usd = float(
                event.event_properties["price_usd"]
            )

            spend_by_user[event.user_id] = (
                spend_by_user.get(event.user_id, 0.0)
                + price_usd
            )

        rows = [
            (
                total_spend,
                user_id,
            )
            for user_id, total_spend
            in spend_by_user.items()
        ]

        with self.connection.cursor() as cursor:
            cursor.executemany(
                '''
                UPDATE generator_user_state
                SET total_spend = total_spend + %s
                WHERE user_id = %s
                ''',
                rows,
            )


    def update_gameplay_state(
        self,
        updates: Sequence[GameplayStateUpdate],
    ) -> None:
        if not updates:
            return

        rows = [
            (
                update.current_level,
                update.frustration_score,
                update.total_levels_completed,
                update.total_levels_failed,
                update.user_id,
            )
            for update in updates
        ]

        with self.connection.cursor() as cursor:
            cursor.executemany(
                """
                UPDATE generator_user_state
                SET
                    current_level = %s,
                    frustration_score = %s,
                    total_levels_completed = %s,
                    total_levels_failed = %s
                WHERE user_id = %s
                """,
                rows,
            )


class EventRepository:
    def __init__(self, connection: Connection):
        self.connection = connection

    def insert_events(
        self,
        events: Sequence[EventRecord],
    ) -> None:
        if not events:
            return

        rows = [
            (
                event.event_id,
                event.event_ts,
                event.event_date,
                event.user_id,
                event.session_id,
                event.event_name,
                event.level_id,
                event.attempt_number,
                event.app_version,
                Jsonb(event.event_properties),
            )
            for event in events
        ]

        with self.connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO raw_events (
                    event_id,
                    event_ts,
                    event_date,
                    user_id,
                    session_id,
                    event_name,
                    level_id,
                    attempt_number,
                    app_version,
                    event_properties
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                """,
                rows,
            )
