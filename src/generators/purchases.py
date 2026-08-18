from dataclasses import dataclass
from math import log
from uuid import UUID

import numpy as np

from src.generators.events import EventRecord
from src.generators.sessions import SessionRecord


@dataclass(frozen=True)
class PurchaseUser:
    user_id: UUID
    payer_propensity: float


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
    ) -> float:
        probability = (
            self.config["base_daily_probability"]
            + self.config["payer_propensity_weight"]
            * payer_propensity
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

        probability = self.purchase_probability(
            user.payer_propensity
        )

        if self.rng.random() >= probability:
            return []

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

        from datetime import timedelta

        event_ts = (
            session.session_start_ts
            + timedelta(seconds=offset_seconds)
        )

        return [
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
                level_id=None,
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
        ]

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
