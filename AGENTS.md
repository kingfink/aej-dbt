# Project Instructions

## General SQL design

- Prefer the simplest SQL that clearly expresses the model's grain and purpose.
- Avoid passthrough CTEs such as `with x as (select * from {{ ref(...) }})`; reference the model directly.
- Use CTEs only for meaningful transformations, aggregation stages, or shared unioned data.
- Select only required columns; avoid `select *`.
- Use `union all`. If deduplication is required, perform it explicitly afterward with `select distinct`, grouping, or a window function.
- Reference columns by ordinal position in statement-level `group by` and `order by`. Positions do not work inside a window function's `order by`, where a bare number is a constant rather than a column reference, so name the column there.
- Put blank lines before and after `union all`.
- Avoid redundant filters, columns, date derivatives, and intermediate calculations.
- Add columns only for concrete current requirements; do not add speculative fields because they may be useful downstream.
- Keep changes local to the model that needs them and preserve existing upstream models when their established contract already supports the new work.
- Prefer BigQuery-native functions and data types.
- Prefer `any_value` when any non-null representative value is acceptable.
- Prefer `min_by` and `max_by` over ordered `array_agg(...)[safe_offset(...)]`.
- Prefer a readable `case` or `if` for state logic; use `coalesce` for simple null defaults.
- Prefer BigQuery `logical_or` and `logical_and` for boolean aggregation rather than expressing them as conditional counts.
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
- Prefix new count measures with `n_` and summed measures with `sum_`, such as `n_impressions` and `sum_position`. Existing columns such as `message_count` keep their names until their contracts change for another reason.

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

## Model governance and public interfaces

- Keep source extraction and raw loading out of this repository. Upstream ingestion belongs in source-specific or shared ingestion systems such as `aej-dlt`; this repository owns transformation plus the currently coupled Parquet publication step.
- Assign models to domain groups. Provider or source staging models and intermediate models should be private within their group; marts should be public.
- Prefer `dbt_project.yml` directory hierarchy for shared access, group, materialization, and contract configuration. Keep per-model group configuration only where mixed-domain models share a directory.
- Enforce contracts on marts and declare a `data_type` for every mart column. Retain uniqueness as a data test rather than a BigQuery contract constraint.
- Treat public Parquet files as public interfaces. The backing mart contract defines the file schema when the publisher selects every model column; update the contract, exposure, export configuration, and README together when the interface changes.
- Declare exposures only for real consumers. Verify Steep exposures against the live workspace and the `aej-steep` repository, and include the module's base relation plus models referenced by join paths, dimensions, or cohorts. Do not invent consumer URLs.
- Use real ingestion timestamps for source freshness and tune thresholds to observed delivery cadence. Do not use event occurrence time as load time.
- Use focused dbt unit tests for nontrivial state or lifecycle logic and reusable generic tests for invariants that apply across models.

## Email modeling

- Use canonical email identifiers:
  - `source_email_id`: provider-supplied message identifier.
  - `email_id`: warehouse message key.
  - `email_event_id`: individual provider event and recipient identifier.
  - `email_campaign_id`: warehouse campaign key.
  - `subscriber_id`: warehouse subscriber key.
- The grain of `dim_email_messages` is one row per `source` and `source_email_id`.
- The grain of `dim_email_campaigns` is one row per `source`, subject, and campaign date. A message is one recipient send, so the campaign is the entity that corresponds to a newsletter issue.
- Anchor the campaign date to the earliest sent event on a message, falling back to its earliest event of any type when the provider never delivered a sent event.
- Transactional and test sends are campaigns too. Separate test sends with `is_test` rather than filtering them out upstream.
- The grain of `dim_email_subscribers` is one row per normalized email address.
- The grain of `fct_email_events` is one row per provider event and recipient.
- Put message attributes in `dim_email_messages`.
- Put campaign attributes in `dim_email_campaigns`.
- Put subscriber attributes in `dim_email_subscribers`.
- Keep `fct_email_events` focused on keys, event type, event timestamp, the clicked link destination, and structured event details.
- Promote a sparse event attribute to its own column when it becomes a dimension of analysis rather than a detail to look up. The clicked link is promoted as `link_url`, `link_type`, and `job_id` because link performance is a question the marts answer directly; a second fact over the same grain is not warranted, since a click carries exactly one link.
- Put remaining sparse event attributes such as IP address, user agent, backfill status, and privacy or bot classification in the native JSON `email_event_details` column.
- Normalize and classify link destinations in `int_email_message_events` so marts stay flat and every consumer sees one definition. Strip the query string and fragment so campaign parameters and per-contact unsubscribe tokens collapse to one value per destination.
- Gate link fields to click events. Providers occasionally attach a URL to other event types, and those are not click destinations.
- Resolve links to `dim_jobs` only under the current job URL scheme. Legacy SendGrid-era job links used a flat single-segment path and stay unresolved rather than being guessed at.
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
- Do not expose `signup_page_url` until ongoing Resend signup attribution is captured reliably; follow-up work is tracked in `kingfink/analytics-engineering-jobs#1839`.

## Site content modeling

- Treat jobs and organizations as site-content entities rather than engagement events.
- Keep site-content models separate from email and future behavioral, web engagement, and search datasets unless a downstream model intentionally combines those domains.

## Web engagement modeling

- Netlify Forms is the authoritative source for current form submissions and submitted email addresses; Webflow form submissions are legacy history.
- PostHog is the behavioral source for page views, outbound apply clicks, and the apply modal lifecycle, but it does not contain the submitted email address.
- The grain of `fct_web_events` is one row per behavioral event. Keep behavioral marts at event grain rather than pre-aggregating, so distinct visitor counts stay correct over any date range.
- Dedupe the PostHog batch export on the provider event identifier. It delivers at least once, and duplicates inflate counts by several percent.
- Restrict behavioral models to production hosts. Local development, deploy preview, and preview worker traffic otherwise counts as real visits.
- `visitor_id` is a device identifier, not a person. Person profiles are disabled, so distinct visitor counts are a floor and repeat visitors across devices are undercounted.
- Filter behavioral marts to the event types a question needs, and keep every captured event type in staging so widening a mart stays a one-line change.
- Treat PostHog as consent-gated and therefore a floor on traffic, not total traffic. Do not blend GA4 into behavioral marts to extend history; GA4 captures a materially smaller and differently biased share of the same traffic, so a union reads as a traffic change at the seam.
- Treat PostHog distinct and session identifiers on form submissions as nullable, consent-gated join keys. Do not require them or use them to discard submissions from visitors without PostHog consent.
- Keep one row per source form submission in `fct_form_submissions`, with source-native submission IDs retained as business keys and one shared surrogate key generated in staging.
- Link form submissions to known subscribers, jobs, and organizations with left joins. Retain unmatched submissions rather than discarding identity or context.
- Keep unnecessary sensitive or operational fields such as IP addresses, user agents, and uploaded-file URLs out of marts.
- The grain of `dim_web_sessions` is one row per PostHog session. PostHog stamps session entry attribution on every event and it is constant within a session, so the dimension aggregates over the session identifier without an entry event selection rule.
- Resolve `web_session_id` onto `fct_web_events` and `fct_form_submissions` by left joining `dim_web_sessions` on the natural session identifier. A null `web_session_id` means no session context, either a submission from before `posthog_session_id` capture was complete in 2026-08 or a visitor without PostHog consent, and it is never direct traffic.
- Derive `channel` from UTM parameters before the referring domain, because email clients strip the referrer and newsletter traffic otherwise reads as direct. Classify on the referring domain rather than `$session_entry_search_engine`, which PostHog sets to `google` for both Gemini and Gmail.
- Keep `internal` distinct from `direct`. A session whose entry referrer is the site's own domain comes from the 30 minute session window expiring mid-visit, not from a direct arrival.

## Search performance modeling

- Google Search Console is the source for organic search demand. The `sc-domain:analyticsengineeringjobs.com` domain property covers every host on the domain, so job URLs are in scope by construction.
- Measure source freshness on `ExportLog.publish_time`, the only real delivery timestamp in the export. `data_date` is when searches happened, not when they landed.
- Tune freshness to Google's publish lag. Dates land two to three days after they close, and the longest observed gap between publishes is 80 hours.
- Aggregate the export to its own grain in staging rather than passing rows through. Google splits anonymized-query volume into several rows per key, so the measures are summed and a pass-through model has no unique key.
- Keep `n_impressions`, `n_clicks`, and `sum_position` (or `sum_top_position`) as the only additive measures. Derive click-through rate and average position from summed numerators and denominators, never by averaging row-level rates. The export's positions are zero based, so average position is `sum_position / n_impressions + 1`.
- Normalize URLs to a canonical site path in staging with the shared `normalize_page_path` macro, which strips scheme, host, query string, and fragment and enforces a trailing slash so tracking parameters and the `www` host collapse onto the site's own path.
- Keep the normalized `page_path` as the natural key in staging, and generate `page_id` and classify pages with the shared `get_page_type` macro in `dim_pages`, the same way `dim_jobs` and `dim_organizations` own their keys. Facts resolve `page_id` by joining on `page_path`, so any source that normalizes paths the same way lands on the same page. Parse slugs in staging with `get_organization_slug` and `get_job_slug`, which return a slug only for current-scheme organization and job paths and null for every other path, whether given a repository file path or a site page path. Keep `job_id` and `organization_id` on the facts so they join straight to `dim_jobs` and `dim_organizations`.
- Resolve countries to `dim_countries` by code in the mart. Normalize Search Console country codes to uppercase alpha-3 in staging; Google's `ZZZ` unknown region stays unresolved rather than getting a synthetic row.
- Resolve job slugs only under the current `/jobs/{organization}/{job}/` scheme; legacy flat single-segment job paths are still `job` pages but stay unresolved rather than being guessed at, matching how legacy job links are treated in the email domain.
- dbt unit tests target models rather than macros, so test shared path macros through native unit tests on the models that call them.
- Keep the URL-level and property-level facts separate and never union them. Property-level impressions count one appearance per search even when several of the site's pages rank for it, so property totals are lower than URL totals rather than equal to them.
- Carry the anonymization caveat in every mart and module description. Most impressions sit on rows where Google withheld the query, so a query drilldown describes a minority of volume and grouping by query silently drops the rest.
- Collapse the export's Google Jobs appearance flags into one `search_appearance` categorical in staging. Google only sets them when a page qualified for the jobs experience, so they are the export's evidence that `JobPosting` markup is being parsed. The flags are mutually exclusive today; a source data test fails if Google ever sets both, since the categorical would then hide one.
- Do not populate `validThrough` in site structured data just to fill the field. Google requires it only when a posting has a known expiration date, and deactivating a posting is already a documented way to expire a listing.

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
