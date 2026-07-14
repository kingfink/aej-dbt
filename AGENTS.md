# Project Instructions

## General SQL design

- Prefer the simplest SQL that clearly expresses the model's grain and purpose.
- Avoid passthrough CTEs such as `with x as (select * from {{ ref(...) }})`; reference the model directly.
- Use CTEs only for meaningful transformations, aggregation stages, or shared unioned data.
- Select only required columns; avoid `select *`.
- Use `union all`. If deduplication is required, perform it explicitly afterward with `select distinct`, grouping, or a window function.
- Put blank lines before and after `union all`.
- Avoid redundant filters, columns, date derivatives, and intermediate calculations.
- Prefer BigQuery-native functions and data types.
- Prefer `any_value` when any non-null representative value is acceptable.
- Prefer `min_by` and `max_by` over ordered `array_agg(...)[safe_offset(...)]`.
- Prefer a readable `case` or `if` for state logic; use `coalesce` for simple null defaults.
- Use native BigQuery `JSON` for sparse, event-specific details.
- Create macros for genuinely reusable or source-normalization logic, not one-off expressions.

## General naming

- Use `_ts` for modeled timestamp columns, never `_at` or `_timestamp`.
- Do not add a separate date column when the timestamp is sufficient; retain date-grained fields as dates when that is their actual grain.
- Use `source`, not `source_system`.
- Generate surrogate keys once at the earliest shared layer and reuse them downstream.
- Staging models may retain source-native names; intermediate and mart models should use canonical project names.
- Use `stg_`, `int_`, `dim_`, and `fct_` prefixes consistently.

## Joins

- Prefer `left join` to `inner join`.
- Use an explicit `where` only when unmatched rows should intentionally be excluded.
- Use `on`, never `using`.
- Alias every relation in a joined query with short, word-initial aliases.
- Qualify all columns in joined queries, including `select`, `on`, `where`, `group by`, `qualify`, and `order by`.
- Do not silently discard unmatched facts to make tests pass; retain them and let relationship or non-null tests expose coverage problems.

## Layers and domain boundaries

- Staging models should normalize source fields and expose only useful columns.
- Intermediate models should consolidate sources within a domain, normalize semantics, and generate shared keys.
- Marts should be narrow and analytics-friendly.
- Keep source-specific fields out of facts when they belong in a dimension.
- Keep mart models directly under `models/marts/` with shared documentation in `marts.yml`.
- Keep domain-specific naming, grains, and business rules scoped to their own sections rather than applying them across the whole project.
- Keep site content, email, web engagement, Search Console, and future domains logically separate unless a model intentionally combines them.
- Add or update a dedicated section in this file when a domain develops its own durable conventions.

## Email modeling

- Use canonical email identifiers:
  - `source_email_id`: provider-supplied message identifier.
  - `email_id`: warehouse message key.
  - `email_event_id`: individual provider event and recipient identifier.
  - `subscriber_id`: warehouse subscriber key.
- Put message attributes in `dim_email_messages`.
- Put subscriber attributes in `dim_email_subscribers`.
- Keep `fct_email_events` focused on keys, event type, event timestamp, and structured event details.
- Resend is the current and authoritative email provider.
- Only Resend contact state determines `is_subscribed`.
- A SendGrid-only address is not currently subscribed.
- SendGrid data may contribute historical subscription and engagement context.
- Normalize provider event types upstream through shared logic.

## Site content modeling

- Treat jobs and organizations as site-content entities rather than engagement events.
- Keep site-content models separate from email and future behavioral, web engagement, and search datasets unless a downstream model intentionally combines those domains.

## Documentation and validation

- Update model YAML whenever columns or semantics change.
- Test primary keys for non-nullness and uniqueness.
- Test foreign-key relationships.
- Add `accepted_values` tests for every categorical column so supported values are discoverable in model YAML without querying the warehouse.
- Format changed SQL, parse the project, and build affected models and their descendants.
- Run a full build for broad naming, staging, or contract changes.

## Markdown

- Do not hard-wrap Markdown prose or list items; keep each paragraph or bullet on a single physical line.
- Apply this convention to all new and edited Markdown files.

## Tooling

- Use connector tools first for GitHub, Netlify, and similar discovery, status, logs, metadata, and comments.
- Use local CLI or API fallbacks only when the connector cannot perform the action.
- Preserve unrelated worktree changes.
