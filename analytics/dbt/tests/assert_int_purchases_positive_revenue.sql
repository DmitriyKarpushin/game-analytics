select
    purchase_id
from {{ ref('int_purchases') }}
where
    revenue_usd is null
    or revenue_usd <= 0
