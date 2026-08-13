from src.config.loader import load_levels_config
from src.storage.levels import LevelRecord, LevelRepository
from src.storage.postgres import get_connection


def build_level_records() -> list[LevelRecord]:
    config = load_levels_config()["levels"]

    return [
        LevelRecord(
            level_id=int(level_id),
            base_difficulty=float(values["base_difficulty"]),
            energy_cost=int(values["energy_cost"]),
            reward_coins=int(values["reward_coins"]),
            base_duration_sec=int(values["base_duration_sec"]),
        )
        for level_id, values in sorted(
            config.items(),
            key=lambda item: int(item[0]),
        )
    ]


def main() -> None:
    levels = build_level_records()

    with get_connection() as connection:
        repository = LevelRepository(connection)
        repository.upsert_levels(levels)

    print(f"Loaded {len(levels)} levels")


if __name__ == "__main__":
    main()
