select
    user_id,
    activity_date,

    days_since_registration,

    sessions,
    session_duration_sec,

    attempts,
    level_completes,
    level_fails,

    purchases,
    purchase_revenue_usd,

    ad_impressions,
    ad_revenue_usd,

    total_revenue_usd

from {{ ref('fct_user_daily') }}

where
    days_since_registration < 0

    or sessions < 0
    or session_duration_sec < 0

    or attempts < 0
    or level_completes < 0
    or level_fails < 0

    or attempts <> level_completes + level_fails

    or purchases < 0
    or purchase_revenue_usd < 0

    or ad_impressions < 0
    or ad_revenue_usd < 0

    or total_revenue_usd < 0