{% snapshot snp_organizations %}

    select file_path, frontmatter, modified_at
    from {{ source("analytics_engineering_jobs", "organizations") }}

{% endsnapshot %}
