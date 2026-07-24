# Prediction-to-probe and continuous repair loop

`SKILL.md` is authoritative. This file expands probing and repair mechanics.

Prediction produces hypotheses. Parking requires verdicts.

The core discipline:

```text
No material prediction without a probe.
No confirmed defect without a regression signal.
No repair without retesting.
No completion without re-prediction.
```

## Probe ledger

Maintain:

```text
PROBE-###
Prediction:
Invariant:
Probe level:
Setup:
Command/action:
Expected pass:
Expected fail:
Observed:
Raw evidence:
Verdict:
Follow-up:
```

Verdicts:

- **disproved** — valid probe demonstrated the invariant holds;
- **confirmed** — failure reproduced or code evidence is decisive;
- **inconclusive** — setup/tool/environment could not distinguish pass/fail;
- **blocked-external** — definitive external barrier;
- **accepted-risk** — user explicitly accepts the unresolved risk;
- **fixed-verified** — confirmed defect repaired and regression probe passes.

Never silently convert `inconclusive` to `disproved`.

## Choose the cheapest valid probe

Cheap is good only when it can falsify the claim.

### Level 1 — static proof

Use for:

- missing auth predicate;
- enum/constraint mismatch;
- wrong route;
- impossible branch;
- unhandled null;
- provably duplicated side effect.

Evidence:

- exact code path;
- schema or type definitions;
- caller inventory;
- state-transition comparison.

Static proof is not enough for timing, browser lifecycle, provider behavior, or
ambiguous runtime shapes.

### Level 2 — focused unit test

Use for:

- pure domain rules;
- parsers/normalizers;
- routing helpers;
- state transition functions;
- amount/date calculations.

Test the invariant and failure shape, not implementation trivia.

Weak:

```text
expects helper to return what the helper currently returns
```

Strong:

```text
unknown Rx state cannot produce shippable=true
```

### Level 3 — integration/API probe

Use for:

- auth and tenant scoping;
- database constraints;
- idempotency;
- transactional writes;
- webhook replay;
- provider adapter behavior with a fake/sandbox.

Assert durable state and side-effect count, not only HTTP status.

### Level 4 — browser/user-journey probe

Use for:

- navigation and redirects;
- hydration;
- back/forward behavior;
- stale UI after mutation;
- loading/error/retry states;
- keyboard/mobile interaction;
- state preservation through multi-step funnels.

Assert URL/state, user-visible content, and backend effect when possible.

### Level 5 — concurrency/fault injection

Use for:

- duplicate clicks;
- two workers;
- cron+webhook overlap;
- callback replay;
- timeout-after-provider-accept;
- process death after claim;
- stale response arriving late.

Prefer deterministic barriers, fake clocks, controlled promises, transaction
hooks, or isolated fixtures. A flaky race loop is evidence only when the
failure is captured clearly.

### Level 6 — target-environment verification

Use for claims about:

- applied migrations;
- real environment variables;
- scheduler/cron installation;
- provider credentials;
- production/sandbox routing;
- deployed flags;
- actual external callbacks.

Local `.env` and repository config do not prove deployed truth.

Obtain authorization before mutations, real charges, messages, migrations, or
deployments.

## Probe design rules

Before running:

1. state the prediction;
2. state what observation would disprove it;
3. ensure the setup reaches the intended branch;
4. isolate destructive effects;
5. capture raw evidence.

After running:

1. verify the setup itself;
2. classify the result;
3. update the prediction record;
4. select the next action.

If a browser test fails before the feature loads, the feature prediction remains
unprobed. If a provider sandbox is down, provider behavior remains unverified.

## Baseline command ledger

Freeze commands before repair:

```text
CHECK-01: npm run test:booking
CHECK-02: npm run typecheck
CHECK-03: npx eslint <parked files>
CHECK-04: npx playwright test tests/booking.spec.ts
```

Record:

- command;
- working directory;
- environment overrides;
- pass/fail counts;
- duration when useful;
- failure ownership.

After repair, rerun the same command. Additional checks may be added; baseline
checks may not be quietly removed or weakened.

If infrastructure requires a corrected invocation (wrong port, missing reuse
flag), record both the failed setup attempt and the corrected canonical command.

## Confirm before repair

A defect is repairable when:

- the failure is reproduced or code proof is decisive;
- severity and blast radius are understood;
- the causal lines are inside the boundary;
- the intended behavior is known;
- the patch can be verified.

Ask for a user decision when multiple product-correct behaviors exist.

## Repair waves

### Wave A — P0

Fix one causal cluster at a time. Add fail-closed behavior where safety is
unknown. Verify auth/tenancy, money/data invariants, and rollback/recovery.

After each P0 patch:

1. inspect diff;
2. run prediction probe;
3. run baseline checks;
4. run adjacent trust-boundary probes;
5. re-predict the changed path.

### Wave B — P1

Group only defects sharing a root cause. Do not mix unrelated UI, retry, and
schema fixes into one opaque batch.

After each batch:

- targeted probes;
- exact baseline commands;
- dependent-path browser/API checks;
- prediction status update.

### Wave C — P2

Every confirmed material P2 in the supported parked surface requires closure:

- fix it when behavior is unambiguous and the patch is inside the boundary;
- block with evidence when repair depends on an external/user-owned decision;
- obtain explicit user acceptance when leaving the risk is intentional.

Documentation alone is not closure.

### P3

Do not derail the park. Report it unless it blocks reliable verification.

## Continuous loop

```text
while contract not proved:
    select highest-severity open uncertainty
    if unprobed:
        run valid probe
    if confirmed and authorized:
        add regression signal
        patch smallest causal surface
        inspect diff
        rerun targeted probe
        rerun frozen baseline
        rerun dependent probes
        re-predict affected surface
    if inconclusive:
        improve setup or escalate probe level
    if external:
        verify target or record blocked evidence
    judge completion
```

## Re-predict after repair

Every repair can:

- change an auth boundary;
- alter state order;
- introduce retry duplication;
- invalidate existing tests;
- make copy dishonest;
- break an alternate entry;
- create a migration/deploy-order dependency.

Run a delta predict:

```text
What new branch exists?
What moved earlier or later?
What now happens twice?
What assumption changed?
What caller still expects old behavior?
What failure is now swallowed?
What rollback path changed?
```

Reopen predictions that depend on changed behavior.

## Blast-radius retesting

For each modified symbol, inspect:

- direct callers;
- shared types;
- sibling roles/tenants;
- free/paid variants;
- mobile/desktop paths;
- API and background callers;
- old and new data shapes.

Retest proportional to risk. A one-line shared auth helper change has a larger
blast radius than a fifty-line isolated display component.

## Handling red outside the boundary

Classify every red:

```text
RED-###
Command:
Failure:
Ownership: parked | pre-existing | environmental | unknown
Evidence:
Effect on parked proof:
Action:
```

Rules:

- parked red: fix and loop;
- pre-existing red: do not touch, but do not claim repository green;
- environmental red: correct setup if safe, then rerun;
- unknown red: investigate until ownership is known or blocked.

Do not use unrelated red as an excuse to skip parked checks. Do not use parked
green to hide repository red.

## Long-running checks

Background builds, CI, deploys, migrations, and data jobs need:

- stable process/job identity;
- expected duration;
- completion or health sentinel;
- failure sentinel;
- a wait barrier;
- independent work while waiting.

Poll only when the next step is blocked and the job needs active supervision.
Otherwise rely on completion notification.

When a long-lived server reaches a healthy steady state, record health and stop
waiting for it to exit.

## Flaky checks

Do not rerun until green and call it fixed.

When a check flakes:

1. preserve the first failure;
2. identify whether setup, timing, data, or product behavior caused it;
3. reproduce with trace/log/screenshot;
4. make the probe deterministic if inside scope;
5. report unresolved flake as verification debt.

Repeated green reduces confidence in flakiness; it does not disprove a captured
race.

## Final proof matrix

Before completion:

```text
Requirement | Prediction IDs | Probe IDs | Final evidence | Verdict
------------|----------------|-----------|----------------|--------
No duplicate callback | PRED-017 | PROBE-021 | replay test 2/2 pass | proved
Cross-tenant denied   | PRED-003 | PROBE-008 | integration 403 + 0 writes | proved
Prod cron configured  | PRED-031 | PROBE-044 | no target access | blocked
```

Every contract requirement and open high-risk prediction must appear.

## Exit gate

The loop may exit only when:

- frozen baseline checks are rerun and classified;
- all material P0–P2 predictions are `disproved`, `fixed-verified`,
  `blocked-external`, or user-accepted;
- no material prediction is silently unprobed;
- fixes received delta predict and blast-radius retest;
- final proof matrix supports the completion judge.
