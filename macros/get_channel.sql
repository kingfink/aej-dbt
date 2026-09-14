{% macro get_channel(
    source,
    medium,
    campaign,
    referring_domain,
    paid_source_type,
    organic_source_type,
    paid_medium_type,
    organic_medium_type,
    paid_referring_domain_type,
    organic_referring_domain_type
) %}
    {#- Port of PostHog's default channel type, which builds on GA4's default channel
    groups: posthog/hogql/database/schema/channel_type.py at PostHog commit 3ed641c.
    Pass lowercased UTM values plus the channel_definitions types looked up for the
    source, medium, and referring domain. The PostHog export carries no click
    identifiers, so the gclid, fbclid, and gad_source branches are omitted. -#}
    lower(
        replace(
            case
                when regexp_contains({{ campaign }}, r"cross-network")
                then "Cross Network"
                when
                    {{ medium }} in ("cpc", "cpm", "cpv", "cpa", "ppc", "retargeting")
                    or starts_with({{ medium }}, "paid")
                then
                    coalesce(
                        {{ paid_source_type }},
                        if(
                            regexp_contains(
                                {{ campaign }}, r"^(.*(([^a-df-z]|^)shop|shopping).*)$"
                            ),
                            "Paid Shopping",
                            null
                        ),
                        {{ paid_medium_type }},
                        {{ paid_referring_domain_type }},
                        if(
                            regexp_contains({{ campaign }}, r"^(.*video.*)$"),
                            "Paid Video",
                            "Paid Unknown"
                        )
                    )
                when
                    {{ referring_domain }} = "$direct"
                    and {{ medium }} is null
                    and (
                        {{ source }} is null
                        or {{ source }} in ("(direct)", "direct", "$direct")
                    )
                then "Direct"
                else
                    coalesce(
                        {{ organic_source_type }},
                        if(
                            regexp_contains(
                                {{ campaign }}, r"^(.*(([^a-df-z]|^)shop|shopping).*)$"
                            ),
                            "Organic Shopping",
                            null
                        ),
                        {{ organic_medium_type }},
                        -- Local rule from GA4, which PostHog's definitions omit.
                        if({{ medium }} = "organic", "Organic Search", null),
                        {{ organic_referring_domain_type }},
                        case
                            when regexp_contains({{ campaign }}, r"^(.*video.*)$")
                            then "Organic Video"
                            when regexp_contains({{ medium }}, r"push$")
                            then "Push"
                            when {{ referring_domain }} = "$direct"
                            then "Direct"
                            -- Local rule: a self-referral is the session window
                            -- expiring mid-visit, not a referral.
                            when
                                net.reg_domain({{ referring_domain }})
                                = "analyticsengineeringjobs.com"
                            then "Internal"
                            when {{ referring_domain }} is not null
                            then "Referral"
                            else "Unknown"
                        end
                    )
            end,
            " ",
            "_"
        )
    )
{% endmacro %}
