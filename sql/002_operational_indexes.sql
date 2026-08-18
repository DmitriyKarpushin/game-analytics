CREATE INDEX IF NOT EXISTS idx_raw_events_user_gameplay_ts
ON raw_events (
    user_id,
    event_ts DESC,
    event_id DESC
)
INCLUDE (event_name)
WHERE event_name IN (
    'level_complete',
    'level_fail'
);

CREATE INDEX IF NOT EXISTS idx_raw_events_user_level_fail_attempt
ON raw_events (
    user_id,
    level_id,
    attempt_number DESC
)
WHERE event_name = 'level_fail';

ANALYZE raw_events;
