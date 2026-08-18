from dataclasses import dataclass
from datetime import date, datetime, timedelta
from uuid import UUID

import numpy as np

from src.config.loader import load_acquisition_config, load_game_config


@dataclass(frozen=True)
class UserRecord:
    user_id: UUID
    registration_ts: datetime
    country: str
    platform: str
    device_tier: str
    acquisition_channel: str
    campaign_id: str | None
    initial_app_version: str


@dataclass(frozen=True)
class UserStateRecord:
    user_id: UUID
    skill: float
    engagement_propensity: float
    payer_propensity: float
    ad_tolerance: float
    base_churn_propensity: float
    current_level: int = 1
    coins: int = 0
    gems: int = 0
    last_active_date: date | None = None
    last_session_ts: datetime | None = None
    total_sessions: int = 0
    total_levels_completed: int = 0
    total_levels_failed: int = 0
    total_spend: float = 0.0
    frustration_score: float = 0.0
    is_churned: bool = False


class UserGenerator:
    def __init__(
        self,
        rng: np.random.Generator,
        app_version: str | None = None,
        channel_weights: dict[str, float] | None = None,
        campaign_by_channel: dict[str, str] | None = None,
    ):
        self.rng = rng
        self.game_config = load_game_config()
        self.acquisition_config = load_acquisition_config()

        self.app_version = (
            app_version
            if app_version is not None
            else self.game_config["game"][
                "default_app_version"
            ]
        )

        self.channel_weights = channel_weights
        self.campaign_by_channel = (
            campaign_by_channel
            if campaign_by_channel is not None
            else {}
        )

    def generate(
        self,
        count: int,
        registration_date: date,
    ) -> tuple[list[UserRecord], list[UserStateRecord]]:
        users: list[UserRecord] = []
        states: list[UserStateRecord] = []

        for _ in range(count):
            user, state = self._generate_user(registration_date)
            users.append(user)
            states.append(state)

        return users, states

    def _generate_user(
        self,
        registration_date: date,
    ) -> tuple[UserRecord, UserStateRecord]:
        user_id = self._generate_uuid()

        country = self._weighted_choice(self.game_config["countries"])
        platform = self._weighted_choice(self.game_config["platforms"])
        device_tier = self._weighted_choice(self.game_config["device_tiers"])

        channels = self.acquisition_config["channels"]

        channel_weights = (
            self.channel_weights
            if self.channel_weights is not None
            else {
                name: config["share"]
                for name, config in channels.items()
            }
        )

        acquisition_channel = self._weighted_choice(
            channel_weights
        )

        registration_ts = self._generate_registration_ts(registration_date)

        latent = self.game_config["latent_parameters"]

        skill = self.rng.beta(
            latent["skill"]["alpha"],
            latent["skill"]["beta"],
        )

        engagement = self.rng.beta(
            latent["engagement"]["alpha"],
            latent["engagement"]["beta"],
        )
        engagement += channels[acquisition_channel]["engagement_modifier"]
        engagement = np.clip(
            engagement,
            latent["engagement"]["min"],
            latent["engagement"]["max"],
        )

        payer_propensity = self.rng.beta(
            latent["payer_propensity"]["alpha"],
            latent["payer_propensity"]["beta"],
        )
        payer_propensity *= channels[acquisition_channel]["payer_multiplier"]
        payer_propensity *= self.acquisition_config[
            "platform_payer_multiplier"
        ][platform]
        payer_propensity = np.clip(payer_propensity, 0.0, 1.0)

        ad_tolerance = self.rng.beta(
            latent["ad_tolerance"]["alpha"],
            latent["ad_tolerance"]["beta"],
        )

        sampled_churn = self.rng.beta(
            latent["base_churn"]["alpha"],
            latent["base_churn"]["beta"],
        )
        base_churn_propensity = (
            latent["base_churn"]["sampled_weight"] * sampled_churn
            + latent["base_churn"]["inverse_engagement_weight"]
            * (1.0 - engagement)
        )

        user = UserRecord(
            user_id=user_id,
            registration_ts=registration_ts,
            country=country,
            platform=platform,
            device_tier=device_tier,
            acquisition_channel=acquisition_channel,
            campaign_id=self.campaign_by_channel.get(
                acquisition_channel
            ),
            initial_app_version=self.app_version,
        )

        state = UserStateRecord(
            user_id=user_id,
            skill=float(skill),
            engagement_propensity=float(engagement),
            payer_propensity=float(payer_propensity),
            ad_tolerance=float(ad_tolerance),
            base_churn_propensity=float(base_churn_propensity),
        )

        return user, state

    def _weighted_choice(self, values: dict[str, float]) -> str:
        names = list(values)

        probabilities = np.asarray(
            list(values.values()),
            dtype=float,
        )

        total = float(probabilities.sum())

        if total <= 0:
            raise ValueError(
                "Weighted choice requires positive total weight"
            )

        probabilities = probabilities / total

        return str(
            self.rng.choice(
                names,
                p=probabilities,
            )
        )

    def _generate_registration_ts(self, registration_date: date) -> datetime:
        seconds = int(self.rng.integers(0, 24 * 60 * 60))

        return datetime.combine(
            registration_date,
            datetime.min.time(),
        ) + timedelta(seconds=seconds)

    def _generate_uuid(self) -> UUID:
        return UUID(bytes=self.rng.bytes(16), version=4)
