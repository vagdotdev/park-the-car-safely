# Persistent park goal loop

`SKILL.md` is authoritative. This file expands its standing-goal mechanics.

Use this playbook to keep a park alive across many tool calls, test runs,
background jobs, context compressions, and user interruptions.

The pattern adapts standing-goal systems such as Hermes Agent’s `/goal`:

- one durable objective;
- a structured completion contract;
- explicit continuation after each partial turn;
- a conservative completion judge;
- wait barriers for genuine background work;
- a finite budget and honest pause/block behavior.

A markdown skill cannot install a scheduler or judge model. Do not pretend it
can. Use native goal/todo/background capabilities when available; otherwise
enforce the same state machine in working notes and keep taking the next action
until the contract is proved.

## The park contract

The goal must be checkable. Draft these fields before work:

| Field | Required meaning |
|---|---|
| Outcome | The single state that must be true at completion |
| Verification | Commands, runtime probes, artifacts, and environment facts that prove it |
| Constraints | What must not change, regress, or be touched |
| Boundaries | Files, hunks, paths, services, and environments in scope |
| Stop when | Conditions requiring user input or an external change |

Bad:

```text
Outcome: Make it safe.
Verification: Tests pass.
```

Good:

```text
Outcome:
  Rescheduling cannot create duplicate appointments, cannot move another
  clinic’s appointment, and leaves the original appointment unchanged when
  Clinicea rejects the move.

Verification:
  npm run test:booking passes; targeted concurrency test proves one winner;
  browser exercise covers success and provider rejection; production mapping
  remains explicitly unverified unless checked.

Constraints:
  Preserve the patient-facing response shape. Do not alter unrelated pharmacy
  WIP. Do not call production Clinicea.

Boundaries:
  Reschedule action, appointment sync helper, its tests, and the patient
  reschedule UI.

Stop when:
  A schema migration is required or the provider sandbox cannot reproduce the
  callback behavior after three distinct attempts.
```

## Goal state

Use native goal state if available. Otherwise keep:

```text
PARK GOAL
Lifecycle: active | waiting | paused | blocked | done
Last judge verdict: WAIT | PAUSED | CONTINUE | BLOCKED | DONE
Turn/iteration:
Outcome:
Verification:
Constraints:
Boundaries:
Stop when:
Additional criteria:
Current phase:
Evidence produced:
Predictions open:
Failures open:
Background work:
Next concrete action:
Last judge verdict:
```

Persist facts, not narrative. “Ran tests” is weak. “`npm run test:booking`:
47 pass, 1 fail in duplicate callback” is state.

## Continuation rule

At the end of every partial work segment, silently apply:

```text
[Continuing toward the standing park goal]

Review the contract and current PARK GOAL state.
Take the next concrete action that most reduces open P0/P1 uncertainty.
Stay inside boundaries and constraints.
Do not claim completion without current verification evidence.
If a real stop condition is reached, produce a blocked audit.
Otherwise continue.
```

Do not send a final response simply because:

- one test command finished;
- a helper returned;
- the first bug was fixed;
- the happy path passed;
- a long command moved to background;
- context was compressed;
- the user has not replied.

These are continuation events.

## Additional criteria

If the user adds requirements mid-park:

1. preserve their wording;
2. append it under `Additional criteria`;
3. identify which predictions, probes, and fixes must be reopened;
4. do not reset evidence that remains valid;
5. judge completion against the original contract plus all added criteria.

A user correction or narrowing overrides older goals immediately.

## Conservative judge

After each major phase and before final output, decide:

```json
{
  "verdict": "WAIT | PAUSED | CONTINUE | BLOCKED | DONE",
  "reason": "one concrete evidence-based sentence",
  "missing_proof": ["..."],
  "next_action": "..."
}
```

Judging rules:

- `done` requires every verification item to have direct, current evidence;
- a violated constraint forces `continue` unless the user accepts it;
- an unprobed material prediction forces `continue`;
- an open P0/P1 forces `continue` or `blocked`;
- “I implemented it” is not proof;
- “all tests pass” without command output is not proof;
- parked-surface green cannot erase whole-branch red;
- a target-environment claim requires target-environment evidence;
- if the agent is waiting on a real background verification process, use
  `wait`, not repetitive continuation.

Judge failures should bias toward continued verification, not premature
completion. A finite iteration budget prevents endless spinning.

## Iteration budget

Use a soft budget of 20 meaningful iterations by default. An iteration is a
predict/probe/fix/retest unit, not every tool call.

At the budget:

1. do not manufacture completion;
2. summarize evidence and open predictions;
3. pause with the exact next action;
4. ask the user whether to resume if meaningful work remains.

Resetting the budget is allowed when the user resumes or materially expands the
contract. It is not permission to repeat failed tactics.

## Waiting correctly

Use `waiting` when progress is genuinely gated by:

- CI;
- a build or test matrix;
- a deployment;
- a migration;
- a provider callback;
- a rate-limit cooldown;
- a long data-generation or audit process.

Record:

```text
WAIT BARRIER
Process/job:
Reason:
Release signal:
Started:
Expected range:
What work can continue in parallel:
```

Rules:

- prefer process completion or a stable sentinel over blind sleep;
- continue independent analysis while waiting;
- do not poll fire-and-forget jobs compulsively;
- do not call the goal blocked because the expected wait has not finished;
- if the process hangs beyond a reasoned bound, collect evidence and either
  recover it safely or produce a blocked audit.

## User preemption

Any new user message takes priority:

- correction/narrowing: rewrite the contract;
- new acceptance criterion: append it;
- pause/stop: stop immediately;
- status request: report state, then continue unless told otherwise;
- unrelated new task: ask whether to pause the active park only if both cannot
  safely coexist.

Never let an automated continuation override an explicit human redirect.

## Context recovery

After context compression, resume, or interruption:

1. read the latest PARK GOAL state;
2. re-read the boundary and contract;
3. verify current repository status;
4. check background-job state;
5. do not rerun expensive work whose evidence is still current unless required
   by the final-verification rule;
6. continue from `Next concrete action`.

If state is missing, reconstruct it from git diff, test outputs, prediction
records, and the newest user request. Do not restart from scratch blindly.

## Blocked audit

Blocked is a precise result:

```text
BLOCKED
Goal:
Blocking condition:
Why it is definitive:
Attempts:
Evidence:
Work completed safely:
Open risk:
Owner/action required:
Exact resume point:
```

Do not use blocked for difficulty, slowness, or lack of imagination. Three
identical retries are one attempt, not three.

## Completion audit

Before `done`, derive every requirement from:

- outcome;
- verification;
- constraints;
- boundaries;
- additional criteria;
- predictions opened during the park.

Mark each:

- `proved`
- `contradicted`
- `incomplete`
- `inconclusive`
- `accepted-risk`

Only `proved` and user-authorized `accepted-risk` may remain at completion.
Anything else means continue or blocked.
