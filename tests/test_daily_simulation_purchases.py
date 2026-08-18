from datetime import date
from unittest.mock import MagicMock

from src.simulation.daily_simulation import DailySimulation


def test_daily_simulation_generates_and_persists_purchases():
    run_repository = MagicMock()
    user_repository = MagicMock()
    event_repository = MagicMock()

    user_repository.fetch_returning_candidates.return_value = []

    simulation = DailySimulation(
        run_repository=run_repository,
        user_repository=user_repository,
        event_repository=event_repository,
        base_seed=42,
    )

    # Keep the test small and deterministic.
    simulation._generate_new_users_count = (
        lambda simulation_date, rng: 20
    )

    # Force every user with at least one session to purchase.
    purchase_config = simulation.monetization_config[
        "purchase"
    ]

    purchase_config["base_daily_probability"] = 1.0
    purchase_config["payer_propensity_weight"] = 0.0

    result = simulation.run(
        date(2026, 1, 1)
    )

    events = (
        event_repository
        .insert_events
        .call_args
        .args[0]
    )

    purchases = [
        event
        for event in events
        if event.event_name == "purchase"
    ]

    session_starts = {
        (
            event.user_id,
            event.session_id,
        )
        for event in events
        if event.event_name == "session_start"
    }

    assert result.users_created == 20
    assert len(purchases) > 0

    # Maximum one purchase per active user per day.
    assert len(
        {
            event.user_id
            for event in purchases
        }
    ) == len(purchases)

    # Every purchase belongs to a real session.
    for purchase in purchases:
        assert (
            purchase.user_id,
            purchase.session_id,
        ) in session_starts

    user_repository.update_purchase_spend.assert_called_once()

    persisted_purchases = (
        user_repository
        .update_purchase_spend
        .call_args
        .args[0]
    )

    assert len(persisted_purchases) == len(purchases)

    assert {
        event.event_id
        for event in persisted_purchases
    } == {
        event.event_id
        for event in purchases
    }
