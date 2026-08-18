from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"


def load_yaml(filename: str) -> dict[str, Any]:
    path = CONFIG_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(f"Config must contain a YAML mapping: {path}")

    return data


def load_game_config() -> dict[str, Any]:
    return load_yaml("game.yaml")


def load_acquisition_config() -> dict[str, Any]:
    return load_yaml("acquisition.yaml")


def load_levels_config() -> dict[str, Any]:
    return load_yaml("levels.yaml")


def load_monetization_config() -> dict[str, Any]:
    return load_yaml("monetization.yaml")


def load_app_versions_config() -> dict[str, Any]:
    return load_yaml("app_versions.yaml")

def load_campaigns_config() -> dict[str, Any]:
    return load_yaml("campaigns.yaml")


def load_experiments_config() -> dict[str, Any]:
    return load_yaml("experiments.yaml")

