{% macro email_event_privacy_or_bot_reason(
    event_type_expression, user_agent_expression
) %}
    case
        when {{ event_type_expression }} not in ("opened", "clicked")
        then null
        when
            regexp_contains(
                lower(coalesce({{ user_agent_expression }}, "")),
                r"(googleimageproxy|gmailimageproxy|ggpht\.com|emailproxy|privacy|proxy)"
            )
        then "privacy_or_image_proxy"
        when
            regexp_contains(
                lower(coalesce({{ user_agent_expression }}, "")),
                r"(bot|crawl|spider|scanner|scan|preview|proofpoint|mimecast|barracuda|safelinks|urldefense|curl/|wget/|python-requests|go-http-client|headless|phantom|selenium)"
            )
        then "bot_or_security_scanner"
    end
{% endmacro %}
