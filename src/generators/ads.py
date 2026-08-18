from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

import numpy as np

from src.generators.events import EventRecord
from src.generators.sessions import SessionRecord


@dataclass(frozen=True)
class AdUser:
    user_id: UUID
    engagement_propensity: float
    ad_tolerance: float


class AdGenerator:
    def __init__(
        self,
        rng: np.random.Generator,
        ads_config: dict,
        app_version: str,
    ):
        self.rng = rng
        self.config = ads_config
        self.app_version = app_version

    def rewarded_probability(
        self,
        ad_tolerance: float,
        engagement_propensity: float,
    ) -> float:
        config = self.config["rewarded"]

        probability = (
            config["base_probability"]
            + config["ad_tolerance_weight"]
            * ad_tolerance
            + config["engagement_weight"]
            * engagement_propensity
        )

        return float(
            np.clip(
                probability,
                0.0,
                config["max_probability"],
            )
        )

    def interstitial_probability(
        self,
        ad_tolerance: float,
    ) -> float:
        config = self.config["interstitial"]

        probability = (
            config["base_probability"]
            + config["ad_tolerance_weight"]
            * ad_tolerance
        )

        return float(
            np.clip(
                probability,
                config["min_probability"],
                1.0,
            )
        )

    def generate_for_user(
        self,
        user: AdUser,
        sessions: list[SessionRecord],
    ) -> list[EventRecord]:
        events: list[EventRecord] = []

        for session in sessions:
            rewarded_probability = self.rewarded_probability(
                ad_tolerance=user.ad_tolerance,
                engagement_propensity=(
                    user.engagement_propensity
                ),
            )

            if self.rng.random() < rewarded_probability:
                events.extend(
                    self._make_ad_pair(
                        user_id=user.user_id,
                        session=session,
                        ad_format="rewarded",
                        revenue_usd=float(
                            self.config["rewarded"][
                                "revenue_per_impression_usd"
                            ]
                        ),
                    )
                )

            interstitial_probability = (
                self.interstitial_probability(
                    ad_tolerance=user.ad_tolerance
                )
            )

            if self.rng.random() < interstitial_probability:
                events.extend(
                    self._make_ad_pair(
                        user_id=user.user_id,
                        session=session,
                        ad_format="interstitial",
                        revenue_usd=float(
                            self.config["interstitial"][
                                "revenue_per_impression_usd"
                            ]
                        ),
                    )
                )

        events.sort(
            key=lambda event: (
                event.event_ts,
                event.event_id,
            )
        )

        return events

    def _make_ad_pair(
        self,
        user_id: UUID,
        session: SessionRecord,
        ad_format: str,
        revenue_usd: float,
    ) -> list[EventRecord]:
        duration_seconds = max(
            int(
                (
                    session.session_end_ts
                    - session.session_start_ts
                ).total_seconds()
            ),
            2,
        )

        offset_seconds = int(
            self.rng.integers(
                0,
                duration_seconds - 1,
            )
        )

        impression_ts = (
            session.session_start_ts
            + timedelta(seconds=offset_seconds)
        )

        revenue_ts = impression_ts + timedelta(seconds=1)

        common_properties = {
            "ad_format": ad_format,
            "revenue_usd": revenue_usd,
        }

        return [
            EventRecord(
                event_id=UUID(
                    bytes=self.rng.bytes(16),
                    version=4,
                ),
                event_ts=impression_ts,
                event_date=impression_ts.date(),
                user_id=user_id,
                session_id=session.session_id,
                event_name="ad_impression",
                level_id=None,
                attempt_number=None,
                app_version=self.app_version,
                event_properties=common_properties,
            ),
            EventRecord(
                event_id=UUID(
                    bytes=self.rng.bytes(16),
                    version=4,
                ),
                event_ts=revenue_ts,
                event_date=revenue_ts.date(),
                user_id=user_id,
                session_id=session.session_id,
                event_name="ad_revenue",
                level_id=None,
                attempt_number=None,
                app_version=self.app_version,
                event_properties=common_properties,
            ),
        ]
