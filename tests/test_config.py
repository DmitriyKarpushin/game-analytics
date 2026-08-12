import pytest

from src.config.loader import load_acquisition_config, load_game_config


def test_game_config_loads():
    config = load_game_config()

    assert config["game"]["name"] == "Merge Kingdom"
    assert config["game"]["levels_count"] == 50


@pytest.mark.parametrize(
    "section",
    ["countries", "platforms", "device_tiers"],
)
def test_game_probability_distributions_sum_to_one(section):
    config = load_game_config()

    assert sum(config[section].values()) == pytest.approx(1.0)


def test_acquisition_shares_sum_to_one():
    config = load_acquisition_config()

    shares = [
        channel_config["share"]
        for channel_config in config["channels"].values()
    ]

    assert sum(shares) == pytest.approx(1.0)


def test_latent_beta_parameters_are_positive():
    config = load_game_config()

    for parameter_name in (
        "skill",
        "engagement",
        "payer_propensity",
        "ad_tolerance",
        "base_churn",
    ):
        parameter = config["latent_parameters"][parameter_name]

        assert parameter["alpha"] > 0
        assert parameter["beta"] > 0
