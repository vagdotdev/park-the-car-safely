# Domain attack lenses

`SKILL.md` is authoritative. This file supplies prediction lenses, not new
repair authority.

Load the lenses that intersect the parked runtime graph. “Not applicable” must
be reasoned, not assumed.

These are prediction generators. Convert relevant items into falsifiable
prediction records and probes.

## Authentication, authorization, and tenancy

- Is auth enforced at every server mutation, not only page/UI?
- Is role derived server-side?
- Can a valid user supply another user’s, clinic’s, org’s, or project’s ID?
- Does an admin/service client bypass RLS? If so, where is explicit scope
  enforced?
- Do list/read/update/delete use the same tenant predicate?
- Can nested resources be accessed through a parent from another tenant?
- Are invitation, account-switch, impersonation, and preview modes isolated?
- Does cached/session state survive a role or account switch incorrectly?
- Do background jobs carry the correct tenant identity?
- Do error differences leak resource existence?

High-risk probes:

- same request with a valid cross-tenant ID;
- patient token against staff action;
- clinic A token against clinic B row;
- stale session after account switch;
- direct API call bypassing disabled UI.

## Input, validation, and parsing

- Which fields are client-authoritative that should not be?
- Do empty string, null, missing, zero, negative, NaN, huge, duplicate, or
  malformed values change safety behavior?
- Does parsing failure default safe or unsafe?
- Are URLs, file paths, redirects, HTML, SQL/filter fragments, and headers
  constrained?
- Does validation happen before external side effects?
- Do client and server schemas disagree?
- Are enum fallbacks honest?
- Are uploaded file type, size, count, and ownership checked server-side?

High-risk probes:

- syntactically valid foreign ID;
- unknown enum;
- malformed JSON that parser converts to empty;
- oversized payload;
- local-path vs protocol-relative redirect.

## Database, schema, and migrations

- Does every referenced column/table/index/constraint exist in a versioned
  migration?
- Is deploy order safe both code-before-schema and schema-before-code?
- Do DB CHECK/enum/nullability rules match TypeScript?
- Is uniqueness enforced in the database or only checked in code?
- Are multi-write transitions transactional?
- Can partial failure create orphans?
- Are backfills idempotent and complete?
- Can old rows violate new assumptions?
- Are indexes present for new hot queries and foreign keys?
- Does rollback leave unreadable new data?
- Does RLS cover new tables and operations?

High-risk probes:

- apply migrations on empty and upgraded schema;
- insert duplicate under concurrency;
- legacy/null row through new code;
- transaction fault between writes;
- RLS checks with anon, user, and service paths.

## Money, payments, credits, stock, and holds

- Is amount computed server-side?
- Do initiation, callback, invoice, refund, and display use the same amount and
  currency?
- Are rounding, taxes, fees, discounts, and zero-value paths symmetric?
- Is callback signature verified before mutation?
- Is provider transaction uniquely bound to one local order?
- Is callback replay idempotent?
- Does a late success resurrect cancelled/expired state?
- Are stock/slots/credits rechecked at commit time?
- Do holds expire safely and release on every terminal path?
- Can free or manual paths bypass safety gates?
- Does refund failure leave local state claiming refunded?

High-risk probes:

- tampered client amount;
- duplicate signed callback;
- timeout after provider acceptance;
- callback after cancellation;
- two buyers for final unit/slot;
- zero-value checkout;
- partial refund.

## State machines, races, and idempotency

- Are allowed transitions explicit?
- Can terminal states transition backward?
- Is check-then-act protected by lock, unique constraint, CAS, or lease?
- Can two UI clicks, workers, callbacks, or schedules run the same action?
- Is idempotency key stable and scoped correctly?
- Does retry repeat an external side effect?
- Can stale async response overwrite newer state?
- Can claim-before-send mute forever after failure?
- Can mark-after-send duplicate under overlap?
- Can process death strand a claim or hold?
- Are leases longer than maximum work duration and renewable?

High-risk probes:

- controlled concurrent requests;
- replay same event;
- reverse callback order;
- fake timeout after side effect;
- expire lease mid-work;
- kill worker after claim.

## External APIs and integrations

- Are credentials presence and validity distinguished?
- Are sandbox and production endpoints unmistakable?
- Are timeouts, retries, backoff, and rate limits bounded?
- Which 4xx are permanent vs retryable?
- Does provider success precede local persistence?
- Is response shape validated?
- Are pagination and partial pages handled?
- Are webhook signatures, timestamps, and replay protected?
- Can fallback/stub behavior be mistaken for live success?
- Is provider ID stored before retry?
- Is reconciliation available for split-brain outcomes?
- Are logs scrubbed of secrets and sensitive payloads?

High-risk probes:

- 401, 429, 500, timeout, malformed success body;
- provider accepts then local DB fails;
- local DB succeeds then provider rejects;
- duplicate/out-of-order webhook;
- expired credentials;
- partial pagination.

## Notifications and communications

Load [notification-idempotency.md](notification-idempotency.md).

Also ask:

- Can test/seed users receive real outreach?
- Is consent/channel preference checked at send time?
- Does copy claim delivery or only enqueue?
- Are templates approved for the target region/provider?
- Are phone/email joins robust to data shape?
- Is every channel independently idempotent?

## Background jobs, cron, queues, and webhooks

- Can two schedulers overlap?
- Is the job authenticated?
- Is batch selection deterministic and bounded?
- Is claim atomic?
- What happens when max duration kills the process?
- Are retries visible and capped?
- Is poison work isolated?
- Can one bad row abort the batch?
- Is dead-letter/recovery available?
- Is schedule configuration deployed to the target?
- Do old cron routes still exist?
- Does clock/time zone alter due selection?

High-risk probes:

- invoke twice concurrently;
- process death after claim;
- one malformed row in batch;
- job beyond max duration;
- missing cron secret;
- replay webhook.

## Frontend, navigation, and client state

- Do direct URL, CTA, refresh, Back, Forward, and resume produce the same valid
  state?
- Is required state only in memory?
- Can stale session/local storage override URL truth?
- Does changing an upstream choice invalidate downstream state?
- Can loading race permit double submit?
- Does optimistic UI roll back on failure?
- Does a late request overwrite newer selection?
- Are errors actionable and retryable?
- Are disabled states enforced server-side?
- Does hydration change selected/default state?
- Are keyboard, mobile viewport, and accessible names functional?
- Do deep links preserve type/tenant/context without loops?

High-risk probes:

- rapid choice changes with delayed responses;
- refresh each funnel step;
- browser back after mutation;
- duplicate click;
- direct malformed URL;
- expired local storage;
- network failure then retry.

## Security and privacy

- Are secrets or service keys exposed to client bundles/logs?
- Are sensitive rows returned more broadly than displayed?
- Is PII/medical/payment data logged?
- Are uploads private and access-controlled?
- Are redirects, HTML, markdown, file names, and URLs sanitized?
- Is SSRF possible through server fetch?
- Are rate limits applied to expensive or sensitive endpoints?
- Can password/reset/invite tokens be replayed or leaked?
- Are error messages over-detailed?
- Do analytics/session replay capture sensitive input?
- Are destructive actions CSRF-resistant where relevant?

For a dedicated security request, use the platform’s security-review workflow.
This lens does not replace specialist review.

## Time, dates, and scheduling

- Which time zone is authoritative?
- Are date-only values parsed without UTC drift?
- What happens at midnight, DST, month/year boundaries?
- Are lead time and business hours checked at commit?
- Can stale availability be booked?
- Are recurring schedules idempotent?
- Do provider and local calendars use the same zone?
- Does retry occur on the intended day?

High-risk probes:

- near-midnight request;
- DST transition where applicable;
- end-of-month/year;
- same slot booked concurrently;
- provider returns zone-less timestamp.

## Files, media, and generated artifacts

- Is path traversal prevented?
- Are file type and content type both checked?
- Are size/count/dimension limits server-side?
- Are temporary files cleaned on success and failure?
- Is object ownership enforced?
- Can replacement orphan old media?
- Are generated files deterministic and complete?
- Does partial upload appear complete?
- Are signed URLs scoped and short-lived appropriately?

## Performance and resource limits

- Did a new path create N+1 queries?
- Are unbounded lists, recursion, retries, logs, or payloads possible?
- Can a user trigger expensive work repeatedly?
- Does serverless duration fit worst-case batch?
- Is memory proportional to untrusted input?
- Do indexes support filters/order?
- Does client render/fetch loop?
- Are background jobs chunked with resumable progress?

Performance becomes P0/P1 when it causes normal-path outage, runaway cost, or
safety-state partial execution.

## Observability and operator recovery

- Can operators distinguish attempted, accepted, settled, failed, and retried?
- Are correlation/provider IDs logged?
- Are logs structured around state transitions?
- Are failures surfaced without leaking secrets?
- Is there a reconciliation or retry action?
- Can stuck rows be identified?
- Are metrics/alerts attached to new critical paths?
- Does UI status match durable/provider truth?
- Can a manual recovery double-run side effects?

## Feature flags, rollout, and compatibility

- Is default flag state safe when missing?
- Are server and client flag evaluations consistent?
- Can partial rollout mix incompatible payloads?
- Does old data/client survive new schema?
- Can flag-off recover rows created while on?
- Is rollback safe?
- Are migrations backward compatible?
- Are cached assets/API responses version-tolerant?

## AI/LLM features

- Is model output treated as untrusted input?
- Are tool calls authorized independently?
- Can prompt injection reach secrets or privileged tools?
- Are structured outputs validated?
- Is fallback behavior safe and honest?
- Are cost/token limits bounded?
- Are medical/legal/financial claims gated appropriately?
- Does retry duplicate side effects?
- Are user data and prompts sent only to approved providers?

## Lens completion record

For each park, record:

```text
Lens | Applied? | Prediction IDs | Non-finding evidence | Skip reason
-----|----------|----------------|----------------------|------------
Tenancy | yes | PRED-01, PRED-02 | NF-01 | —
Money | no | — | — | no monetary/scarce-resource path in runtime graph
Cron | yes | PRED-09 | NF-07 | —
```

An explicit skip is auditable. An omitted lens is forgotten work.
