with starts as (

    select
        event_id as attempt_id,
        event_at as attempt_started_at,
        user_id,
        session_id,
        level_id,
        attempt_number,
        app_version
    from {{ ref('stg_events') }}
    where event_name = 'level_start'

),

outcomes as (

    select
        event_id as outcome_event_id,
        event_at as attempt_result_at,
        user_id,
        session_id,
        level_id,
        attempt_number,
        event_name as outcome
    from {{ ref('stg_events') }}
    where event_name in (
        'level_complete',
        'level_fail'
    )

)

select
    s.attempt_id,
    o.outcome_event_id,

    s.user_id,
    s.session_id,
    s.level_id,
    s.attempt_number,

    s.attempt_started_at,
    o.attempt_result_at,
    s.attempt_started_at::date as attempt_date,

    extract(
        epoch from (
            o.attempt_result_at
            - s.attempt_started_at
        )
    )::integer as attempt_duration_sec,

    o.outcome,
    (
        o.outcome = 'level_complete'
    ) as is_success,

    s.app_version

from starts s

left join outcomes o
    on s.user_id = o.user_id
    and s.session_id = o.session_id
    and s.level_id = o.level_id
    and s.attempt_number = o.attempt_number
