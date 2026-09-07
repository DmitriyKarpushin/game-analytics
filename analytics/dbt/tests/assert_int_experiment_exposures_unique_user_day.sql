select
    experiment_id,
    user_id,
    exposure_date,
    count(*) as exposure_count
from {{ ref('int_experiment_exposures') }}
group by
    experiment_id,
    user_id,
    exposure_date
having count(*) <> 1
