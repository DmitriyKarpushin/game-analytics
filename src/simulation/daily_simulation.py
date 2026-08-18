from collections import defaultdict
from dataclasses import dataclass
from datetime import date

import numpy as np

from src.config.loader import (
    load_acquisition_config,
    load_app_versions_config,
    load_campaigns_config,
    load_game_config,
    load_levels_config,
    load_monetization_config,
)
from src.generators.ads import AdGenerator, AdUser
from src.generators.events import EventGenerator, EventRecord
from src.generators.gameplay import (
    GameplayGenerator,
    GameplayUserState,
)
from src.generators.purchases import (
    PurchaseGenerator,
    PurchaseUser,
)
from src.generators.sessions import (
    SessionGenerator,
    SessionRecord,
    SessionUser,
)
from src.generators.users import UserGenerator
from src.simulation.app_versions import AppVersionResolver
from src.simulation.campaigns import CampaignResolver
from src.simulation.user_state import (
    ReturningUserState,
    UserActivitySelector,
)
from src.storage.repositories import (
    EventRepository,
    GameplayStateUpdate,
    ReturningUserCandidate,
    UserRepository,
)
from src.storage.simulation_runs import SimulationRunRepository


@dataclass(frozen=True)
class SimulationResult:
    simulation_date: date
    seed: int
    users_created: int
    returning_active_users: int
    sessions_created: int
    events_created: int


class DailySimulation:
    def __init__(
        self,
        run_repository: SimulationRunRepository,
        user_repository: UserRepository,
        event_repository: EventRepository,
        base_seed: int | None = None,
    ):
        self.run_repository = run_repository
        self.user_repository = user_repository
        self.event_repository = event_repository

        self.game_config = load_game_config()
        self.acquisition_config = load_acquisition_config()
        self.levels_config = load_levels_config()["levels"]
        self.monetization_config = load_monetization_config()
        self.app_versions_config = load_app_versions_config()
        self.campaigns_config = load_campaigns_config()

        simulation_config = self.game_config["simulation"]

        self.start_date = date.fromisoformat(
            simulation_config["start_date"]
        )

        self.app_version_resolver = AppVersionResolver(
            start_date=self.start_date,
            config=self.app_versions_config,
        )

        self.campaign_resolver = CampaignResolver(
            start_date=self.start_date,
            config=self.campaigns_config,
        )

        self.base_seed = (
            simulation_config["base_seed"]
            if base_seed is None
            else base_seed
        )

    def run(self, simulation_date: date) -> SimulationResult:
        self.run_repository.ensure_date_can_run(simulation_date)

        seed = self._seed_for_date(simulation_date)
        rng = np.random.default_rng(seed)

        app_version = (
            self.app_version_resolver.version_for_date(
                simulation_date
            )
        )

        self.run_repository.start(
            simulation_date=simulation_date,
            seed=seed,
        )

        users_count = self._generate_new_users_count(
            simulation_date,
            rng,
        )

        user_generator = UserGenerator(
            rng=rng,
            app_version=app_version,
            channel_weights=(
                self._channel_weights_for_date(
                    simulation_date
                )
            ),
            campaign_by_channel=(
                self._campaign_ids_for_date(
                    simulation_date
                )
            ),
        )

        users, states = user_generator.generate(
            count=users_count,
            registration_date=simulation_date,
        )

        self.user_repository.insert_users(users)
        self.user_repository.insert_states(states)

        returning_candidates = (
            self.user_repository.fetch_returning_candidates(
                simulation_date
            )
        )

        active_returning_users = (
            self._select_returning_active_users(
                candidates=returning_candidates,
                simulation_date=simulation_date,
                rng=rng,
                app_version=app_version,
            )
        )

        session_generator = SessionGenerator(
            rng=rng,
            session_config=self.game_config["sessions"],
        )

        sessions: list[SessionRecord] = []

        for user, state in zip(users, states):
            sessions.extend(
                session_generator.generate_for_user(
                    SessionUser(
                        user_id=user.user_id,
                        engagement_propensity=(
                            self._effective_engagement(
                                engagement=state.engagement_propensity,
                                app_version=app_version,
                                platform=user.platform,
                                device_tier=user.device_tier,
                            )
                        ),
                        earliest_start_ts=user.registration_ts,
                    ),
                    simulation_date,
                )
            )

        for candidate in active_returning_users:
            sessions.extend(
                session_generator.generate_for_user(
                    SessionUser(
                        user_id=candidate.user_id,
                        engagement_propensity=(
                            self._effective_engagement(
                                engagement=(
                                    candidate.engagement_propensity
                                ),
                                app_version=app_version,
                                platform=candidate.platform,
                                device_tier=candidate.device_tier,
                            )
                        ),
                    ),
                    simulation_date,
                )
            )

        event_generator = EventGenerator(
            rng=rng,
            app_version=app_version,
        )

        session_events = (
            event_generator.generate_session_events(
                sessions
            )
        )

        gameplay_events, gameplay_updates = (
            self._generate_gameplay(
                rng=rng,
                sessions=sessions,
                new_users=users,
                new_states=states,
                returning_users=active_returning_users,
                app_version=app_version,
            )
        )

        purchase_events = self._generate_purchases(
            rng=rng,
            sessions=sessions,
            new_users=users,
            new_states=states,
            returning_users=active_returning_users,
            app_version=app_version,
        )

        ad_events = self._generate_ads(
            rng=rng,
            sessions=sessions,
            new_users=users,
            new_states=states,
            returning_users=active_returning_users,
            app_version=app_version,
        )

        events: list[EventRecord] = [
            *session_events,
            *gameplay_events,
            *purchase_events,
            *ad_events,
        ]

        events.sort(
            key=lambda event: event.event_ts
        )

        self.event_repository.insert_events(events)

        self.user_repository.update_session_activity(
            sessions=sessions,
            simulation_date=simulation_date,
        )

        self.user_repository.update_gameplay_state(
            gameplay_updates
        )

        self.user_repository.update_purchase_spend(
            purchase_events
        )

        self.run_repository.mark_success(
            simulation_date=simulation_date,
            users_created=len(users),
            events_created=len(events),
        )

        return SimulationResult(
            simulation_date=simulation_date,
            seed=seed,
            users_created=len(users),
            returning_active_users=len(
                active_returning_users
            ),
            sessions_created=len(sessions),
            events_created=len(events),
        )

    def _generate_ads(
        self,
        rng: np.random.Generator,
        sessions: list[SessionRecord],
        new_users,
        new_states,
        returning_users: list[ReturningUserCandidate],
        app_version: str,
    ) -> list[EventRecord]:
        sessions_by_user = defaultdict(list)

        for session in sessions:
            sessions_by_user[session.user_id].append(
                session
            )

        generator = AdGenerator(
            rng=rng,
            ads_config=self.monetization_config["ads"],
            app_version=app_version,
        )

        events: list[EventRecord] = []

        for user, state in zip(new_users, new_states):
            events.extend(
                generator.generate_for_user(
                    AdUser(
                        user_id=user.user_id,
                        engagement_propensity=(
                            self._effective_engagement(
                                engagement=state.engagement_propensity,
                                app_version=app_version,
                                platform=user.platform,
                                device_tier=user.device_tier,
                            )
                        ),
                        ad_tolerance=state.ad_tolerance,
                    ),
                    sessions_by_user.get(
                        user.user_id,
                        [],
                    ),
                )
            )

        for candidate in returning_users:
            events.extend(
                generator.generate_for_user(
                    AdUser(
                        user_id=candidate.user_id,
                        engagement_propensity=(
                            self._effective_engagement(
                                engagement=(
                                    candidate.engagement_propensity
                                ),
                                app_version=app_version,
                                platform=candidate.platform,
                                device_tier=candidate.device_tier,
                            )
                        ),
                        ad_tolerance=(
                            candidate.ad_tolerance
                        ),
                    ),
                    sessions_by_user.get(
                        candidate.user_id,
                        [],
                    ),
                )
            )

        return events

    def _generate_purchases(
        self,
        rng: np.random.Generator,
        sessions: list[SessionRecord],
        new_users,
        new_states,
        returning_users: list[ReturningUserCandidate],
        app_version: str,
    ) -> list[EventRecord]:
        sessions_by_user = defaultdict(list)

        for session in sessions:
            sessions_by_user[session.user_id].append(
                session
            )

        generator = PurchaseGenerator(
            rng=rng,
            purchase_config=self.monetization_config[
                "purchase"
            ],
            app_version=app_version,
        )

        events: list[EventRecord] = []

        for user, state in zip(new_users, new_states):
            events.extend(
                generator.generate_for_user(
                    PurchaseUser(
                        user_id=user.user_id,
                        payer_propensity=(
                            state.payer_propensity
                        ),
                        total_spend=state.total_spend,
                        current_level=state.current_level,
                    ),
                    sessions_by_user.get(
                        user.user_id,
                        [],
                    ),
                )
            )

        for candidate in returning_users:
            events.extend(
                generator.generate_for_user(
                    PurchaseUser(
                        user_id=candidate.user_id,
                        payer_propensity=(
                            candidate.payer_propensity
                        ),
                        total_spend=(
                            candidate.total_spend
                        ),
                        current_level=(
                            candidate.current_level
                        ),
                    ),
                    sessions_by_user.get(
                        candidate.user_id,
                        [],
                    ),
                )
            )

        return events

    def _generate_gameplay(
        self,
        rng: np.random.Generator,
        sessions: list[SessionRecord],
        new_users,
        new_states,
        returning_users: list[ReturningUserCandidate],
        app_version: str,
    ) -> tuple[
        list[EventRecord],
        list[GameplayStateUpdate],
    ]:
        sessions_by_user = defaultdict(list)

        for session in sessions:
            sessions_by_user[session.user_id].append(
                session
            )

        generator = GameplayGenerator(
            rng=rng,
            gameplay_config=self.game_config["gameplay"],
            levels_config=self.levels_config,
            app_version=app_version,
        )

        events: list[EventRecord] = []
        updates: list[GameplayStateUpdate] = []

        for user, state in zip(new_users, new_states):
            user_sessions = sessions_by_user.get(
                user.user_id,
                [],
            )

            if not user_sessions:
                continue

            result = generator.generate(
                GameplayUserState(
                    user_id=user.user_id,
                    skill=state.skill,
                    current_level=state.current_level,
                    frustration_score=(
                        state.frustration_score
                    ),
                    total_levels_completed=(
                        state.total_levels_completed
                    ),
                    total_levels_failed=(
                        state.total_levels_failed
                    ),
                    next_attempt_number=1,
                ),
                user_sessions,
            )

            events.extend(result.events)

            updates.append(
                GameplayStateUpdate(
                    user_id=user.user_id,
                    current_level=result.current_level,
                    frustration_score=(
                        result.frustration_score
                    ),
                    total_levels_completed=(
                        result.total_levels_completed
                    ),
                    total_levels_failed=(
                        result.total_levels_failed
                    ),
                )
            )

        for candidate in returning_users:
            user_sessions = sessions_by_user.get(
                candidate.user_id,
                [],
            )

            if not user_sessions:
                continue

            result = generator.generate(
                GameplayUserState(
                    user_id=candidate.user_id,
                    skill=candidate.skill,
                    current_level=candidate.current_level,
                    frustration_score=(
                        candidate.frustration_score
                    ),
                    total_levels_completed=(
                        candidate.total_levels_completed
                    ),
                    total_levels_failed=(
                        candidate.total_levels_failed
                    ),
                    next_attempt_number=(
                        candidate.next_attempt_number
                    ),
                ),
                user_sessions,
            )

            events.extend(result.events)

            updates.append(
                GameplayStateUpdate(
                    user_id=candidate.user_id,
                    current_level=result.current_level,
                    frustration_score=(
                        result.frustration_score
                    ),
                    total_levels_completed=(
                        result.total_levels_completed
                    ),
                    total_levels_failed=(
                        result.total_levels_failed
                    ),
                )
            )

        return events, updates

    def _effective_engagement(
        self,
        engagement: float,
        app_version: str,
        platform: str,
        device_tier: str,
    ) -> float:
        multiplier = (
            self.app_version_resolver.engagement_multiplier(
                version=app_version,
                platform=platform,
                device_tier=device_tier,
            )
        )

        return float(
            np.clip(
                engagement * multiplier,
                0.01,
                0.99,
            )
        )

    def _select_returning_active_users(
        self,
        candidates: list[ReturningUserCandidate],
        simulation_date: date,
        rng: np.random.Generator,
        app_version: str,
    ) -> list[ReturningUserCandidate]:
        selector = UserActivitySelector(
            rng=rng,
            activity_config=self.game_config["activity"],
        )

        default_recent_success = self.game_config[
            "activity"
        ]["default_recent_success"]

        active_users: list[ReturningUserCandidate] = []

        for candidate in candidates:
            state = ReturningUserState(
                user_id=candidate.user_id,
                registration_date=(
                    candidate.registration_date
                ),
                last_active_date=(
                    candidate.last_active_date
                ),
                engagement_propensity=(
                    self._effective_engagement(
                        engagement=(
                            candidate.engagement_propensity
                        ),
                        app_version=app_version,
                        platform=candidate.platform,
                        device_tier=candidate.device_tier,
                    )
                ),
                frustration_score=(
                    candidate.frustration_score
                ),
                base_churn_propensity=(
                    candidate.base_churn_propensity
                ),
                recent_success=(
                    candidate.recent_success
                    if candidate.recent_success is not None
                    else default_recent_success
                ),
            )

            if selector.is_active(
                state,
                simulation_date,
            ):
                active_users.append(candidate)

        return active_users

    def _channel_weights_for_date(
        self,
        simulation_date: date,
    ) -> dict[str, float]:
        channels = self.acquisition_config["channels"]

        return {
            channel: (
                float(config["share"])
                * self.campaign_resolver.multiplier_for_channel(
                    simulation_date,
                    channel,
                )
            )
            for channel, config in channels.items()
        }

    def _campaign_ids_for_date(
        self,
        simulation_date: date,
    ) -> dict[str, str]:
        result: dict[str, str] = {}

        for channel in self.acquisition_config["channels"]:
            campaign_id = (
                self.campaign_resolver.campaign_id_for_channel(
                    simulation_date,
                    channel,
                )
            )

            if campaign_id is not None:
                result[channel] = campaign_id

        return result

    def _campaign_factor_for_date(
        self,
        simulation_date: date,
    ) -> float:
        return float(
            sum(
                self._channel_weights_for_date(
                    simulation_date
                ).values()
            )
        )

    def _lambda_for_date(
        self,
        simulation_date: date,
    ) -> float:
        day_number = (
            simulation_date - self.start_date
        ).days

        if day_number < 0:
            raise ValueError(
                "Simulation date cannot be earlier than start date"
            )

        config = self.acquisition_config["new_users"]

        trend = (
            1.0
            + day_number * config["daily_trend"]
        )

        weekday_name = (
            simulation_date.strftime("%A").lower()
        )

        weekday_factor = config[
            "weekday_factors"
        ][weekday_name]

        campaign_factor = (
            self._campaign_factor_for_date(
                simulation_date
            )
        )

        return (
            config["base_lambda"]
            * trend
            * weekday_factor
            * campaign_factor
        )

    def _generate_new_users_count(
        self,
        simulation_date: date,
        rng: np.random.Generator,
    ) -> int:
        lambda_day = self._lambda_for_date(
            simulation_date
        )

        return int(rng.poisson(lambda_day))

    def _seed_for_date(
        self,
        simulation_date: date,
    ) -> int:
        seed_sequence = np.random.SeedSequence(
            [
                self.base_seed,
                simulation_date.toordinal(),
            ]
        )

        return int(
            seed_sequence.generate_state(
                1,
                dtype=np.uint64,
            )[0]
            & ((1 << 63) - 1)
        )
