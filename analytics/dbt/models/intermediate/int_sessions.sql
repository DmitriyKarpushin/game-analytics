with session_events as (

    select
        event_id,
        event_at,
        user_id,
        session_id,
        event_name,
        app_version
    from {{ ref('stg_events') }}
    where
        event_name in ('session_start', 'session_end')
        and session_id is not null

),

aggregated as (

    select
        session_id,
        user_id,

        min(event_at) filter (
            where event_name = 'session_start'
        ) as session_started_at,

        max(event_at) filter (
            where event_name = 'session_end'
        ) as session_ended_at,

        max(app_version) filter (
            where event_name = 'session_start'
        ) as app_version,

        count(*) filter (
            where event_name = 'session_start'
        ) as start_event_count,

        count(*) filter (
            where event_name = 'session_end'
        ) as end_event_count

    from session_events
    group by
        session_id,
        user_id

)

select
    session_id,
    user_id,
    session_started_at,
    session_ended_at,
    session_started_at::date as session_date,
    extract(
        epoch from (
            session_ended_at
            - session_started_at
        )
    )::integer as session_duration_sec,
    app_version,
    start_event_count,
    end_event_count
from aggregated
