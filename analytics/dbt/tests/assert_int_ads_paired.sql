select
    ad_impression_id
from {{ ref('int_ads') }}
where
    ad_revenue_event_id is null
    or revenue_at is null
    or revenue_at < impression_at
    or revenue_usd is null
    or revenue_usd <= 0
    or impression_revenue_usd
        is distinct from revenue_usd
