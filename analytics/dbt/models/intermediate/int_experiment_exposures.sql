select
    event_id as exposure_id,
    event_at as exposed_at,
    event_date as exposure_date,

    user_id,
    session_id,
    level_id,

    event_properties ->> 'experiment_id'
        as experiment_id,

    event_properties ->> 'variant'
        as variant,

    app_version

from {{ ref('stg_events') }}

where event_name = 'experiment_exposure'
