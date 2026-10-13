select
    s.session_id,
    s.session_started_ts,
    s.page_view_count,
    s.distinct_page_count,
    s.job_page_view_count,
    s.apply_click_count,
    s.job_page_view_count > 0
    and (s.distinct_page_count >= 2 or s.apply_click_count > 0) as is_engaged_job_seeker
from {{ ref("int_web_sessions") }} as s
