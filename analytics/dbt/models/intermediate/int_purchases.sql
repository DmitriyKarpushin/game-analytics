select
    event_id as purchase_id,
    event_at as purchased_at,
    event_date as purchase_date,

    user_id,
    session_id,
    level_id,
    app_version,

    event_properties ->> 'sku'
        as sku,

    event_properties ->> 'currency'
        as currency,

    (
        event_properties ->> 'price_usd'
    )::numeric(12, 2)
        as revenue_usd

from {{ ref('stg_events') }}

where event_name = 'purchase'
