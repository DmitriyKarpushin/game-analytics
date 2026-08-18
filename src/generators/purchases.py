from dataclasses import dataclass
from datetime import timedelta
from math import log
from uuid import UUID

import numpy as np

from src.generators.events import EventRecord
from src.generators.sessions import SessionRecord


@dataclass(frozen=True)
class PurchaseUser:
    user_id: UUID
    payer_propensity: float
    total_spend: float = 0.0
    current_level: int | None = 1


class PurchaseGenerator:
    def __init__(
        self,
        rng: np.random.Generator,
        purchase_config: dict,
        app_version: str,
    ):
        self.rng = rng
        self.config = purchase_config
        self.app_version = app_version

    def purchase_probability(
        self,
        payer_propensity: float,
        has_purchased: bool = False,
        current_level: int = 1,
    ) -> float:
        if has_purchased:
            probability = (
                self.config["repeat_base_daily_probability"]
                + self.config[
                    "repeat_payer_propensity_weight"
                ]
                * payer_propensity
            )
        else:
            probability = (
                self.config["base_daily_probability"]
                + self.config[
                    "payer_propensity_weight"
                ]
                * payer_propensity
            )

        probability *= (
            self._purchase_probability_multiplier(
                current_level
            )
        )

        return float(
            np.clip(
                probability,
                0.0,
                1.0,
            )
        )

    def generate_for_user(
        self,
        user: PurchaseUser,
        sessions: list[SessionRecord],
    ) -> list[EventRecord]:
        if not sessions:
            return []

        has_purchased = user.total_spend > 0.0

        probability = self.purchase_probability(
            payer_propensity=user.payer_propensity,
            has_purchased=has_purchased,
            current_level=user.current_level,
        )

        if self.rng.random() >= probability:
            return []

        purchase_count = self._purchase_count(
            user=user,
            has_purchased=has_purchased,
        )

        events: list[EventRecord] = []

        for _ in range(purchase_count):
            preferred_price = float(
                self.rng.lognormal(
                    mean=log(
                        self.config[
                            "preferred_price_median_usd"
                        ]
                    ),
                    sigma=self.config[
                        "preferred_price_sigma"
                    ],
                )
            )

            preferred_price *= (
                self._preferred_price_multiplier(
                    user.current_level
                )
            )

            product = self._nearest_product(
                preferred_price
            )

            session = sessions[
                int(
                    self.rng.integers(
                        0,
                        len(sessions),
                    )
                )
            ]

            duration_seconds = int(
                (
                    session.session_end_ts
                    - session.session_start_ts
                ).total_seconds()
            )

            offset_seconds = int(
                self.rng.integers(
                    0,
                    max(duration_seconds, 1),
                )
            )

            event_ts = (
                session.session_start_ts
                + timedelta(
                    seconds=offset_seconds
                )
            )

            events.append(
                EventRecord(
                    event_id=UUID(
                        bytes=self.rng.bytes(16),
                        version=4,
                    ),
                    event_ts=event_ts,
                    event_date=event_ts.date(),
                    user_id=user.user_id,
                    session_id=session.session_id,
                    event_name="purchase",
                    level_id=user.current_level,
                    attempt_number=None,
                    app_version=self.app_version,
                    event_properties={
                        "sku": product["sku"],
                        "price_usd": float(
                            product["price_usd"]
                        ),
                        "currency": "USD",
                    },
                )
            )

        events.sort(
            key=lambda event: (
                event.event_ts,
                event.event_id,
            )
        )

        return events

    def _purchase_probability_multiplier(
        self,
        current_level: int | None,
    ) -> float:
        uplift = self.config.get(
            "level31_uplift",
            {},
        )

        if current_level != uplift.get("level_id"):
            return 1.0

        return float(
            uplift.get(
                "purchase_probability_multiplier",
                1.0,
            )
        )

    def _preferred_price_multiplier(
        self,
        current_level: int | None,
    ) -> float:
        uplift = self.config.get(
            "level31_uplift",
            {},
        )

        if current_level != uplift.get("level_id"):
            return 1.0

        return float(
            uplift.get(
                "preferred_price_multiplier",
                1.0,
            )
        )

    def _purchase_count(
        self,
        user: PurchaseUser,
        has_purchased: bool,
    ) -> int:
        if not has_purchased:
            return 1

        extra_purchases = int(
            self.rng.poisson(
                self.config[
                    "repeat_purchase_count_lambda"
                ]
                * user.payer_propensity
            )
        )

        return min(
            1 + extra_purchases,
            self.config["max_purchases_per_day"],
        )

    def _nearest_product(
        self,
        preferred_price: float,
    ) -> dict:
        return min(
            self.config["products"],
            key=lambda product: abs(
                log(float(product["price_usd"]))
                - log(preferred_price)
            ),
        )
