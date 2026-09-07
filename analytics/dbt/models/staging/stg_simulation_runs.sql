select
    simulation_date,
    started_at,
    finished_at,
    status,
    seed,
    users_created,
    events_created
from {{ source('raw', 'simulation_runs') }}
