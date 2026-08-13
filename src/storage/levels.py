from dataclasses import dataclass

from psycopg import Connection


@dataclass(frozen=True)
class LevelRecord:
    level_id: int
    base_difficulty: float
    energy_cost: int
    reward_coins: int
    base_duration_sec: int


class LevelRepository:
    def __init__(self, connection: Connection):
        self.connection = connection

    def upsert_levels(
        self,
        levels: list[LevelRecord],
    ) -> None:
        if not levels:
            return

        rows = [
            (
                level.level_id,
                level.base_difficulty,
                level.energy_cost,
                level.reward_coins,
                level.base_duration_sec,
            )
            for level in levels
        ]

        with self.connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO levels (
                    level_id,
                    base_difficulty,
                    energy_cost,
                    reward_coins,
                    base_duration_sec
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (level_id)
                DO UPDATE SET
                    base_difficulty = EXCLUDED.base_difficulty,
                    energy_cost = EXCLUDED.energy_cost,
                    reward_coins = EXCLUDED.reward_coins,
                    base_duration_sec = EXCLUDED.base_duration_sec
                """,
                rows,
            )
