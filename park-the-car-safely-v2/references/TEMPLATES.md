# Templates

Most ledgers (baseline, predictions, probes) are produced by `park.py` and
live in your park's own directory — `.park/parks/<park-id>/` — so do not
duplicate them by hand. These are the two artifacts the human actually reads.

## Completion contract (`contract.md`, created by `park.py init`)

```text
PARK COMPLETION CONTRACT
Outcome:
  The single state that must be true at completion, named concretely.
  Bad: "Make rescheduling safe."
  Good: "Rescheduling cannot create duplicate appointments, cannot move
  another tenant's appointment, and leaves the original untouched when the
  provider rejects the move."

Verification:
  Exact commands, probes, artifacts, and environment checks that prove the
  outcome. Name the tests. Name the flows. Name the target environment if
  deploy truth matters.

Constraints:
  Behaviors that must not regress; unrelated WIP that stays untouched; no
  speculative refactors; no unauthorized external mutations.

Boundaries:
  Reference this park's boundary.json plus the hand-added runtime surface and
  DO NOT TOUCH paths.

Stop when:
  A user-owned destructive/product decision is required; a definitive
  auth/quota/permission barrier denies a required check; target-environment
  truth cannot be inspected; or three materially different attempts hit the
  same external wall.
```

## Final handoff

```text
PARKED: <feature>                                    VERDICT: <DONE|BLOCKED|STOPPED|PAUSED>
Park: <park-id>               Tier: <QUICK|STANDARD|DEEP>
Boundary: <one line + pointer to the park's boundary.json>
Contract: <proved | which clause failed and why>

Baseline -> final:
  B1 <cmd>: <before> -> <after>     (fingerprint: <head short-sha>, tree <clean|dirty-hash>)
  ...

Predictions: <total> funded / <n> disproved / <n> fixed-verified / <n> blocked / <n> accepted-risk
Unfunded hypotheses: <n> (listed in unfunded.json — honestly unprobed)
Concurrent parks: <none | ids sharing files, and how the overlap was handled>

Fixed: <one line per fix: PRED-id, cause, smallest patch, regression probe>
Open P0/P1: <none | list — implies verdict is not DONE>
Ship blockers: <none | list>
External unknowns: <claims not verified in the target environment, stated plainly>
Leftovers: <P3s and observations, not fixed by design>
Commit/push/deploy status: <exact state; nothing pushed/deployed without authorization>
```

Keep the handoff short — the park's ledgers did the long work, and
`park.py judgepack` bundles them for anyone who wants the evidence.
