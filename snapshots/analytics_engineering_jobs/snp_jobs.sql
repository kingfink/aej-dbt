{% snapshot snp_jobs %}

    select file_path, frontmatter, modified_at
    from {{ source("analytics_engineering_jobs", "jobs") }}

{% endsnapshot %}
