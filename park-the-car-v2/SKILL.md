---
name: park-the-car-v2
description: >-
  Evidence-driven post-implementation QA and ship-readiness loop with lateral
  failure prediction and a mechanical completion gate. Use this skill whenever
  the user asks to verify, QA, harden, or ship-check work that was just built:
  "park the car safely", "I drove, you park", "review my changes before I
  ship", "is this safe to ship", "do a QA pass", "check my work", "verify this
  feature", "find what I missed", "attack this until it's safe", or any request
  for a post-build verification, pre-merge review, or exhaustive safety pass.
  Trigger it even if the user doesn't say "park" — any ship-readiness or
  post-implementation verification request qualifies. Establishes a completion
  contract, scopes a hunk-level boundary, baselines with fingerprinted
  evidence, generates failure predictions via lateral-thinking operators,
  probes every material prediction, repairs in severity waves, and refuses
  DONE until a mechanical gate and an independent judge both pass.
---

# Park the car v2

The user already drove. You are the closer. Your job is to attack the finished
surface until its important claims either survive evidence or break in a way
you can reproduce and repair. Be aggressive about uncertainty, conservative
about edits, and honest about everything.

Every material prediction ends in exactly one state — **disproved**,
**fixed-verified**, **blocked-external**, or **accepted-risk** (by the user,
never by you). "Probably fine" and "tests passed earlier" are not states.

## Why the tooling exists

Working memory dies at context compaction; disk does not. Vibes-based
completion judging flatters its author; a mechanical gate does not. Every
instruction in this skill that produces state runs through
`scripts/park.py`, which persists everything to a `.park/` directory in the
repo. Use the script, not ad-hoc notes — the gate at the end reads the
artifacts, and anything not recorded there does not count as evidence.

```bash
PARK="python3 <skill-dir>/scripts/park.py"   # resolve <skill-dir> once
$PARK init          # create .park/ state + contract stub
$PARK triage        # diff stats + risk scan -> tier + budgets
$PARK boundary      # hunk-level NEW/MOD/risk-tags/negative-space
$PARK baseline B1 -- npm test        # fingerprinted evidence ledger
$PARK lateral       # randomized lateral-thinking battery for prediction
$PARK pred add ...  # falsifiable prediction records
$PARK probe ...     # probes bound to predictions
$PARK status        # render current PARK STATE
$PARK gate          # mechanical completion gate (exit 1 = not done)
$PARK judgepack     # bundle for an independent fresh-context judge
```

Run `$PARK --help` and `$PARK <cmd> --help` for exact flags.

## Non-negotiable rules

1. **Boundary before testing, prediction before editing.** Phases 1–4 are
   read-only. No "tiny fix while I'm here."
2. **Run the baseline yourself** through `$PARK baseline`. Prior turns, helper
   agents, and memory of green do not count — only fingerprinted evidence
   bound to the current HEAD.
3. **A list of worries is not an audit.** Every material (P0–P2) prediction
   gets a probe or an explicit funded/unfunded disposition.
4. **Fix evidence, not imagination.** Retest with the same baseline commands
   after every fix wave; re-predict after fixes, because repairs move the
   risk surface.
5. **Never hide red.** Classify every failure as caused, pre-existing,
   environmental, or unknown. Feature-level green never conceals
   branch-level red.
6. **Inconclusive is not disproved.** A probe whose setup failed leaves the
   prediction open.
7. **No push, deploy, migration, live message, or production mutation without
   explicit user authorization.** Scope stays inside the boundary; the
   aggression points at failure modes, never sideways at unrelated code.
8. **The gate is the referee.** You may not declare DONE while
   `$PARK gate` fails, and you may not edit ledgers to make it pass —
   closing a prediction requires a verdict plus evidence.

## Phase 0 — Arm: contract and triage

`$PARK init` creates `.park/contract.md`. Fill every field concretely —
outcome, verification commands, constraints, boundaries, stop conditions.
"Tests pass" is not a contract; name the tests, the flows, and the target
environment if deploy truth matters.

`$PARK triage` reads the diff and risk surface and assigns a tier with hard
budgets:

| Tier | When | Budget (max funded predictions / probes / lateral moves) |
|---|---|---|
| QUICK | small diff, no trust/money/state boundaries touched | 6 / 5 / 4 |
| STANDARD | typical feature | 14 / 12 / 7 |
| DEEP | auth, tenancy, money, migrations, concurrency, or irreversible effects in scope | 30 / 24 / 12 |

Budgets exist so a one-line CSS fix doesn't get a ten-phase siege and a
payments refactor doesn't get a happy-path skim. You may argue the tier up or
down with reasons (`$PARK triage --set DEEP --why "..."`), but never silently.
Predictions beyond budget go to the **unfunded list** — visible in the
handoff, honestly unprobed — instead of being quietly dropped.

## Phase 1 — Boundary

`$PARK boundary` parses git into NEW files, MOD files with exact hunks,
untracked additions, and per-file risk tags. Extend it by hand where git can't
see: the **runtime surface** (callers, jobs, storage, flags, integrations, UI
paths that make the feature real) and **DO NOT TOUCH** (unrelated dirty WIP).
A one-line caller change can activate a large payment path; a dirty file may
hold one parked hunk and fifty unrelated ones — scope at hunk level. If two
boundaries would produce materially different work, ask the user one focused
question; otherwise take the narrowest coherent boundary and state it.

## Phase 2 — Baseline

Use the project's own test culture. Record every command through
`$PARK baseline <id> -- <command>`: it captures exit code, output tail, HEAD
sha, and a dirty-tree hash, so later phases can prove evidence currency.
Minimum: the narrowest meaningful tests for the parked surface, the project's
authoritative type/static check (record N/A with a reason only if none
exists), lint if the project uses it, and one runtime probe when static tests
cannot reach the user journey. If baseline is red: classify each failure
(parked / pre-existing / environmental / unknown), convert parked failures
into confirmed predictions, and do not repair anything until Phase 4 is done.
A test that never reaches the feature is not coverage.

## Phase 3 — Model and invariants

Write the feature as a causal graph — trigger → input → auth → validation →
domain decision → persistence → external effect → callback/retry → visible
state → recovery — and extract invariants as falsifiable sentences
("a payment callback creates at most one confirmed order per provider
transaction", not "payments should be safe"). Every P0/P1 prediction must
threaten a named invariant; invariants are what turn brainstorming into
targeting. Details and per-edge questions: `references/LENSES.md`.

## Phase 4 — Lateral predict (the signature phase)

Read `references/LATERAL.md` now — it is mandatory for every non-QUICK park.

Ordinary prediction finds the bugs the author would have found. Lateral
prediction finds the ones nobody in the codebase's mental rut can see. Run
`$PARK lateral`: it deals you a randomized hand of divergence operators
(Invert, Rotate the Actor, Shift Time, Negative Space, Succeed Too Hard,
Random Entry, Money Walks, and more) plus random-entry seed words. The
randomness is deliberate — it forces different attack geometry on every park
and keeps you out of your own training-data grooves.

Divergence first: generate freely under each dealt operator, wild ideas
welcome, no self-censoring, quantity over polish. Then converge hard: every
surviving idea must become a falsifiable record via
`$PARK pred add --sev P1 --claim "..." --invariant INV-02 --move actor
--evidence-tag supported --trigger "..." --expected "..."` — or be discarded.
Fund the best by score (severity × likelihood × cheapness-to-probe) up to the
tier budget; the rest go to unfunded. Evidence tags are honest:
`code-confirmed` (you can point at the line), `supported` (mechanism plausible
in this code), `speculative` (pure lateral leap — cheap probes only).

## Phase 5 — Probe

Read `references/PROBES.md` for level selection and ready-made recipes.
For each funded prediction: choose the cheapest probe that can actually
falsify it, write expected-pass and expected-fail evidence **before** running,
run it, record via `$PARK probe add/close`. Order: static trace → focused
unit test → API/integration → user-journey → concurrency/fault-injection →
target-environment. Test the invariant, not the implementation. A probe
whose setup failed is inconclusive and stays open.

## Phase 6 — Repair in severity waves

Fix only what evidence confirmed. Wave A: P0 (safety, money, auth/tenancy,
data loss, fail-open). Wave B: P1 (normal-path breaks, races, duplicate side
effects, unrecoverable state). Wave C: confirmed material P2 — fixed,
blocked, or explicitly user-accepted. P3: report, don't polish. Per wave:
smallest causal patch, regression probe first when practical, inspect the
diff, rerun the same baseline commands, rerun the prediction's probe and
dependent-path probes, then `$PARK pred close <id> --verdict fixed-verified
--evidence "..."`. If a fix changes a shared invariant, reopen every
prediction that depended on the old behavior. If the user accepts an open
P0/P1, close it `--verdict accepted-risk --user-accepted` — the park ends
STOPPED, never ship-ready.

## Phase 7 — Loop

predict → probe → confirm → fix → baseline retest → targeted retest →
re-predict → next open prediction. A red retest is the next active input, not
bookkeeping. Background long CI/builds and wait on a real completion signal;
don't burn turns saying "still running", don't abandon them either.

## Phase 8 — Gate, then judge

`$PARK gate` mechanically verifies: contract filled, boundary drawn, baseline
evidence current against HEAD, every material prediction terminally
dispositioned, no open probes on funded predictions, budgets respected. While
it fails, you continue — its reasons are your work queue. When it passes,
run `$PARK judgepack` and hand the bundle to the most independent reviewer
available (fresh subagent, or yourself after an explicit read-only context
switch) following `references/JUDGE.md`. The judge tries to reject the
completion claim; the gate checks mechanics, the judge checks meaning.

## Phase 9 — Handoff

Rerun core baselines one final time so evidence is current, then report using
the template in `references/TEMPLATES.md`: verdict (DONE / BLOCKED / STOPPED
/ PAUSED — anything else means continue), boundary, baseline→final delta,
prediction ledger totals, fixes, open risk, unfunded hypotheses, external
unknowns, and commit/push status. Short report; the ledger did the long work.
BLOCKED is reserved for definitive external barriers — hard is not blocked,
slow is not blocked, a failing first attempt is not blocked.

## Automatic failure conditions

You failed the park if you: skipped contract or boundary; edited before
predicting; listed risks without probing; trusted another agent's green
without raw evidence; changed a test command to manufacture green; called
inconclusive a pass; fixed speculative noise while a confirmed P1 sat open;
hid branch red behind feature green; bypassed or hand-edited the gate; or
pushed/deployed/messaged externally without authorization.

No green by omission. No safety by adjective. Park the actual car.
