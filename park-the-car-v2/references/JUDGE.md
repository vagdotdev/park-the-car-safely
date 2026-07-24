# Completion: the gate, then the judge

Completion has two layers because self-review fails in two different ways.
The **gate** (`park.py gate`) is mechanical and catches omission: unprobed
material predictions, stale evidence, missing dispositions. The **judge** is
semantic and catches self-deception: probes that couldn't have failed,
contracts quietly narrowed, green that doesn't mean what the report implies.
A park is done only when both pass.

## The gate

Run `park.py gate`. It exits non-zero with a reason list while any of these
hold: contract unfilled; boundary missing; no baseline, or the latest
baseline's HEAD/dirty fingerprint doesn't match the working tree (evidence
is stale — rerun baselines); any funded P0–P2 prediction without a terminal
disposition; any P0/P1 closed as accepted-risk without the user-accepted
flag; open probes on funded predictions; budget overflow not routed to the
unfunded list. Treat the reason list as the work queue. Hand-editing
`.park/*.json` to satisfy the gate is an automatic park failure.

## The judge

When the gate passes, produce `park.py judgepack` — a single bundle of
contract, boundary, ledgers, and final fingerprinted baselines — and give it
to the most independent reviewer available, in this order of preference: a
fresh subagent with no memory of writing the fixes; a fresh context; or
yourself after an explicit switch to read-only adversarial mode. Instruct
the judge to **try to reject the completion claim**, not to review generally.

The judge asks:

1. Does current evidence prove every contract requirement — commands rerun
   at the final HEAD, not remembered from earlier?
2. Could each closing probe actually have failed? A probe with no plausible
   failure output is a demo; reopen its prediction.
3. Is every supported user path exercised or explicitly out of scope — and
   did "out of scope" grow during the park?
4. Does any P0/P1 hide inside "external", "environmental", or "flaky"?
5. Did fixes regress an adjacent path or violate a constraint? Check the
   final diff against DO-NOT-TOUCH.
6. Is branch-wide red being presented as parked-surface green?
7. Do the unfunded list and external unknowns appear in the handoff, or did
   inconvenient ideas evaporate?

## Verdicts

- **DONE** — contract proved with current evidence; P0/P1 all disproved or
  fixed-verified; P2 disproved, fixed-verified, or user-accepted.
- **STOPPED** — the user accepted open P0/P1 risk. Never described as
  ship-ready, in any phrasing.
- **BLOCKED** — a definitive external or user-owned barrier: a destructive
  or product decision only the user can make; permissions/quota/credentials
  definitively denying a required check; target-environment truth
  unreachable; or three materially different attempts hitting the same
  external wall. Record attempts, evidence, owner, and the exact unblock
  condition. Hard is not blocked; slow is not blocked; a failing first
  attempt is not blocked.
- **PAUSED** — user- or platform-required pause, or no new tactic exists;
  state preserved in `.park/` with the exact resume point.
- **WAIT** — a real background verification barrier (CI, deploy) is active
  with a concrete completion signal being awaited.

Anything else means continue.
