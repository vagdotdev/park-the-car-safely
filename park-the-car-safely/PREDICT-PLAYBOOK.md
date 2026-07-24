# Exhaustive predict playbook

`SKILL.md` is authoritative. This file expands its read-only predict phase.

Predict is the read-only construction of an attack map before repair. It is not
a code review summary and not a list of generic concerns.

The output must tell the next phase exactly what to try to break.

## Inputs

Do not begin without:

- park completion contract;
- NEW / MOD / RUNTIME SURFACE / DO NOT TOUCH boundary;
- baseline command ledger with raw results;
- business invariants;
- known target environments and external unknowns.

## Build the runtime graph

Trace the feature as a graph, not a file list:

```text
human/system trigger
  → client state and input
  → route/action/API
  → authentication and authorization
  → validation and normalization
  → domain decision
  → database read/write
  → external provider or async job
  → callback/retry/reconciliation
  → displayed/operator state
  → cancellation/recovery
```

For each edge ask:

- What identity crosses this edge?
- Which value is trusted?
- Which source is authoritative?
- Can this edge run twice?
- Can it run late or out of order?
- What happens on partial success?
- What does the user believe happened?

Draw separate graphs for materially different paths:

- happy path;
- alternate role or tenant;
- retry;
- cancellation;
- free vs paid;
- synchronous vs webhook;
- empty/first-run vs existing-state;
- old client/new server or old schema/new code.

## Extract invariants

Write invariants as falsifiable sentences:

```text
INV-01: A clinic admin can mutate only rows whose clinic_id equals their
resolved clinic.

INV-02: A successful payment callback creates at most one confirmed order for
the provider transaction.

INV-03: Unknown prescription status cannot unlock shipping.
```

Weak:

```text
Auth should work.
Payments should be safe.
```

Every P0/P1 prediction should threaten a named invariant.

## Breadth pass

Walk every applicable category. Do not skip silently.

### Entry and journey coverage

- every CTA, deep link, redirect, back button, resume link, and alternate entry;
- default, empty, loading, success, failure, retry, cancel, and stale states;
- role-specific and anonymous/authenticated variants;
- mobile/desktop or server/client divergence where relevant.

### Trust and authority

- client-supplied IDs, roles, prices, status, ownership, feature flags;
- page-level auth without server-action auth;
- tenant lookup from mutable query params;
- admin/service clients bypassing RLS without explicit scope checks;
- indirect object references and guessed IDs.

### Data and schema

- missing columns/migrations/indexes/constraints;
- TypeScript union vs DB enum/CHECK drift;
- null, empty, duplicate, malformed, legacy, or partially backfilled rows;
- object-vs-array join shape;
- stale read followed by blind overwrite;
- transaction boundaries and orphan creation.

### State transitions

- impossible transitions accepted;
- terminal states resurrected;
- cancellation racing success;
- callback arriving before initiation is fully persisted;
- partial success represented as complete;
- retry after a timeout duplicating side effects.

### Time and concurrency

- two clicks, two workers, cron+webhook, sync+manual action;
- time zone/date boundary and clock skew;
- lease expiry while work is still running;
- late response overwriting newer state;
- process killed after claim but before settle.

### External systems

- missing/invalid credentials;
- provider 4xx vs 5xx vs timeout;
- provider accepted request but local persistence failed;
- local success but provider rejected;
- response schema drift;
- rate limits, pagination, webhook signature, replay.

### Money and scarce resources

- client price trust;
- amount mismatch initiation vs callback;
- currency/rounding/tax/fee asymmetry;
- stock/slot/hold checked too early;
- free path bypassing a paid-path safety invariant;
- refund/cancel/reconcile asymmetry.

### Product truth

- copy says delivered, synced, verified, reserved, paid, or secure when code
  proves only attempted;
- disabled control enforced only in UI;
- hidden errors;
- success toast before durable success;
- operator has no recovery path.

### Deployment and compatibility

- code before migration or migration before code;
- env/flag absent in one deployment target;
- rolling deploy old/new request incompatibility;
- cache or queue carrying old schema;
- rollback impossible after irreversible writes;
- background schedule still calling removed routes.

Use [DOMAIN-LENSES.md](DOMAIN-LENSES.md) for deeper prompts.

## Depth pass

Select high-blast-radius invariants and execute a causal trace.

For each:

1. identify authoritative input;
2. follow all transformations;
3. identify validation and auth gates;
4. locate durable state transition;
5. locate side effects;
6. inspect error/retry/cancel paths;
7. compare user-visible claim with durable/provider truth;
8. inspect all alternate entrypoints into the same transition.

Then ask adversarial counterfactuals:

- What if this value is absent?
- What if it is syntactically valid but belongs to another tenant?
- What if two requests arrive in the same millisecond?
- What if the provider times out after accepting?
- What if local persistence fails after provider success?
- What if the callback is replayed?
- What if the schema is one migration behind?
- What if this is the first row ever?
- What if legacy data violates the new assumption?
- What if the user refreshes or presses Back?

## Prediction record

Use one record per falsifiable failure:

```text
PRED-017 — Duplicate appointment after callback retry
Severity: P0
Invariant: INV-02
Confidence: high | medium | low
Evidence class: confirmed-from-code | supported-hypothesis | speculative-external
Evidence path:
  api/payu/callback.ts:createAppointment → appointments.insert
Trigger:
  Same valid provider callback delivered twice
Predicted failure:
  Two confirmed appointments and two Clinicea pushes
Blast radius:
  Patient charged once but receives duplicate bookings; clinic schedule corrupt
Cheapest valid probe:
  Replay identical signed callback twice against isolated fixture and assert one
  appointment + one provider push
Expected pass evidence:
  Second call returns existing reference; row count remains one
Expected fail evidence:
  Row count or push spy equals two
Status: unprobed
```

## Evidence classes

### Confirmed-from-code

The trace itself proves the failure:

- mutation lacks any tenant predicate;
- error branch returns success;
- parser converts unknown safety state to false;
- side effect occurs before idempotency claim.

The decisive trace counts as a Level 1 static probe. Escalate to runtime probing
when preconditions, timing, framework behavior, or blast radius remain unclear.

### Supported hypothesis

Code presents a concrete failure shape but runtime evidence is needed:

- two workers may race between read and insert;
- React state may go stale during fast navigation;
- timeout may duplicate a provider request.

These are prime probe targets.

### Speculative external

Depends on environment truth not inspected:

- production migration may be missing;
- provider key may be invalid;
- cron may not be scheduled.

Do not patch code to “fix” speculation. Verify the environment or put it on the
ship checklist.

## Severity

Rank from trigger plausibility, blast radius, reversibility, and detectability.

### P0

- cross-tenant access;
- wrong charge or financial loss;
- data destruction/corruption;
- fail-open medical, permission, payment, or prescription gate;
- normal path creates irreversible contradiction.

### P1

- normal or common path breaks;
- duplicate external side effect;
- transient failure creates permanent mute/stuck state;
- stale write overwrites valid newer state;
- no recovery from a common provider failure.

### P2

- uncommon edge with bounded impact;
- recoverable operator path;
- honest soft failure;
- unsupported deep link;
- non-critical copy mismatch.

### P3

- hygiene, maintainability, naming, optional coverage, cosmetic polish.

Do not inflate severity to justify an edit. Do not deflate it to avoid work.

## Completeness challenges

Before ending predict, run these challenges:

### The omitted path challenge

Name every entrypoint and explain why it is covered or out of scope.

### The dirty-world challenge

Assume legacy rows, duplicate rows, missing optional fields, stale browser
state, and half-applied rollout.

### The double-execution challenge

Assume every externally triggered operation runs twice, concurrently, late,
and after a timeout.

### The authority challenge

Replace every client-provided identifier with another valid identifier from a
different user/tenant.

### The partial-success challenge

Cut power between every external side effect and every local write.

### The honesty challenge

Read every success/status label literally. Identify the exact evidence that
earns each word.

### The rollback challenge

Ask what happens if the release rolls back after new writes exist.

## Explicit non-findings

Record areas checked and cleared:

```text
NON-FINDING NF-04
Area: Clinic tenancy on cancel action
Trace: page → cancelAppointment → requireClinicUser → appointment.clinic_id match
Probe: cross-clinic fixture returned 404; own-clinic fixture succeeded
Result: invariant holds
```

Non-findings are evidence of breadth. “No P0 found” without non-findings is not
an exhaustive predict.

## Exit gate

Predict is complete only when:

- runtime graphs exist for all supported path families;
- applicable lenses were walked or explicitly skipped with reason;
- high-risk invariants have prediction records;
- each material prediction has a proposed probe;
- non-findings show what was cleared;
- no edits occurred during the phase.
