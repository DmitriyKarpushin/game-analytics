select
    user_id,
    activity_date,
    count(*) as row_count

from {{ ref('fct_user_daily') }}

group by
    user_id,
    activity_date

having count(*) > 1