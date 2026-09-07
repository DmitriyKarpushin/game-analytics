select
    level_id,
    base_difficulty,
    energy_cost,
    reward_coins,
    base_duration_sec
from {{ source('raw', 'levels') }}
