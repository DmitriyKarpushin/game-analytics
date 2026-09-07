select
    attempt_id
from {{ ref('int_gameplay_attempts') }}
where
    outcome_event_id is null
    or attempt_result_at is null
    or attempt_result_at <= attempt_started_at
    or attempt_duration_sec <= 0
