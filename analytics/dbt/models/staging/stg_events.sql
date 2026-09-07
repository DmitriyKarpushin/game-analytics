select
    event_id,
    event_ts as event_at,
    event_date,
    user_id,
    session_id,
    event_name,
    level_id,
    attempt_number,
    app_version,
    event_properties
from {{ source('raw', 'raw_events') }}
