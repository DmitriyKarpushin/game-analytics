select
    session_id
from {{ ref('int_sessions') }}
where
    start_event_count <> 1
    or end_event_count <> 1
    or session_started_at is null
    or session_ended_at is null
    or session_ended_at <= session_started_at
