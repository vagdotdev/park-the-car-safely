---
name: park-the-car-safely
description: >-
  QA / safety check-loop after the user drove a feature themselves.
  Discover scope, baseline tests+typecheck, severity-ranked predict (P0–P3),
  surgical fix of confirmed issues only, retest, exhaustive QA, blunt ship report.
  Use when the user says "park the car safely", "park my car safely",
  "driver, park the car safely", "do the checks", "checking loop", or that they
  implemented something and want the chauffeur QA pass — not a re-drive.
---

# Park the car safely

User drove. You park. **Do not re-implement the feature** unless predict finds a real break.

## Triggers (load this skill)

- "Park the car safely" / "Park my car safely" / "Driver, park the car safely"
- "I drove today — you do the checks / loop"
- Same intent in other words (checking loop, safety pass after their drive)

## Division of labor

| Role | Who |
|------|-----|
| Major feature / drive | User (or prior build agent) |
| QA chauffeur | You — tests → predict → fix confirmed → exhaustive |

No push unless they ask. No "while we're here" refactors.

## Sequence (always)

Copy and track:

```
Park progress:
- [ ] 1. Discover scope
- [ ] 2. Ignore unrelated dirty WIP
- [ ] 3. Baseline (you run tests + typecheck)
- [ ] 4. Predict P0–P3 (read-only)
- [ ] 5. Fix confirmed P0/P1 only
- [ ] 6. Retest + typecheck yourself
- [ ] 7. Exhaustive QA (read-only)
- [ ] 8. Blunt report (fixed · leftovers · ship blockers)
```

### 1. Discover scope

```bash
git status -sb
git diff --stat
git log -5 --oneline
# + search for the named feature if they named one
```

Build an explicit **NEW + MODIFIED** file list for the parked work.

### 2. Ignore unrelated dirty WIP

Mixed trees are normal. Scope tightly. Do not "fix" adjacent WIP unless they said park everything.

### 3. Baseline yourself first

Run the project's relevant tests + typecheck **before** any predict/fix agent.

- Prefer the package scripts / test paths the repo already uses
- Record pass/fail counts
- Feed "already green" into predict so you don't thrash on false alarms

**Client-only / zero unit tests:** still typecheck; static-audit the surface; report green/yellow by path — don't invent a fake PASS matrix.

### 4. Predict (read-only)

Severity-ranked **P0–P3**. Confirmed-from-code vs speculative.

Include in the audit:
- Explicit file list (NEW / MOD)
- Baseline green note
- Project business rules you know (e.g. mutually exclusive roles, money soft-fail, seeds never outreach)
- Focus: races, auth/scoping, migrations-before-code, cron TTL, double fan-out, honesty of user-facing copy

**Output only** — no edits in this step.

Optional: spawn Cursor CLI for a second pair of eyes:

```bash
agent --print --trust --mode ask --model cursor-grok-4.5-high \
  --workspace <app-root> \
  "$(cat .park-predict-prompt.md)"
```

Write long prompts to a temp `.md`, `$(cat …)`, delete after. Prefer ask/plan mode for predict.

### 5. Fix confirmed only

- Only P0/P1 with concrete failure modes
- Surgical; explicit **DO NOT touch** for out-of-scope paths
- Re-run tests + typecheck after (don't trust self-report alone)

### 6–7. Retest + exhaustive QA

Exhaustive QA is **read-only**: overall PASS/FAIL, leftover P0/P1 only, ship checklist (migrations applied?, env, cron paths, ops honesty). No dual-role / speculative noise.

### 8. Report (blunt)

What fixed · leftovers · ship blockers. Short. No essay. No push unless asked.

## Prompt shapes

### Predict
Explicit files · baseline green · business rules · focus bullets · `Do NOT edit. P0–P3 only.`

### Fix
Confirmed issues + concrete directions · DO NOT touch list · retest · report fixed + leftover risks

### Exhaustive QA
`READ-ONLY` · PASS/FAIL · leftover P0/P1 · ship checklist

## Optional Cursor CLI

When `agent` is on PATH (`~/.local/bin/agent`):

| Pass | Flags |
|------|--------|
| Predict / exhaustive | `--print --trust --mode ask` |
| Fix | `--print --trust --yolo` |

Models: prefer a strong coding model; if hung empty ~2–3 min, kill and retry with a faster high-tier model (e.g. `cursor-grok-4.5-high`).

You may also park entirely in-session (read → baseline → predict → fix → QA) without CLI — same sequence.

## Domain checklists (load when relevant)

When parking notification / multi-channel send paths, see [notification-idempotency.md](notification-idempotency.md).

## Anti-patterns

- Re-driving the feature "cleaner"
- Fixing unrelated dirty files
- Claiming ship-ready when migrations aren't applied / remote
- Trusting an agent "done" without re-running tests yourself
- Pushing without an explicit ask
