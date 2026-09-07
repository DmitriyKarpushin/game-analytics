with impressions as (

    select
        event_id as ad_impression_id,
        event_at as impression_at,
        event_date as ad_date,

        user_id,
        session_id,
        app_version,

        event_properties ->> 'ad_format'
            as ad_format,

        (
            event_properties ->> 'revenue_usd'
        )::numeric(12, 4)
            as impression_revenue_usd,

        row_number() over (
            partition by
                user_id,
                session_id,
                event_properties ->> 'ad_format'
            order by
                event_at,
                event_id
        ) as pair_number

    from {{ ref('stg_events') }}

    where event_name = 'ad_impression'

),

revenues as (

    select
        event_id as ad_revenue_event_id,
        event_at as revenue_at,

        user_id,
        session_id,

        event_properties ->> 'ad_format'
            as ad_format,

        (
            event_properties ->> 'revenue_usd'
        )::numeric(12, 4)
            as revenue_usd,

        row_number() over (
            partition by
                user_id,
                session_id,
                event_properties ->> 'ad_format'
            order by
                event_at,
                event_id
        ) as pair_number

    from {{ ref('stg_events') }}

    where event_name = 'ad_revenue'

)

select
    i.ad_impression_id,
    r.ad_revenue_event_id,

    i.user_id,
    i.session_id,

    i.impression_at,
    r.revenue_at,
    i.ad_date,

    i.ad_format,
    i.impression_revenue_usd,
    r.revenue_usd,

    i.app_version

from impressions i

left join revenues r
    on i.user_id = r.user_id
    and i.session_id = r.session_id
    and i.ad_format = r.ad_format
    and i.pair_number = r.pair_number
