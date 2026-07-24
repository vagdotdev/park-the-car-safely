---
name: park-the-car-safely
description: >-
  Relentless post-implementation QA and ship-readiness loop. Use when the user
  says "park the car safely", "park my car", "do the checking loop", "I drove,
  you park", or asks for an exhaustive safety pass after building a feature.
  Establishes a persistent completion contract, maps the runtime surface,
  baselines tests and typecheck, predicts failures across P0-P3, turns every
  material prediction into a probe, fixes confirmed defects in severity waves,
  continuously retests and re-predicts, independently judges completion, and
  refuses to declare ship-ready without concrete evidence. This is a long-range
  QA objective, not a redesign pass.
---

# Park the car safely

The user already drove. You are the closer.

Do not admire the feature. Do not rewrite it to suit your taste. Do not run one
happy path, see green, and hand back the keys. Your job is to attack the parked
surface until its important claims either survive evidence or break in a way
you can reproduce and repair.

Be aggressive about uncertainty. Be conservative about edits.

Every material prediction must end in one of these states:

1. **Disproved by evidence**
2. **Confirmed, fixed, and re-verified**
3. **Confirmed and explicitly blocked**
4. **Accepted as risk by the user**

“Probably fine,” “tests passed earlier,” and “the helper agent said green” are
not states. They are evasions.
## Prime directive

Keep working until the completion contract is proven or a genuine stop
condition is reached. Do not end a turn merely because you completed a phase.
The end of a phase means: update park state, select the next concrete action,
and continue.

If the environment provides persistent goals, todos, background jobs, or
subagents, use them. If it does not, maintain the state block below in the
conversation. The skill cannot create runtime persistence by itself; it directs
continuation during the active invocation and preserves resumable state.

## What this is — and what it is not

This is:

- a standing post-drive objective;
- an evidence-producing audit;
- an adversarial prediction and falsification loop;
- a severity-ordered repair loop;
- a final independent ship judge.

This is not:

- a redesign;
- a refactor safari;
- an excuse to clean unrelated dirty files;
- a broad security audit unless the parked surface requires one;
- permission to push, deploy, migrate, or mutate production without the user’s
  authorization.

The aggression points inward at weak reasoning and outward at failure modes.
It never points sideways at unrelated code.
## Non-negotiable rules

1. **Write the boundary before testing.** No boundary means no park.
2. **Run the baseline yourself.** Prior turns and helper reports do not count.
3. **Predict before editing.** Read-only means read-only.
4. **Probe predictions.** A list of worries is not an audit.
5. **Fix evidence, not imagination.**
6. **Retest after every fix wave.** Use the same commands as baseline.
7. **Re-predict after fixes.** Repairs alter the risk surface.
8. **Separate parked-surface readiness from whole-branch readiness.**
9. **Never hide red.** Classify it as caused, pre-existing, environmental, or
   unknown.
10. **No push or deploy unless explicitly requested.**
## Phase 0 — Arm the standing objective

Before touching code, draft this completion contract:

```text
Park Completion Contract
Outcome:
  The named feature is safe on its supported paths and honest about unsupported
  or externally unverified behavior.

Verification:
  Exact commands, runtime probes, artifacts, and environment checks that prove
  the outcome.

Constraints:
  Behaviors that must not regress; unrelated WIP that must remain untouched;
  no speculative refactors; no unauthorized external mutations.

Boundaries:
  NEW files, MOD files or hunks, runtime entrypoints, storage, integrations,
  migrations, tests, and explicit DO NOT TOUCH paths.

Stop when:
  A destructive/product decision is required; definitive auth/quota/permission
  blocks progress; a target environment cannot be inspected; or three distinct
  reasonable attempts hit the same external blocker.
```
Make the contract concrete. “Tests pass” is not enough. Name the tests. Name
the flows. Name the target environment if deploy truth matters.

Read [GOAL-LOOP.md](GOAL-LOOP.md) for the full standing-goal protocol,
continuation judge, wait behavior, and completion audit.

## Persistent park state

Create and continuously update this state in todos or working notes:

```text
PARK STATE
Objective:
Contract:
Phase:
Boundary:
Do not touch:
Baseline:
System map:
Predictions: total / unprobed / confirmed / disproved / blocked
Open P0:
Open P1:
Fix waves:
Current verification:
External unknowns:
Next concrete action:
Stop condition:
```
Rules:

- Exactly one next action is active.
- Update evidence after every meaningful command, code read, probe, or fix.
- Never reset counts to make progress look cleaner.
- A user correction preempts the loop immediately and rewrites the contract.
- If context is compressed, reconstruct state from evidence before continuing.

## Phase 1 — Draw the real boundary

Start with repository truth:

```bash
git status -sb
git diff --stat
git diff
git log -5 --oneline
```

Then trace the named feature. Build four lists:

- **NEW** — files introduced by the drive
- **MOD** — changed files or exact changed hunks in mixed files
- **RUNTIME SURFACE** — callers, APIs, jobs, storage, migrations, flags,
  integrations, and UI paths that make the feature real
- **DO NOT TOUCH** — unrelated dirty WIP and adjacent systems

Do not confuse `git diff` with runtime scope. A one-line caller change can
activate a large existing payment, auth, or queue path. Conversely, a dirty
file may contain one parked hunk and fifty unrelated hunks. Scope at hunk level
when necessary.

If the request is truly ambiguous and two boundaries would produce materially
different edits, ask one focused question. Otherwise choose the narrowest
coherent boundary and state it.
## Phase 2 — Baseline before prediction

Use the project’s own test culture. Record exact commands and counts:

```text
BASELINE LEDGER
B1  <targeted tests>    → N pass / N fail
B2  <integration/e2e>  → N pass / N fail
B3  <lint>             → clean / findings
B4  <typecheck>        → clean / findings
B5  <build>            → clean / findings / not relevant
```

Minimum:

- the narrowest meaningful tests for the parked surface;
- typecheck, always;
- targeted lint when the project uses it;
- one runtime or browser/API probe when static tests cannot prove the user
  journey.

If baseline is red:

1. determine whether each failure is parked, pre-existing, environmental, or
   unknown;
2. turn parked failures into confirmed prediction/probe records;
3. do not repair unrelated red unless the user expands scope;
4. do not edit until the read-only predict phase is complete;
5. do not call the repository green.

A test that never reaches the feature is not coverage. A stale locator, missing
fixture, dead server, or wrong port must be classified honestly.
## Phase 3 — Model the system before attacking it

Write the feature as a causal map:

```text
entry → validation → authorization → domain logic → persistence
      → external side effect → callback/retry → user-visible state → recovery
```

For every node, record:

- inputs and trust boundary;
- authoritative source of truth;
- state transition;
- failure behavior;
- retry/idempotency behavior;
- observable claim made to the user or operator.

Extract invariants. Examples:

- a patient cannot select a doctor from another clinic;
- amount at payment callback equals server-priced amount;
- unknown permission fails closed;
- the same webhook cannot create two appointments;
- “delivered” requires provider acceptance, not merely an attempted request.

Prediction without invariants becomes random bug brainstorming. Invariants give
you something precise to try to break.

## Phase 4 — Predict broadly, then deeply

This phase is read-only. No “tiny fix while I am here.”

Run two passes:

### Breadth pass

Walk every applicable lens in [PREDICT-PLAYBOOK.md](PREDICT-PLAYBOOK.md) and
[DOMAIN-LENSES.md](DOMAIN-LENSES.md). Generate concrete failure hypotheses
across:

- normal and alternate user journeys;
- auth, roles, and tenancy;
- data shape, migrations, and deploy order;
- money, inventory, quotas, or irreversible state;
- races, retries, idempotency, callbacks, and cancellation;
- external providers, timeout, partial success, and stale data;
- UI hydration, navigation, back behavior, and state restoration;
- observability, copy honesty, and operator recovery;
- compatibility, rollout, rollback, and dirty-world behavior.

### Depth pass

For each high-risk invariant, trace from entrypoint to final effect. Ask:

- What input makes this lie?
- What timing makes this duplicate?
- What missing row makes this fail open?
- What stale state makes this overwrite newer truth?
- What partial success leaves the system contradictory?
- What deploy order makes code and schema disagree?
- What would a normal user do that the happy-path test did not?

Create prediction records, not prose fog:

```text
PRED-###
Severity:
Claim:
Evidence path:
Trigger/precondition:
Expected failure:
Blast radius:
Probe:
Status: unprobed
```

Tag every item:

- **confirmed-from-code**
- **supported hypothesis**
- **speculative external**

Material means P0–P2 risk affecting a supported user/operator path, invariant,
deployability, data, money, trust boundary, side effect, or recovery path.
Rank P0–P3, but do not use severity to avoid probing. Severity controls repair
order, not whether the thought deserves evidence.

## Phase 5 — Turn predictions into probes

Now attack the predictions. Read [PROBE-AND-LOOP.md](PROBE-AND-LOOP.md).

For every material prediction:

1. choose the cheapest probe that can actually falsify it;
2. write expected pass and fail evidence before running;
3. run the probe;
4. capture raw evidence;
5. classify the result.

Probe order usually moves from cheap to expensive:

1. static trace / schema comparison;
2. focused unit test;
3. integration or API probe;
4. browser/user-journey exercise;
5. concurrency, retry, or fault-injection probe;
6. target-environment verification.

Do not write a test that merely repeats the implementation. Test the invariant.
Do not call a prediction disproved because the setup failed. That is
**inconclusive** and remains open.

Material predictions may not disappear. They must be disproved, confirmed,
blocked, or accepted by the user.

## Phase 6 — Repair in severity waves

Fix only after prediction and probing produce evidence.

Repair order:

1. **Wave A — P0:** safety, money, auth/tenancy, data loss, fail-open gates.
2. **Wave B — P1:** normal-path breaks, races, duplicate side effects, stale or
   unrecoverable state.
3. **Wave C — P2:** every confirmed material P2 inside the supported parked
   surface must be fixed, blocked, or explicitly accepted by the user.
4. **P3:** report by default. Do not spend the park polishing.

For each wave:

- state the exact failure and smallest closing patch;
- write or update a regression probe first when practical;
- touch only causal lines;
- inspect the diff immediately;
- run the same baseline commands;
- run the prediction-specific probe;
- re-run dependent-path probes.

If a fix changes a shared invariant, reopen every prediction that depended on
the old behavior.

## Phase 7 — Continuous retest and re-predict

The loop is:

```text
predict → probe → confirm → fix → baseline retest → targeted retest
       → dependent-path retest → re-predict → next open prediction
```

Do not batch unrelated fixes merely to reduce tool calls. Do not continue after
a red retest as if it were bookkeeping. The failure becomes the next active
input.

After each wave, record:

```text
ITERATION N
Predictions closed:
Patch:
Baseline delta:
Targeted evidence:
New regressions:
Predictions reopened:
Next action:
```

Long-running CI, builds, deploys, or migrations should be backgrounded and
waited on with a real completion signal. Do not burn turns saying “still
running.” Do not abandon them and declare completion either.

## Phase 8 — Adversarial completion judge

When you think the work is done, switch back to read-only and try to reject your
own completion claim.

The judge asks:

1. Is every contract requirement proved by current evidence?
2. Is every supported user path exercised or explicitly out of scope?
3. Does any P0/P1 remain open, inconclusive, or hidden as “external”?
4. Did fixes regress an adjacent path or violate a constraint?
5. Are target-environment claims actually verified there?
6. Is branch-wide red being misrepresented as parked-surface green?
7. Did any prediction vanish without disposition?

Verdict:

- **WAIT** — a real background verification barrier is active.
- **PAUSED** — the user paused or the iteration budget was reached with state
  preserved.
- **CONTINUE** — evidence missing, prediction open, regression present.
- **BLOCKED** — definitive external/user decision prevents progress.
- **DONE** — contract proved; material P0–P2 disproved, fixed-verified, or
  user-accepted; final verification is current.

If independent read-only review is available, use it. Give it the contract,
boundary, prediction ledger, fixes, and raw final test results. Do not ask it
for a generic review.

## Phase 9 — Final verification and handoff

Immediately before reporting:

- run the same core tests and typecheck again;
- verify the final diff and file status;
- verify claimed artifacts exist;
- distinguish parked-surface PASS/FAIL from repository PASS/FAIL;
- list external unknowns without pretending they are verified.

Use [REPORT-TEMPLATES.md](REPORT-TEMPLATES.md). The final report is short
because the evidence ledger did the long work.

Minimum handoff:

```text
Parked:
Boundary:
Contract verdict:
Baseline → final:
Predictions: total / disproved / fixed / blocked / accepted
Fixed:
Open P0/P1:
Leftovers:
Ship blockers:
External verification:
Commit/push/deploy status:
```

## Severity authority

- **P0:** normal or plausible path can lose money/data, cross trust boundaries,
  bypass a safety gate, or create irreversible harm. Fix or block ship.
- **P1:** confirmed substantial break, race, duplicate side effect, or
  unrecoverable operator/user failure. Fix before declaring parked.
- **P2:** real but bounded issue with a viable workaround or uncommon trigger.
  Fix, block, or obtain explicit user acceptance under Wave C.
- **P3:** hygiene or polish. Record; do not derail the safety loop.

When uncertain between severities, reason from blast radius and reversibility,
not emotional language.
## Honest blocking

Hard is not blocked. Slow is not blocked. A failing first attempt is not
blocked.

Use BLOCKED only when:

- the next action is a user-owned destructive or product decision;
- permissions, authentication, quota, or external state definitively deny the
  required check;
- target-environment truth cannot be accessed;
- three materially different reasonable attempts reach the same external
  barrier.

Record attempts, evidence, owner, and exact unblock condition.

## Domain playbooks

- Exhaustive prediction method: [PREDICT-PLAYBOOK.md](PREDICT-PLAYBOOK.md)
- Prediction falsification and continuous repair:
  [PROBE-AND-LOOP.md](PROBE-AND-LOOP.md)
- Security, data, money, distributed, UI, integration, and ops lenses:
  [DOMAIN-LENSES.md](DOMAIN-LENSES.md)
- Persistent goal state and conservative completion judge:
  [GOAL-LOOP.md](GOAL-LOOP.md)
- Audit and handoff artifacts: [REPORT-TEMPLATES.md](REPORT-TEMPLATES.md)
- Notification-specific idempotency:
  [notification-idempotency.md](notification-idempotency.md)

Load only the references relevant to the parked surface, except
PREDICT-PLAYBOOK.md and PROBE-AND-LOOP.md, which are mandatory for every
non-trivial park.

## Automatic failure conditions

You failed the park if you:

- skipped the completion contract;
- never wrote the boundary;
- predicted only after editing;
- listed risks but did not probe them;
- trusted another agent’s test claim without raw evidence;
- changed the test command to manufacture green;
- fixed speculative noise while a confirmed P1 remained open;
- called an inconclusive probe a pass;
- forgot deploy order or target-environment truth;
- stopped after the happy path;
- hid whole-branch red behind “feature tests pass”;
- pushed, deployed, migrated, or messaged externally without authorization;
- ended with “looks good” instead of a verdict backed by evidence.

No green by omission. No safety by adjective. Park the actual car.
