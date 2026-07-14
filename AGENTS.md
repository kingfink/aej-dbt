# Project Instructions

## General SQL design

- Prefer the simplest SQL that clearly expresses the model's grain and purpose.
- Avoid passthrough CTEs such as `with x as (select * from {{ ref(...) }})`; reference the model directly.
- Use CTEs only for meaningful transformations, aggregation stages, or shared unioned data.
- Select only required columns; avoid `select *`.
- Use `union all`. If deduplication is required, perform it explicitly afterward with `select distinct`, grouping, or a window function.
- Put blank lines before and after `union all`.
- Avoid redundant filters, columns, date derivatives, and intermediate calculations.
- Add columns only for concrete current requirements; do not add speculative fields because they may be useful downstream.
- Keep changes local to the model that needs them and preserve existing upstream models when their established contract already supports the new work.
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
- Give each mart a single `_id` surrogate primary key; retain natural or composite identifiers as business keys.
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
- The grain of `dim_email_messages` is one row per `source` and `source_email_id`.
- The grain of `dim_email_subscribers` is one row per normalized email address.
- The grain of `fct_email_events` is one row per provider event and recipient.
- Put message attributes in `dim_email_messages`.
- Put subscriber attributes in `dim_email_subscribers`.
- Keep `fct_email_events` focused on keys, event type, event timestamp, and structured event details.
- Put sparse event attributes such as link URL, IP address, user agent, backfill status, and privacy or bot classification in the native JSON `email_event_details` column.
- Resend is the current and authoritative email provider.
- Only Resend contact state determines `is_subscribed`.
- A SendGrid-only address is not currently subscribed.
- SendGrid subscription state is authoritative for historical dates through the Resend contact-import cutover. The migration exported SendGrid contacts and imported them into Resend with both subscribed and unsubscribed status.
- Derive the cutover from the Resend contacts backfill. Use SendGrid state through the backfill date and Resend state beginning the following UTC date so same-day subscription is preserved without inventing a precise historical unsubscribe time.
- SendGrid data may also contribute historical engagement context.
- Build `int_email_subscribers` from the normalized lifecycle in `int_email_subscription_events` rather than independently reconciling provider contact states.
- For daily subscription state, mark a subscriber as subscribed when they entered the date subscribed or had a subscribe event during the date; a later unsubscribe on the same date does not erase that day's subscription. Do not add source, webhook, or backfill precedence without a concrete requirement.
- Normalize provider event types upstream through shared logic.
- Keep source-specific event categories in staging and expose the consolidated category domain in intermediate and mart YAML through `accepted_values` tests.
- Do not expose `signup_page_url` until ongoing Resend signup attribution is captured reliably; follow-up work is tracked in `kingfink/analytics-engineering-jobs#1437`.

## Site content modeling

- Treat jobs and organizations as site-content entities rather than engagement events.
- Keep site-content models separate from email and future behavioral, web engagement, and search datasets unless a downstream model intentionally combines those domains.

## Documentation and validation

- Update model YAML whenever columns or semantics change.
- Test primary keys for non-nullness and uniqueness.
- Test foreign-key relationships.
- Add `accepted_values` tests for every categorical column so supported values are discoverable in model YAML without querying the warehouse.
- Avoid tests that only restate static configuration; tests should validate behavior or meaningful invariants.
- Format changed SQL, parse the project, and build affected models and their descendants.
- Run a full build for broad naming, staging, or contract changes.

## Markdown

- Do not hard-wrap Markdown prose or list items; keep each paragraph or bullet on a single physical line.
- Apply this convention to all new and edited Markdown files.

## YAML

- Do not hard-wrap YAML descriptions; keep each paragraph on a single physical line.
- Use `|` rather than `>-` for block-style descriptions.

## Tooling

- Use connector tools first for GitHub, Netlify, and similar discovery, status, logs, metadata, and comments.
- Use local CLI or API fallbacks only when the connector cannot perform the action.
- Preserve unrelated worktree changes.
