-- Core schema for Milestone 1

CREATE TABLE levels (
    level_id SMALLINT PRIMARY KEY,
    base_difficulty DOUBLE PRECISION NOT NULL,
    energy_cost INTEGER NOT NULL,
    reward_coins INTEGER NOT NULL,
    base_duration_sec INTEGER NOT NULL,

    CONSTRAINT chk_levels_level_id
        CHECK (level_id BETWEEN 1 AND 50),

    CONSTRAINT chk_levels_base_difficulty
        CHECK (base_difficulty > 0),

    CONSTRAINT chk_levels_energy_cost
        CHECK (energy_cost > 0),

    CONSTRAINT chk_levels_reward_coins
        CHECK (reward_coins >= 0),

    CONSTRAINT chk_levels_duration
        CHECK (base_duration_sec > 0)
);


CREATE TABLE raw_users (
    user_id UUID PRIMARY KEY,
    registration_ts TIMESTAMP NOT NULL,
    country VARCHAR(2) NOT NULL,
    platform VARCHAR(16) NOT NULL,
    device_tier VARCHAR(16) NOT NULL,
    acquisition_channel VARCHAR(32) NOT NULL,
    campaign_id VARCHAR(64),
    initial_app_version VARCHAR(16) NOT NULL,

    CONSTRAINT chk_raw_users_platform
        CHECK (platform IN ('android', 'ios')),

    CONSTRAINT chk_raw_users_device_tier
        CHECK (device_tier IN ('low', 'mid', 'high')),

    CONSTRAINT chk_raw_users_channel
        CHECK (
            acquisition_channel IN (
                'organic',
                'google_ads',
                'tiktok',
                'facebook',
                'referral'
            )
        )
);


CREATE TABLE simulation_runs (
    simulation_date DATE PRIMARY KEY,
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP,
    status VARCHAR(16) NOT NULL,
    seed BIGINT NOT NULL,
    users_created INTEGER NOT NULL DEFAULT 0,
    events_created INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT chk_simulation_runs_status
        CHECK (status IN ('running', 'success', 'failed')),

    CONSTRAINT chk_simulation_runs_users_created
        CHECK (users_created >= 0),

    CONSTRAINT chk_simulation_runs_events_created
        CHECK (events_created >= 0),

    CONSTRAINT chk_simulation_runs_timestamps
        CHECK (finished_at IS NULL OR finished_at >= started_at)
);


CREATE TABLE generator_user_state (
    user_id UUID PRIMARY KEY
        REFERENCES raw_users(user_id)
        ON DELETE CASCADE,

    skill DOUBLE PRECISION NOT NULL,
    engagement_propensity DOUBLE PRECISION NOT NULL,
    payer_propensity DOUBLE PRECISION NOT NULL,
    ad_tolerance DOUBLE PRECISION NOT NULL,
    base_churn_propensity DOUBLE PRECISION NOT NULL,

    current_level SMALLINT NOT NULL DEFAULT 1,

    coins INTEGER NOT NULL DEFAULT 0,
    gems INTEGER NOT NULL DEFAULT 0,

    last_active_date DATE,
    last_session_ts TIMESTAMP,

    total_sessions INTEGER NOT NULL DEFAULT 0,
    total_levels_completed INTEGER NOT NULL DEFAULT 0,
    total_levels_failed INTEGER NOT NULL DEFAULT 0,
    total_spend NUMERIC(12, 2) NOT NULL DEFAULT 0,

    frustration_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    is_churned BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT chk_state_skill
        CHECK (skill BETWEEN 0 AND 1),

    CONSTRAINT chk_state_engagement
        CHECK (engagement_propensity BETWEEN 0 AND 1),

    CONSTRAINT chk_state_payer
        CHECK (payer_propensity BETWEEN 0 AND 1),

    CONSTRAINT chk_state_ad_tolerance
        CHECK (ad_tolerance BETWEEN 0 AND 1),

    CONSTRAINT chk_state_churn
        CHECK (base_churn_propensity BETWEEN 0 AND 1),

    CONSTRAINT chk_state_current_level
        CHECK (current_level BETWEEN 1 AND 51),

    CONSTRAINT chk_state_coins
        CHECK (coins >= 0),

    CONSTRAINT chk_state_gems
        CHECK (gems >= 0),

    CONSTRAINT chk_state_total_sessions
        CHECK (total_sessions >= 0),

    CONSTRAINT chk_state_levels_completed
        CHECK (total_levels_completed >= 0),

    CONSTRAINT chk_state_levels_failed
        CHECK (total_levels_failed >= 0),

    CONSTRAINT chk_state_total_spend
        CHECK (total_spend >= 0),

    CONSTRAINT chk_state_frustration
        CHECK (frustration_score BETWEEN 0 AND 1)
);


CREATE TABLE raw_events (
    event_id UUID PRIMARY KEY,
    event_ts TIMESTAMP NOT NULL,
    event_date DATE NOT NULL,

    user_id UUID NOT NULL
        REFERENCES raw_users(user_id),

    session_id UUID,
    event_name VARCHAR(64) NOT NULL,

    level_id SMALLINT
        REFERENCES levels(level_id),

    attempt_number INTEGER,
    app_version VARCHAR(16) NOT NULL,
    event_properties JSONB NOT NULL DEFAULT '{}'::JSONB,

    CONSTRAINT chk_raw_events_attempt_number
        CHECK (attempt_number IS NULL OR attempt_number >= 1),

    CONSTRAINT chk_raw_events_date
        CHECK (event_date = event_ts::DATE)
);


CREATE INDEX idx_raw_users_registration_ts
    ON raw_users (registration_ts);

CREATE INDEX idx_raw_events_event_date
    ON raw_events (event_date);

CREATE INDEX idx_raw_events_user_ts
    ON raw_events (user_id, event_ts);

CREATE INDEX idx_raw_events_session_ts
    ON raw_events (session_id, event_ts)
    WHERE session_id IS NOT NULL;

CREATE INDEX idx_raw_events_level
    ON raw_events (level_id)
    WHERE level_id IS NOT NULL;