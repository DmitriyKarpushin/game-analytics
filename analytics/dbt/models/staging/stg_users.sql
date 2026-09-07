select
    user_id,
    registration_ts as registered_at,
    registration_ts::date as registration_date,
    country,
    platform,
    device_tier,
    acquisition_channel,
    campaign_id,
    initial_app_version
from {{ source('raw', 'raw_users') }}
