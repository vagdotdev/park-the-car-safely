# Probes — turning predictions into verdicts

Prediction produces hypotheses; parking requires verdicts. The discipline:

```
No material prediction without a probe or an explicit unfunded disposition.
No confirmed defect without a regression signal.
No repair without retesting.
No completion without re-prediction.
```

Record every probe with `park.py probe add --pred PRED-003 --level unit
--setup "..." --cmd "..." --expect-pass "..." --expect-fail "..."` and close
it with `park.py probe close <id> --observed "..." --verdict <verdict>`.
Writing expected-pass AND expected-fail evidence *before* running is what
separates a probe from a demo: if you can't say what failure would look like,
the probe can't falsify anything.

Verdicts: **disproved** (valid probe showed the invariant holds),
**confirmed** (failure reproduced or code evidence decisive),
**inconclusive** (setup/tool/environment couldn't distinguish — prediction
stays open), **blocked-external**. Never silently promote inconclusive to
disproved; that is the single most common way parks lie.

## Choose the cheapest probe that can actually falsify

Cheap is only good when it can prove you wrong. Escalate levels only when
the cheaper level structurally cannot reach the invariant.

**Level 1 — static trace.** Read the exact code path and quote the lines.
Decisive for missing checks, fail-open defaults, absent files (negative
space), schema/type drift. Recipe: trace one identifier from entry to
persistence; quote every trust decision; diff declared types against DB
constraints.

**Level 2 — focused unit test.** One test, one invariant, hostile input.
Recipe: call the function with the other tenant's ID / a negative amount /
an empty list / a duplicate key and assert the invariant, not the
implementation's current behavior.

**Level 3 — API / integration probe.** Exercise the real route with real
serialization. Recipes: replay the same webhook payload twice and count side
effects; send a valid session's token against another tenant's resource id;
POST with fields the UI never sends (disabled controls, extra keys, changed
price).

**Level 4 — user-journey probe.** Browser or end-to-end flow, including the
back button, refresh mid-flow, resume links, and double-click on submit.
Only when the claim lives in the journey (hydration, navigation state,
optimistic UI honesty).

**Level 5 — concurrency / fault injection.** Two workers, one resource:
fire the same request from two coroutines/processes and assert one winner;
kill the process between persist and acknowledge; inject a provider timeout
after acceptance. Recipe skeleton (python): run the handler in
`ThreadPoolExecutor(2)`, barrier both at entry, assert exactly one durable
effect.

**Level 6 — target-environment verification.** Config, credentials, flags,
migrations, and quotas in the environment the claim is about. A local pass
proves nothing about production mappings; either verify there (with
authorization) or record the claim as an external unknown — never as green.

## Rules of engagement

- Do not write a test that restates the implementation; test the invariant.
- Capture raw evidence (command + output tail) in the probe record; the gate
  and judge read the ledger, not your recollection.
- A probe that required weakening an assertion, skipping a check, or editing
  the test command to pass is a confession, not a pass.
- When a fix lands, the prediction's probe becomes its regression signal:
  rerun it plus every probe on dependent paths, then close the prediction
  `fixed-verified` with the rerun evidence.
