with sessions as (

    select
        user_id,
        session_date as activity_date,
        count(*) as sessions,
        sum(session_duration_sec) as session_duration_sec

    from {{ ref('int_sessions') }}

    group by
        user_id,
        session_date

),

gameplay as (

    select
        user_id,
        attempt_date as activity_date,

        count(*) as attempts,

        count(*) filter (
            where is_success
        ) as level_completes,

        count(*) filter (
            where not is_success
        ) as level_fails,

        count(distinct level_id) as levels_attempted,

        max(level_id) as max_level_started,

        max(level_id) filter (
            where is_success
        ) as max_level_completed

    from {{ ref('int_gameplay_attempts') }}

    group by
        user_id,
        attempt_date

),

purchases as (

    select
        user_id,
        purchase_date as activity_date,
        count(*) as purchases,
        sum(revenue_usd) as purchase_revenue_usd

    from {{ ref('int_purchases') }}

    group by
        user_id,
        purchase_date

),

ads as (

    select
        user_id,
        ad_date as activity_date,
        count(*) as ad_impressions,
        sum(revenue_usd) as ad_revenue_usd

    from {{ ref('int_ads') }}

    group by
        user_id,
        ad_date

),

user_days as (

    select
        user_id,
        activity_date
    from sessions

    union

    select
        user_id,
        activity_date
    from gameplay

    union

    select
        user_id,
        activity_date
    from purchases

    union

    select
        user_id,
        activity_date
    from ads

)

select
    ud.user_id,
    ud.activity_date,

    u.registration_date,
    ud.activity_date - u.registration_date as days_since_registration,

    u.country,
    u.platform,
    u.device_tier,
    u.acquisition_channel,
    u.campaign_id,
    u.initial_app_version,

    coalesce(s.sessions, 0) as sessions,
    coalesce(s.session_duration_sec, 0) as session_duration_sec,

    coalesce(g.attempts, 0) as attempts,
    coalesce(g.level_completes, 0) as level_completes,
    coalesce(g.level_fails, 0) as level_fails,
    coalesce(g.levels_attempted, 0) as levels_attempted,

    g.max_level_started,
    g.max_level_completed,

    coalesce(p.purchases, 0) as purchases,
    coalesce(p.purchase_revenue_usd, 0) as purchase_revenue_usd,

    coalesce(a.ad_impressions, 0) as ad_impressions,
    coalesce(a.ad_revenue_usd, 0) as ad_revenue_usd,

    coalesce(p.purchase_revenue_usd, 0)
        + coalesce(a.ad_revenue_usd, 0)
        as total_revenue_usd,

    coalesce(p.purchases, 0) > 0 as is_payer

from user_days ud

join {{ ref('stg_users') }} u
    on ud.user_id = u.user_id

left join sessions s
    on ud.user_id = s.user_id
    and ud.activity_date = s.activity_date

left join gameplay g
    on ud.user_id = g.user_id
    and ud.activity_date = g.activity_date

left join purchases p
    on ud.user_id = p.user_id
    and ud.activity_date = p.activity_date

left join ads a
    on ud.user_id = a.user_id
    and ud.activity_date = a.activity_date