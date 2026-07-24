# Domain lenses — convergent prediction generators

Lenses complement the Lateral Battery: the battery breaks the frame, lenses
sweep known minefields. Load only lenses whose triggers intersect the
boundary's risk tags (`park.py boundary` emits them). "Not applicable" must
be reasoned from the runtime graph, not assumed. Convert every hit into a
prediction record; a lens item you nodded at but never recorded does not
exist.

## Runtime graph edge-questions (Phase 3 companion)

For every edge in trigger → input → auth → validation → domain → persistence
→ external effect → callback → visible state → recovery, ask: What identity
crosses here? Which value is trusted, and who says so? Which store is
authoritative? Can this edge run twice, late, or out of order? What does
partial success leave behind? What does the user believe happened? Draw
separate graphs for materially different paths: alternate role/tenant,
retry, cancellation, webhook vs sync, cold-start vs steady-state, old
client/new server.

## Auth, authorization, tenancy — trigger tags: auth, tenant, role, session

Server-side enforcement on every mutation, not just pages; role derived
server-side; any client-supplied ID swappable for another user/org/tenant's
(IDOR); list/read/update/delete sharing the same tenant predicate; nested
resources reachable through a parent from another tenant; admin/service
clients that bypass row-level security without explicit scoping; unknown or
missing role failing closed; invitation/impersonation/preview modes
isolated; sessions surviving role or account switches; background jobs
carrying the correct tenant identity; error messages leaking resource
existence.

## Input and validation — always applicable

Client-authoritative fields that shouldn't be (price, role, status, owner,
flags); empty, null, missing, zero, negative, NaN, huge, duplicate, and
malformed values changing safety behavior; parse failure defaulting unsafe;
injection surfaces (URL, path, redirect, HTML, SQL/filter fragments,
headers); fields the UI never sends but the API accepts.

## Data, schema, migrations — tags: schema, migration, sql, model

Missing migration/index/constraint for new code (negative space); type-union
vs DB-enum drift; legacy/partially-backfilled rows; stale read followed by
blind overwrite; transaction boundaries that can orphan; deploy order —
code-before-migration and migration-before-code both survivable; rollback
possible after the first irreversible write.

## State machines and concurrency — tags: retry, lock, queue, cron, webhook, async

Impossible transitions accepted; terminal states resurrected; cancellation
racing success; callback arriving before initiation persists; retry after
timeout duplicating side effects; two clicks / two workers / cron+webhook on
one resource; lease expiring mid-work; late response overwriting newer
truth; process killed between claim and settle.

## External providers — tags: api key, provider, http client, sdk

Missing/invalid credentials in the *target* env; 4xx vs 5xx vs timeout
handled distinctly; provider-accepted-but-local-persist-failed and the
reverse; response schema drift; rate limits and pagination; webhook
signature verification and replay windows.

## Money and scarce resources — tags: payment, charge, price, credit, stock, quota

Client price trust; initiation-vs-callback amount mismatch;
currency/rounding/tax asymmetry; stock/slot/hold checked earlier than
committed; free path bypassing a paid-path invariant; refund/cancel/
reconcile asymmetric with purchase; every conservation-law violation is P0.

## Notifications and messaging — tags: email, sms, notify, push

Model the logical event (`reminder:<entity-id>:<offset>`), not the send:
recipient eligibility and consent checked at send time, not enqueue time; a
durable per-channel claim/outbox before provider submission; provider retry
of a slow success deduplicated; permanent-mute only on terminal provider
errors, not blips; seed/test users excluded from real outreach; regional
delivery constraints (sender IDs, template pre-registration) verified in the
target environment.

## UI honesty and recovery — tags: toast, status, disabled, optimistic

Success shown before durable success; disabled controls enforced only in
UI; hidden error branches; back/refresh/resume mid-flow; an operator
recovery path for every contradictory state the Cut-the-Wire operator found.

## Ops, deploy, observability — tags: env, flag, config, deploy

Flag/env present in every deployment target; cache and queues carrying old
schema through a rolling deploy; enough logging to reconstruct the incident
INVERT wrote; secrets, debug code, and lockfile drift out of the final diff.

## Privacy and AI surfaces — tags: pii, export, prompt, model

PII in logs, exports, and error messages; retention/deletion honored by the
new rows; prompt-injectable inputs reaching tool-bearing model calls;
model output trusted as authorization or fact without verification.
