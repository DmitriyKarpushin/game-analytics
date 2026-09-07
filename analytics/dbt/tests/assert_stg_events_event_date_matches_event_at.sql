select
    event_id,
    event_at,
    event_date
from {{ ref('stg_events') }}
where event_date <> event_at::date
