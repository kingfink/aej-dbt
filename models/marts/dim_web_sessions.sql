select
    s.session_id,
    s.source_session_id,
    s.source,
    s.visitor_id,
    s.session_started_ts,
    s.session_page_path,
    s.session_referring_domain,
    s.session_utm_source,
    s.session_utm_medium,
    s.session_utm_campaign,
    s.browser,
    s.device_type,
    s.country_code,
    {{
        get_channel(
            source="s.session_utm_source",
            medium="s.session_utm_medium",
            campaign="lower(s.session_utm_campaign)",
            referring_domain="s.session_referring_domain",
            paid_source_type="coalesce(us.type_if_paid, usr.type_if_paid)",
            organic_source_type="coalesce(us.type_if_organic, usr.type_if_organic)",
            paid_medium_type="um.type_if_paid",
            organic_medium_type="um.type_if_organic",
            paid_referring_domain_type="coalesce(rd.type_if_paid, rdr.type_if_paid)",
            organic_referring_domain_type="coalesce(rd.type_if_organic, rdr.type_if_organic)",
        )
    }}
    as channel
from {{ ref("int_web_sessions") }} as s
left join
    {{ ref("channel_definitions") }} as us
    on us.kind = "source"
    and s.session_utm_source = us.domain
left join
    {{ ref("channel_definitions") }} as usr
    on usr.kind = "source"
    and net.reg_domain(s.session_utm_source) = usr.domain
left join
    {{ ref("channel_definitions") }} as um
    on um.kind = "medium"
    and s.session_utm_medium = um.domain
left join
    {{ ref("channel_definitions") }} as rd
    on rd.kind = "source"
    and s.session_referring_domain = rd.domain
left join
    {{ ref("channel_definitions") }} as rdr
    on rdr.kind = "source"
    and net.reg_domain(s.session_referring_domain) = rdr.domain
