from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from psycopg import Connection

from src.config.loader import (
    load_app_versions_config,
    load_campaigns_config,
    load_experiments_config,
    load_game_config,
)
from src.experiments import ExperimentResolver
from src.simulation.app_versions import AppVersionResolver
from src.simulation.campaigns import CampaignResolver


@dataclass(frozen=True)
class ValidationCheck:
    name: str
    passed: bool
    details: str


@dataclass(frozen=True)
class RawValidationReport:
    checks: tuple[ValidationCheck, ...]

    @property
    def passed(self) -> bool:
        return all(
            check.passed
            for check in self.checks
        )


class RawValidator:
    def __init__(
        self,
        connection: Connection,
    ):
        self.connection = connection

        game_config = load_game_config()

        self.start_date = date.fromisoformat(
            game_config["simulation"][
                "start_date"
            ]
        )

        self.app_version_resolver = (
            AppVersionResolver(
                start_date=self.start_date,
                config=load_app_versions_config(),
            )
        )

        self.campaign_resolver = (
            CampaignResolver(
                start_date=self.start_date,
                config=load_campaigns_config(),
            )
        )

        self.experiments_config = (
            load_experiments_config()
        )

        self.experiment_resolver = (
            ExperimentResolver(
                start_date=self.start_date,
                config=self.experiments_config,
            )
        )

    def validate(self) -> RawValidationReport:
        checks = (
            self._check_simulation_history(),
            self._check_run_statuses(),
            self._check_user_state_integrity(),
            self._check_run_counts(),
            self._check_event_users(),
            self._check_sessions(),
            self._check_levels(),
            self._check_app_versions(),
            self._check_campaigns(),
            *self._check_experiments(),
        )

        return RawValidationReport(
            checks=checks
        )

    def _check_simulation_history(
        self,
    ) -> ValidationCheck:
        rows = self._rows(
            """
            SELECT simulation_date
            FROM simulation_runs
            ORDER BY simulation_date
            """
        )

        if not rows:
            return ValidationCheck(
                name="simulation_history_contiguous",
                passed=False,
                details="simulation_runs is empty",
            )

        actual = [
            row[0]
            for row in rows
        ]

        expected = _date_range(
            self.start_date,
            actual[-1],
        )

        missing = sorted(
            set(expected)
            - set(actual)
        )

        unexpected = sorted(
            set(actual)
            - set(expected)
        )

        passed = (
            actual[0] == self.start_date
            and not missing
            and not unexpected
        )

        return ValidationCheck(
            name="simulation_history_contiguous",
            passed=passed,
            details=(
                f"runs={len(actual)} "
                f"first={actual[0]} "
                f"last={actual[-1]} "
                f"missing={len(missing)} "
                f"unexpected={len(unexpected)}"
            ),
        )

    def _check_run_statuses(
        self,
    ) -> ValidationCheck:
        rows = self._rows(
            """
            SELECT
                simulation_date,
                status
            FROM simulation_runs
            WHERE status <> 'success'
            ORDER BY simulation_date
            """
        )

        preview = ", ".join(
            f"{row[0]}:{row[1]}"
            for row in rows[:5]
        )

        return ValidationCheck(
            name="simulation_runs_successful",
            passed=not rows,
            details=(
                "all success"
                if not rows
                else (
                    f"non_success={len(rows)} "
                    f"examples={preview}"
                )
            ),
        )

    def _check_user_state_integrity(
        self,
    ) -> ValidationCheck:
        users_without_state = self._scalar(
            """
            SELECT COUNT(*)
            FROM raw_users u
            LEFT JOIN generator_user_state s
                USING (user_id)
            WHERE s.user_id IS NULL
            """
        )

        states_without_user = self._scalar(
            """
            SELECT COUNT(*)
            FROM generator_user_state s
            LEFT JOIN raw_users u
                USING (user_id)
            WHERE u.user_id IS NULL
            """
        )

        return ValidationCheck(
            name="user_state_1_to_1",
            passed=(
                users_without_state == 0
                and states_without_user == 0
            ),
            details=(
                f"users_without_state="
                f"{users_without_state} "
                f"states_without_user="
                f"{states_without_user}"
            ),
        )

    def _check_run_counts(
        self,
    ) -> ValidationCheck:
        run_rows = self._rows(
            """
            SELECT
                simulation_date,
                users_created,
                events_created
            FROM simulation_runs
            ORDER BY simulation_date
            """
        )

        user_rows = self._rows(
            """
            SELECT
                registration_ts::date,
                COUNT(*)
            FROM raw_users
            GROUP BY registration_ts::date
            """
        )

        event_rows = self._rows(
            """
            SELECT
                event_date,
                COUNT(*)
            FROM raw_events
            GROUP BY event_date
            """
        )

        runs = {
            row[0]: (
                int(row[1]),
                int(row[2]),
            )
            for row in run_rows
        }

        user_counts = {
            row[0]: int(row[1])
            for row in user_rows
        }

        event_counts = {
            row[0]: int(row[1])
            for row in event_rows
        }

        all_dates = (
            set(runs)
            | set(user_counts)
            | set(event_counts)
        )

        mismatches = []

        for simulation_date in sorted(
            all_dates
        ):
            expected = runs.get(
                simulation_date
            )

            actual = (
                user_counts.get(
                    simulation_date,
                    0,
                ),
                event_counts.get(
                    simulation_date,
                    0,
                ),
            )

            if expected != actual:
                mismatches.append(
                    (
                        simulation_date,
                        expected,
                        actual,
                    )
                )

        preview = ", ".join(
            str(item[0])
            for item in mismatches[:5]
        )

        return ValidationCheck(
            name="simulation_run_counts_match",
            passed=not mismatches,
            details=(
                f"dates={len(all_dates)} "
                f"mismatches={len(mismatches)}"
                + (
                    ""
                    if not preview
                    else f" examples={preview}"
                )
            ),
        )

    def _check_event_users(
        self,
    ) -> ValidationCheck:
        count = self._scalar(
            """
            SELECT COUNT(*)
            FROM raw_events e
            LEFT JOIN raw_users u
                USING (user_id)
            WHERE u.user_id IS NULL
            """
        )

        return ValidationCheck(
            name="event_users_exist",
            passed=count == 0,
            details=f"orphan_events={count}",
        )

    def _check_sessions(
        self,
    ) -> ValidationCheck:
        count = self._scalar(
            """
            WITH session_summary AS (
                SELECT
                    session_id,
                    COUNT(*) FILTER (
                        WHERE event_name
                            = 'session_start'
                    ) AS starts,
                    COUNT(*) FILTER (
                        WHERE event_name
                            = 'session_end'
                    ) AS ends,
                    COUNT(
                        DISTINCT user_id
                    ) AS users
                FROM raw_events
                WHERE session_id IS NOT NULL
                GROUP BY session_id
            )
            SELECT COUNT(*)
            FROM session_summary
            WHERE
                starts <> 1
                OR ends <> 1
                OR users <> 1
            """
        )

        return ValidationCheck(
            name="session_integrity",
            passed=count == 0,
            details=(
                f"invalid_sessions={count}"
            ),
        )

    def _check_levels(
        self,
    ) -> ValidationCheck:
        count = self._scalar(
            """
            SELECT COUNT(*)
            FROM raw_events e
            LEFT JOIN levels l
                USING (level_id)
            WHERE
                e.level_id IS NOT NULL
                AND l.level_id IS NULL
            """
        )

        return ValidationCheck(
            name="event_levels_exist",
            passed=count == 0,
            details=(
                f"orphan_level_events={count}"
            ),
        )

    def _check_app_versions(
        self,
    ) -> ValidationCheck:
        event_rows = self._rows(
            """
            SELECT
                event_date,
                app_version,
                COUNT(*)
            FROM raw_events
            GROUP BY
                event_date,
                app_version
            """
        )

        user_rows = self._rows(
            """
            SELECT
                registration_ts::date,
                initial_app_version,
                COUNT(*)
            FROM raw_users
            GROUP BY
                registration_ts::date,
                initial_app_version
            """
        )

        mismatches = 0

        for event_date, version, count in (
            event_rows
        ):
            try:
                expected = (
                    self.app_version_resolver
                    .version_for_date(
                        event_date
                    )
                )
            except ValueError:
                expected = None

            if version != expected:
                mismatches += int(count)

        for registration_date, version, count in (
            user_rows
        ):
            try:
                expected = (
                    self.app_version_resolver
                    .version_for_date(
                        registration_date
                    )
                )
            except ValueError:
                expected = None

            if version != expected:
                mismatches += int(count)

        return ValidationCheck(
            name="app_version_schedule",
            passed=mismatches == 0,
            details=(
                f"mismatched_rows={mismatches}"
            ),
        )

    def _check_campaigns(
        self,
    ) -> ValidationCheck:
        rows = self._rows(
            """
            SELECT
                registration_ts::date,
                acquisition_channel,
                campaign_id,
                COUNT(*)
            FROM raw_users
            GROUP BY
                registration_ts::date,
                acquisition_channel,
                campaign_id
            """
        )

        mismatches = 0

        for (
            registration_date,
            channel,
            campaign_id,
            count,
        ) in rows:
            try:
                expected = (
                    self.campaign_resolver
                    .campaign_id_for_channel(
                        registration_date,
                        channel,
                    )
                )
            except ValueError:
                expected = "__invalid__"

            if campaign_id != expected:
                mismatches += int(count)

        return ValidationCheck(
            name="campaign_assignments",
            passed=mismatches == 0,
            details=(
                f"mismatched_users={mismatches}"
            ),
        )

    def _check_experiments(
        self,
    ) -> tuple[ValidationCheck, ...]:
        rows = self._rows(
            """
            SELECT
                user_id,
                event_date,
                level_id,
                attempt_number,
                session_id,
                event_properties
                    ->> 'experiment_id',
                event_properties
                    ->> 'variant'
            FROM raw_events
            WHERE event_name
                = 'experiment_exposure'
            """
        )

        experiments = {
            str(item["experiment_id"]): item
            for item
            in self.experiments_config[
                "experiments"
            ]
        }

        invalid = 0
        assignment_mismatches = 0

        exposure_counter = Counter()
        variants_by_user = defaultdict(set)
        exposure_days_by_experiment = (
            defaultdict(set)
        )

        for (
            user_id,
            event_date,
            level_id,
            attempt_number,
            session_id,
            experiment_id,
            variant,
        ) in rows:
            experiment = experiments.get(
                experiment_id
            )

            if experiment is None:
                invalid += 1
                continue

            start_date = (
                self.start_date
                + timedelta(
                    days=int(
                        experiment[
                            "start_day"
                        ]
                    ) - 1
                )
            )

            end_date = (
                self.start_date
                + timedelta(
                    days=int(
                        experiment[
                            "end_day"
                        ]
                    ) - 1
                )
            )

            valid_variants = set(
                experiment["variants"]
            )

            structurally_valid = (
                start_date
                <= event_date
                <= end_date
                and level_id
                == int(
                    experiment[
                        "eligible_level"
                    ]
                )
                and attempt_number is None
                and session_id is not None
                and variant
                in valid_variants
            )

            if not structurally_valid:
                invalid += 1

            key = (
                experiment_id,
                user_id,
                event_date,
            )

            exposure_counter[key] += 1

            variants_by_user[
                (
                    experiment_id,
                    user_id,
                )
            ].add(variant)

            exposure_days_by_experiment[
                experiment_id
            ].add(
                (
                    user_id,
                    event_date,
                )
            )

            try:
                expected = (
                    self.experiment_resolver
                    .assignment_for_user(
                        user_id=user_id,
                        simulation_date=event_date,
                    )
                )

            except ValueError:
                expected = None

            if (
                expected is None
                or expected.experiment_id
                != experiment_id
                or expected.variant
                != variant
            ):
                assignment_mismatches += 1

        duplicate_user_days = sum(
            1
            for count
            in exposure_counter.values()
            if count != 1
        )

        unstable_users = sum(
            1
            for variants
            in variants_by_user.values()
            if len(variants) != 1
        )

        missing_exposure = 0
        extra_exposure = 0

        for experiment_id, experiment in (
            experiments.items()
        ):
            start_date = (
                self.start_date
                + timedelta(
                    days=int(
                        experiment[
                            "start_day"
                        ]
                    ) - 1
                )
            )

            end_date = (
                self.start_date
                + timedelta(
                    days=int(
                        experiment[
                            "end_day"
                        ]
                    ) - 1
                )
            )

            level_id = int(
                experiment[
                    "eligible_level"
                ]
            )

            gameplay_rows = self._rows(
                """
                SELECT DISTINCT
                    user_id,
                    event_date
                FROM raw_events
                WHERE
                    event_name = 'level_start'
                    AND level_id = %s
                    AND event_date
                        BETWEEN %s AND %s
                """,
                (
                    level_id,
                    start_date,
                    end_date,
                ),
            )

            gameplay_days = set(
                gameplay_rows
            )

            exposure_days = (
                exposure_days_by_experiment[
                    experiment_id
                ]
            )

            missing_exposure += len(
                gameplay_days
                - exposure_days
            )

            extra_exposure += len(
                exposure_days
                - gameplay_days
            )

        return (
            ValidationCheck(
                name="experiment_exposures_valid",
                passed=(
                    invalid == 0
                    and duplicate_user_days == 0
                ),
                details=(
                    f"exposures={len(rows)} "
                    f"invalid={invalid} "
                    f"duplicate_user_days="
                    f"{duplicate_user_days}"
                ),
            ),
            ValidationCheck(
                name="experiment_assignment_stable",
                passed=(
                    unstable_users == 0
                    and assignment_mismatches == 0
                ),
                details=(
                    f"unstable_users="
                    f"{unstable_users} "
                    f"resolver_mismatches="
                    f"{assignment_mismatches}"
                ),
            ),
            ValidationCheck(
                name="experiment_exposure_coverage",
                passed=(
                    missing_exposure == 0
                    and extra_exposure == 0
                ),
                details=(
                    f"missing_user_days="
                    f"{missing_exposure} "
                    f"extra_user_days="
                    f"{extra_exposure}"
                ),
            ),
        )

    def _rows(
        self,
        query: str,
        params=None,
    ) -> list[tuple]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                query,
                params,
            )

            return cursor.fetchall()

    def _scalar(
        self,
        query: str,
        params=None,
    ) -> int:
        with self.connection.cursor() as cursor:
            cursor.execute(
                query,
                params,
            )

            row = cursor.fetchone()

        if row is None:
            raise RuntimeError(
                "Scalar validation query "
                "returned no row"
            )

        return int(row[0])


def _date_range(
    start_date: date,
    end_date: date,
) -> list[date]:
    result = []
    current = start_date

    while current <= end_date:
        result.append(current)
        current += timedelta(days=1)

    return result
