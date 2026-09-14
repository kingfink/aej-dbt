{% macro normalize_page_path(url_or_path) %}
    {#- Accepts a full URL or a bare path. Drops scheme, host, query string, and
    fragment, then enforces exactly one trailing slash to match the site's URLs. -#}
    concat(
        rtrim(regexp_extract({{ url_or_path }}, r"^(?:https?://[^/]+)?([^?#]*)"), "/"),
        "/"
    )
{% endmacro %}
