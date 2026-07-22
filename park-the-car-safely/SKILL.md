---
name: park-the-car-safely
description: >-
  QA / safety check-loop after the user drove a feature themselves.
  Discover scope, baseline tests+typecheck, severity-ranked predict (P0–P3),
  surgical fix of confirmed issues only, continuous retest loop, exhaustive QA,
  blunt ship report. Use when the user says "park the car safely",
  "park my car safely", "driver, park the car safely", "do the checks",
  "checking loop", or that they implemented something and want the chauffeur
  QA pass — not a re-drive.
---

# Park the car safely

User drove. You park. **Do not re-implement the feature** unless predict finds a real break.

The blood of this skill is not the checklist labels — it is:

1. **Predict** — a real read-only audit with P0–P3, confirmed-from-code vs speculative
2. **Continuous testing** — you run tests/typecheck before predict, after every fix, and again before ship report; failures feed the next fix; never trust an agent’s “green”

## Triggers (load this skill)

- "Park the car safely" / "Park my car safely" / "Driver, park the car safely"
- "I drove today — you do the checks / loop"
- Same intent in other words (checking loop, safety pass after their drive)

## Division of labor

| Role | Who |
|------|-----|
| Major feature / drive | User (or prior build agent) |
| QA chauffeur | You — baseline → predict → fix confirmed → **retest loop** → exhaustive |

No push unless they ask. No "while we're here" refactors.

## Sequence (always)

Copy and track:

```
Park progress:
- [ ] 1. Discover scope
- [ ] 2. Ignore unrelated dirty WIP
- [ ] 3. Baseline (YOU run tests + typecheck) → record numbers
- [ ] 4. Predict P0–P3 (read-only) → write the audit
- [ ] 5. Fix confirmed P0/P1 only
- [ ] 6. Continuous test loop (YOU re-run; fail → fix → re-run)
- [ ] 7. Exhaustive QA (read-only)
- [ ] 8. Blunt report (fixed · leftovers · ship blockers)
```

---

### 1. Discover scope

```bash
git status -sb
git diff --stat
git log -5 --oneline
# + search for the named feature if they named one
```

Build an explicit **NEW + MODIFIED** file list for the parked work. That list is the park boundary.

### 2. Ignore unrelated dirty WIP

Mixed trees are normal. Scope tightly. Do not "fix" adjacent WIP unless they said park everything. Keep an explicit **DO NOT touch** list.

### 3. Baseline (you, before any predict/fix)

Run the project's relevant tests + typecheck **before** predict.

- Prefer package scripts / test paths the repo already uses
- Record: command(s), pass/fail counts, typecheck result
- Feed “already green: N pass / typecheck clean” into predict so you don’t thrash on false alarms
- If baseline is red on the parked surface: fix or isolate that first — don’t predict on a broken floor

**Client-only / zero unit tests:** still typecheck; static-audit the surface; report green/yellow by path — don’t invent a fake PASS matrix.

---

### 4. Predict (read-only) — required, not optional

This is a full audit pass. **Output only. No edits.**

#### Severity ladder

| Sev | Meaning | Fix in park? |
|-----|---------|--------------|
| **P0** | Ship blocker: wrong money, auth/scoping hole, data loss/corruption, silent fail-open on a safety gate, “works” only because tests never touch it | Yes — must address or explicitly block ship |
| **P1** | Confirmed break with a concrete failure mode (stale UI after mutation, race, migration missing → soft-fail, double fan-out) | Yes — surgical |
| **P2** | Real issue, non-blocking / edge / intentional soft-fail with ops note | Usually no — leftover |
| **P3** | Missing tests, polish, naming, dead paths that don’t bite yet | No |

#### Confirmed vs speculative

Every finding must be tagged:

- **confirmed-from-code** — you can point at the line/path and state the failure mode
- **speculative** — plausible but not proven (remote env, unapplied migration, timing). Do **not** fix speculative alone; call it out as leftover / ship checklist

Ignore noise that the project’s business rules already kill (e.g. “dual-role account” when roles are mutually exclusive).

#### What the audit must include

1. Explicit file list (NEW / MOD) + park boundary
2. Baseline green note (commands + counts)
3. Project business rules you know (auth model, money soft-fail, seeds never outreach, etc.)
4. Focus scan (at least check these where relevant):
   - races / claim-before-send / TTL vs late callbacks
   - auth + tenancy / scoping
   - migrations-before-code (CHECK constraints, new columns)
   - cron `maxDuration`, double fan-out
   - fail-open safety gates (Rx, payments, permissions)
   - honesty of user-facing copy vs actual behavior
5. Severity-ranked list P0→P3 with evidence
6. Explicit **non-findings** for areas you checked and cleared (stops fake confidence)

#### Predict output shape (use this)

```markdown
## Park predict — <feature>

**Scope:** NEW … / MOD …
**Baseline:** <cmd> → N pass; typecheck <clean|fail>
**Verdict:** <one line>

### P0
1. **<title>** — confirmed-from-code | speculative
   Evidence: `path` … Failure mode: …

### P1
…

### P2 / P3
…

### Explicit non-findings
| Area | Result |
|------|--------|
| Auth on … | checked — … |
```

#### Predict prompt template (in-session or CLI)

Write to a temp file, then run — do not skip the file list or baseline note:

```markdown
# Park predict (READ-ONLY)

Do NOT edit files. Output severity-ranked P0–P3 only.

## Scope (NEW / MOD)
- …

## Baseline (already run — trust these numbers)
- tests: …
- typecheck: …

## Business rules
- …

## Focus
- races, auth/scoping, migrations-before-code, cron TTL, double fan-out,
  fail-open gates, copy honesty

## Required output
- P0–P3 with confirmed-from-code vs speculative
- concrete failure modes
- explicit non-findings table
```

Optional second pair of eyes via Cursor CLI (`agent` on PATH):

```bash
agent --print --trust --mode ask --model <strong-coding-model> \
  --workspace <app-root> \
  "$(cat .park-predict-prompt.md)"
```

If the agent hangs empty ~2–3 min → kill → retry with a faster high-tier model. Delete the temp prompt after.

---

### 5. Fix confirmed only

- Only **P0/P1** with **confirmed-from-code** and a concrete failure mode
- Surgical; paste the **DO NOT touch** list into every fix pass
- Prefer smallest patch that closes the failure mode
- Do not “clean up” or re-drive the feature

#### Fix prompt shape

```markdown
# Park fix

Address ONLY these confirmed issues:
1. … (concrete direction)
2. …

DO NOT touch:
- …

After edits: run <same baseline test cmds> + typecheck.
Report: fixed · leftover risks. No drive-by refactors.
```

---

### 6. Continuous testing loop (required)

This is not a single retest at the end. **You** own the loop:

```
baseline (step 3)
  → predict
  → fix batch
  → YOU run same tests + typecheck
       ↓ fail?
       → feed failures into next fix (still surgical, still in scope)
       → YOU re-run again
       → repeat until green or blocked
  → only then exhaustive QA
```

Rules:

- Same commands as baseline when possible (don’t silently change the suite)
- Record pass/fail after **every** loop iteration
- Agent says “tests passed” → **ignore until you re-run**
- Agent says “files written” → verify on disk (`git diff` / read) before trusting
- If a fix breaks unrelated tests outside the park boundary: stop, report, don’t expand scope unless user says so
- Typecheck is part of the loop, not a nice-to-have

**Stop conditions:** green on parked surface, or a ship blocker you cannot fix without product/ops (missing migration remote, missing creds) — then report as blocker, don’t fake green.

---

### 7. Exhaustive QA (read-only)

After the test loop is green (or honestly blocked):

- `READ-ONLY` — no edits
- Overall **PASS / FAIL** on the parked surface
- Leftover **P0/P1 only** (anything still open)
- Ship checklist: migrations applied on target env? env vars present **and** valid? cron routes? ops honesty (never claim delivered on stub/401)?
- No dual-role / speculative noise

#### Exhaustive prompt shape

```markdown
# Exhaustive QA (READ-ONLY)

NO edits. Parked files: …
Baseline/retest: … (numbers)

Return:
- PASS or FAIL
- leftover P0/P1 only
- ship checklist (migrations, env, cron, ops honesty)
```

---

### 8. Report (blunt)

Short. No essay. No push unless asked.

```text
Parked: <feature>
Baseline → final: <N pass> / typecheck <ok>
Fixed: …
Leftovers: …
Ship blockers: … (or none)
```

---

## Optional Cursor CLI

When `agent` is on PATH (`~/.local/bin/agent`):

| Pass | Flags |
|------|--------|
| Predict / exhaustive | `--print --trust --mode ask` |
| Fix | `--print --trust --yolo` |

You may also park entirely in-session (read → baseline → predict → fix → continuous retest → QA) without CLI — **same sequence, same loop**.

Long prompts → temp `.md` + `$(cat …)`. Never giant nested shell heredocs.

## Domain checklists (load when relevant)

When parking notification / multi-channel send paths, see [notification-idempotency.md](notification-idempotency.md).

## Anti-patterns

- Skipping predict because “it looks fine”
- One baseline at the start and no retest after fixes
- Trusting an agent “done” / “tests passed” without re-running yourself
- Re-driving the feature “cleaner”
- Fixing unrelated dirty files
- Claiming ship-ready when migrations aren’t applied / remote
- Fixing speculative P2/P3 noise to look busy
- Pushing without an explicit ask
