from unittest.mock import MagicMock

import numpy as np
import pytest

from src.generators.purchases import PurchaseGenerator


def make_generator():
    config = {
        "base_daily_probability": 0.002,
        "payer_propensity_weight": 0.05,
        "repeat_base_daily_probability": 0.10,
        "repeat_payer_propensity_weight": 0.30,
        "repeat_purchase_count_lambda": 1.50,
        "max_purchases_per_day": 3,
        "preferred_price_median_usd": 5.0,
        "preferred_price_sigma": 0.70,
        "products": [],
        "level31_uplift": {
            "level_id": 31,
            "purchase_probability_multiplier": 1.8,
            "preferred_price_multiplier": 1.35,
        },
    }

    return PurchaseGenerator(
        rng=np.random.default_rng(42),
        purchase_config=config,
        app_version="1.0",
    )


def test_level31_increases_first_purchase_probability():
    generator = make_generator()

    baseline = generator.purchase_probability(
        payer_propensity=0.20,
        has_purchased=False,
        current_level=30,
    )

    level31 = generator.purchase_probability(
        payer_propensity=0.20,
        has_purchased=False,
        current_level=31,
    )

    assert level31 == pytest.approx(
        baseline * 1.8
    )


def test_level31_increases_repeat_purchase_probability():
    generator = make_generator()

    baseline = generator.purchase_probability(
        payer_propensity=0.20,
        has_purchased=True,
        current_level=32,
    )

    level31 = generator.purchase_probability(
        payer_propensity=0.20,
        has_purchased=True,
        current_level=31,
    )

    assert level31 == pytest.approx(
        baseline * 1.8
    )


def test_level31_increases_preferred_price():
    generator = make_generator()

    assert generator._preferred_price_multiplier(
        31
    ) == pytest.approx(1.35)


def test_other_levels_have_no_uplift():
    generator = make_generator()

    for level in [1, 17, 30, 32, 50]:
        assert (
            generator._purchase_probability_multiplier(
                level
            )
            == pytest.approx(1.0)
        )

        assert (
            generator._preferred_price_multiplier(
                level
            )
            == pytest.approx(1.0)
        )
