# Raw Data Contract

## Status

Engineering version: `v1.0`

The generator and raw data layer are frozen after the `engineering-v1.0`
release.

During the analytical phase, PostgreSQL raw tables and this contract are the
analyst-facing source of truth.

Generator implementation, latent user parameters, simulation effects, and
engineering configuration should be treated as upstream implementation
details rather than analytical inputs.

Changes after the freeze are limited to genuine engineering bug fixes or
operational fixes. Changes that alter historical business behavior require a
new engineering version.

## Simulation calendar

Simulation start date:

`2026-01-01`

The production pipeline generates complete virtual days only.

The normal scheduler target is:

`current UTC date - 1 day`

The pipeline is stateful. Missing dates after the latest successful date are
generated sequentially. Historical gaps before a later successful date are
treated as an error and are not silently regenerated.

Each virtual day is committed independently.

## Tables

### `levels`

Static level dimension.

Primary key:

`level_id`

Levels are numbered `1..50`.

Fields:

- `level_id`
- `base_difficulty`
- `energy_cost`
- `reward_coins`
- `base_duration_sec`

### `raw_users`

One row per registered user.

Primary key:

`user_id`

Fields:

- `user_id`
- `registration_ts`
- `country`
- `platform`
- `device_tier`
- `acquisition_channel`
- `campaign_id`
- `initial_app_version`

Contract:

- `registration_ts` is the user's simulated registration timestamp.
- `campaign_id` is populated only when the user's acquisition channel has an
  active campaign on the registration date.
- `initial_app_version` is the application version active on the registration
  date.
- each user must have exactly one corresponding
  `generator_user_state` row.

### `generator_user_state`

Mutable operational state used by the generator.

Primary key:

`user_id`

This is an engineering state table, not an immutable event fact table.

It contains latent and accumulated state required to continue the simulation,
including:

- skill
- engagement propensity
- payer propensity
- ad tolerance
- churn propensity
- progression
- session activity
- spend
- frustration
- churn state

`current_level = 51` means the user completed all 50 configured levels.

Analytical models should normally be derived from raw events and raw users
rather than treating latent generator parameters as observed product data.

### `raw_events`

Immutable event stream.

Primary key:

`event_id`

Fields:

- `event_id`
- `event_ts`
- `event_date`
- `user_id`
- `session_id`
- `event_name`
- `level_id`
- `attempt_number`
- `app_version`
- `event_properties`

Contract:

- `event_date = event_ts::date`
- every `user_id` references a real `raw_users` row
- non-null `level_id` references `levels`
- session-bound events reference a real simulated session
- `app_version` is the version active on the event date

### `simulation_runs`

Operational metadata for virtual-day generation.

Primary key:

`simulation_date`

Fields:

- `simulation_date`
- `started_at`
- `finished_at`
- `status`
- `seed`
- `users_created`
- `events_created`

Allowed statuses:

- `running`
- `success`
- `failed`

For a healthy completed history:

- dates are continuous from the simulation start date
- every completed date has `status = success`
- `users_created` equals actual registrations on that date
- `events_created` equals actual raw events on that date

A failed day may be retried. Partial raw data from a failed generation
transaction must not remain committed.

## Event contract

### `session_start`

Marks the beginning of a simulated session.

Expected:

- `session_id`: non-null
- `level_id`: null
- `attempt_number`: null

### `session_end`

Marks the end of the same simulated session.

Expected:

- `session_id`: non-null
- `level_id`: null
- `attempt_number`: null

Every session must have exactly one `session_start` and exactly one
`session_end`, belonging to the same user.

### `level_start`

Marks the beginning of one gameplay attempt.

Expected:

- `session_id`: non-null
- `level_id`: `1..50`
- `attempt_number`: positive integer

### `level_complete`

Successful result of a gameplay attempt.

Expected:

- same user/session/level/attempt context as its attempt
- `level_id`: `1..50`
- `attempt_number`: positive integer

### `level_fail`

Failed result of a gameplay attempt.

Expected:

- same user/session/level/attempt context as its attempt
- `level_id`: `1..50`
- `attempt_number`: positive integer

### `purchase`

In-app purchase event.

Expected:

- `session_id`: non-null
- `level_id`: current valid gameplay level when available, otherwise null

`event_properties`:

- `sku`
- `price_usd`
- `currency`

Currency is currently `USD`.

### `ad_impression`

Ad impression inside a real session.

Expected:

- `session_id`: non-null

`event_properties` contains:

- `ad_format`
- `revenue_usd`

Current ad formats:

- `rewarded`
- `interstitial`

### `ad_revenue`

Revenue event paired with an ad impression.

Expected:

- same user/session/ad-format context as the corresponding impression

`event_properties` contains:

- `ad_format`
- `revenue_usd`

### `experiment_exposure`

Records actual exposure to an A/B experiment.

Expected:

- `session_id`: non-null
- `level_id`: experiment eligibility level
- `attempt_number`: null

`event_properties`:

- `experiment_id`
- `variant`

For `level17_balance_v1`:

- eligibility is actual Level 17 interaction during the experiment window
- assignment is deterministic and stable for a user
- variants are `control` and `treatment`
- a user cannot belong to multiple variants
- at most one exposure is emitted per user per virtual day
- users interacting with Level 17 on an eligible day must have an exposure

The exposure event is the analytical assignment source. Engineering treatment
implementation is intentionally outside the analyst-facing contract.

## Application versions

Version schedules are defined in:

`config/app_versions.yaml`

Contract:

- a new user's `initial_app_version` matches the version active on registration
- every event's `app_version` matches the version active on its event date

The shared `AppVersionResolver` defines calendar interpretation.

## Acquisition campaigns

Campaign schedules are defined in:

`config/campaigns.yaml`

Contract:

- campaign attribution occurs at registration
- `campaign_id` must match both registration date and acquisition channel
- users outside an active campaign/channel combination have
  `campaign_id = NULL`

The shared `CampaignResolver` defines calendar interpretation.

## Experiments

Experiment schedules and assignment configuration are defined upstream in:

`config/experiments.yaml`

For analytical work, use `experiment_exposure` events rather than reading
generator-side treatment implementation.

The shared deterministic assignment guarantees that the same user receives the
same variant throughout an experiment.

## Operational validation

The canonical raw-layer health check is:

`python -m src.cli.validate_raw`

A healthy dataset returns exit code `0`.

Any failed critical invariant returns a non-zero exit code.

Current validator checks:

1. continuous simulation history
2. successful run statuses
3. `raw_users` / `generator_user_state` one-to-one integrity
4. simulation run counts against actual raw rows
5. event user references
6. session integrity
7. level references
8. app-version schedule
9. campaign attribution
10. experiment exposure structure
11. stable experiment assignment
12. experiment exposure coverage

Business metrics such as retention, monetization, funnel performance,
experiment significance, and churn performance are intentionally not part of
engineering validation. They belong to the analytical layer.

## Production orchestration

Canonical daily command:

`python -m src.cli.run_pending`

Behavior:

- acquires a PostgreSQL advisory lock
- determines the latest successful virtual date
- rejects historical gaps
- generates missing tail dates sequentially
- persists `running` state before generation
- commits each successful day independently
- rolls back partial raw data on failure
- persists `failed` status for a failed day
- supports retry
- is idempotent when already current

Production execution is followed by:

`python -m src.cli.validate_raw`

The deployed systemd unit and timer are stored in:

`deploy/systemd/`

## Engineering freeze boundary

After tag `engineering-v1.0`:

Frozen:

- synthetic business behavior
- acquisition behavior
- gameplay behavior
- monetization behavior
- app-version effects
- campaign behavior
- experiment assignment and treatment behavior
- raw event semantics
- raw table contract

Allowed later:

- analytical SQL/dbt models
- BI dashboards
- A/B statistical analysis
- churn feature engineering and ML
- documentation
- infrastructure fixes that do not change historical business behavior
- genuine generator/raw bugs, with explicit versioning if data semantics change
