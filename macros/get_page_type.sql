{% macro get_page_type(page_path) %}
    case
        when {{ page_path }} = "/"
        then "home"
        when {{ page_path }} = "/jobs/"
        then "job_index"
        when {{ page_path }} like "/jobs/%"
        then "job"
        when {{ page_path }} = "/organizations/"
        then "organization_index"
        when {{ page_path }} like "/organizations/%"
        then "organization"
        when {{ page_path }} like "/landing-pages/%"
        then "landing_page"
        when {{ page_path }} like "/tags/%"
        then "tag"
        when {{ page_path }} = "/subscribe/"
        then "subscribe"
        else "other"
    end
{% endmacro %}
