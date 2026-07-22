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

Someone already drove the feature. Your job is not to rebuild it prettier. Your job is to **park it**: find what can break, fix only what is confirmed and dangerous, prove the suite still holds, and tell the human the truth about ship readiness.

The blood of this skill is two things that most agents fake:

1. **Predict** — a real read-only audit. You read the parked code, name failure modes, rank them P0–P3, and separate what the code proves from what you are guessing about prod.
2. **Continuous testing** — you personally run tests and typecheck before predict, after every fix batch, and again before you speak the ship report. If something fails, that failure becomes the next fix input. You never accept “tests passed” from another agent (or from yourself in a previous turn) without re-running.

If you skip either of those, you are not parking. You are vibing.

---

## When to load this skill

Load it when the human (or the chat context) means:

- “Park the car safely” / “Park my car safely” / “Driver, park the car safely”
- “I drove today — you do the checks / loop”
- “Do the checking loop” / “safety pass after my drive”
- Any phrasing that says: *the feature exists; now chauffeur the QA, don’t re-drive*

Do **not** load this as an excuse to redesign the feature. If predict finds a real break, you may patch that break surgically. You may not rewrite the architecture “while you’re here.”

---

## Division of labor

| Role | Who | Allowed to do |
|------|-----|----------------|
| Drive | User or prior build agent | Invent the feature, large design choices |
| Park (you) | QA chauffeur | Scope, baseline, predict, fix confirmed P0/P1, retest loop, exhaustive, blunt report |

Hard rules for the chauffeur:

- No push unless they explicitly ask.
- No drive-by refactors, renames, “cleanup,” or formatting sweeps.
- No expanding into adjacent dirty WIP unless they said “park everything.”
- No claiming ship-ready when migrations, env, or cron are unverified on the target environment.

---

## The sequence you always run

Track this openly in your working notes so you don’t skip steps under pressure:

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

Do them in order. Predicting before a baseline is how you invent ghost bugs. Fixing before predict is how you re-drive. Exhaustive QA before the test loop is green is theater.

---

## 1. Discover scope — draw the boundary first

Parking without a file list is how you “fix” the wrong feature.

Start with git, then search:

```bash
git status -sb
git diff --stat
git log -5 --oneline
```

If they named a feature (“pharmacy Rx gate”, “follow-up SMS”, “admin ship button”), search for those symbols and routes. Build an explicit list:

- **NEW** — files that exist because of this drive
- **MOD** — files changed for this drive
- **OUT OF SCOPE** — dirty or nearby files you will not touch

That NEW+MOD list is the **park boundary**. Every later prompt (predict, fix, exhaustive) should paste it. If a finding lives outside the boundary, it is leftover commentary unless it is a true ship blocker caused by the parked work (say so explicitly).

How to think while scoping:

- Prefer the smallest coherent surface that makes the feature real (API + caller + migration + UI that completes the path).
- If the tree is a mess of two features, ask only if truly ambiguous. Otherwise pick the named one and put the rest on the DO NOT touch list.
- Recent commits help when the working tree is noisy: `git log -5 --oneline` often shows what they thought they shipped.

Write the boundary down before you run tests. Example:

```text
Park boundary:
NEW: src/app/api/foo/route.ts, src/lib/foo/gate.ts
MOD: src/components/FooActions.tsx, supabase/migrations/107_....sql
DO NOT touch: src/lib/pharmacy-core/** (unrelated WIP)
```

---

## 2. Ignore unrelated dirty WIP — mixed trees are normal

Real repos are dirty. Another feature half-landed next to yours is not an invitation.

- Do not “improve” adjacent files to make the park feel complete.
- Do not run formatter/linter autofix across the repo.
- Do not merge, rebase, or push to clean the story.
- Keep the DO NOT touch list in every fix prompt so a helper agent cannot wander.

If they literally say “park everything” or “the whole branch,” expand the boundary and say so in the report. Otherwise stay narrow.

---

## 3. Baseline — you run the suite before anyone predicts

Baseline is how you stop false alarms. If the suite is already red, predict will drown in noise. If it is green, predict must explain how production can still die.

### What to run

Use what the project already uses. Do not invent a parallel test culture.

Typical patterns:

- Targeted unit tests for the parked libs: e.g. `npx tsx --test path/to/relevant.test.ts`
- Package scripts: `npm test`, `pnpm test`, `npm run typecheck`, `npm run lint` when that is the house standard
- Prefer the narrowest suite that still covers the parked surface, plus typecheck always

### What to record

Write the actual numbers into your notes and into the predict prompt:

```text
Baseline:
- cmd: npx tsx --test src/lib/foo/*.test.ts → 47 pass / 0 fail
- cmd: npm run typecheck → clean
```

Those numbers travel with you. After fixes you will re-run the **same** commands and compare.

### If baseline is red on the parked surface

Do not leap into a speculative predict essay. Either:

1. the red is caused by the parked work → treat it as the first confirmed break and fix/retest before a full predict, or
2. the red is pre-existing outside the boundary → note it, keep it out of your “already green” claim, and still predict the parked surface carefully

Never invent a fake PASS matrix to look professional.

### Client-only / zero unit tests

Some drives are UI + browser API with no tests. You still park, but honestly:

1. Run typecheck (and targeted lint if useful).
2. Static-audit the hook/components yourself: feature detect, cleanup on unmount, append vs overwrite, stop-on-send, unsupported paths.
3. Report by surface: main path green / secondary path yellow, with concrete edge bugs — not a fake N/N unit matrix.
4. Still do a lightweight predict: what fails for a real user, what hydration/lint traps exist, what duplicate weaker implementations live nearby.
5. Do not re-drive shared hooks “for consistency” unless they asked for that fix.

---

## 4. Predict — the real audit (read-only, required)

Predict is not a vibe check. It is a structured hunt for failure modes in the parked code. **No edits in this step.** If you catch yourself patching mid-predict, stop. Write the finding instead.

You can predict in-session (read the files yourself) or spawn a read-only helper agent. Either way, the **output artifact** should look the same: severity-ranked, evidenced, tagged confirmed vs speculative.

### How to actually do a predict

1. Paste the park boundary and baseline numbers at the top of your working doc.
2. List business rules you already know for this product (auth model, money soft-fail, seeds never get outreach, roles mutually exclusive, etc.). These kill false positives.
3. Read every NEW/MOD file that sits on a runtime path — not just the pretty UI file. Follow the click/API/cron to the storage write and back.
4. For each risky spot, ask: “What input or race makes this lie?” Prefer concrete traces over adjectives.
5. Rank findings. Tag each one. Write non-findings for areas you checked and cleared.

Good predict energy: “If `items` fails to parse, `orderRequiresPrescription` returns false, so paid Rx orders skip the review queue and ship unlocks.”

Bad predict energy: “Maybe auth is wrong somewhere” with no path.

### Severity ladder (use judgment, not vibes)

| Sev | Meaning | Typical examples | Fix during park? |
|-----|---------|------------------|------------------|
| **P0** | Ship blocker or safety lie | Wrong money; auth/tenancy hole; data loss; fail-open safety gate (Rx/permission/payment); “secure” path that defaults false when data missing | Yes — fix or hard-block ship |
| **P1** | Confirmed break with a clear repro shape | Stale UI after server mutation (no refresh); claim-before-send mute; migration missing → soft-fail oversell; double SMS; late callback resurrects cancelled order | Yes — surgical |
| **P2** | Real, non-blocking, or intentional soft-fail with ops note | Edge admin path; hold not released until bill; copy slightly misleading | Usually leftover |
| **P3** | Hygiene | Missing unit tests, naming, dead code, polish | No |

When torn between P0 and P1: if a normal successful user path can bypass a safety gate or lose money/data, it is P0.

### Confirmed-from-code vs speculative

Every finding needs a tag:

- **confirmed-from-code** — you can cite the file/function and state the failure mode without guessing about prod. Fix candidates live here (P0/P1 only).
- **speculative** — depends on remote state you did not verify (migration not applied on Vercel, cron secret missing in that env, provider keys present locally but not in deploy). Put these on the ship checklist. Do not “fix” them by rewriting code you cannot validate.

Example of honest tagging:

- “Fail-open Rx when parse returns []” → confirmed-from-code (the helper returns false).
- “Migration 107 might be missing in prod” → speculative until someone checks the remote DB — still a ship checklist item if the code soft-fails on insert errors.

### Focus lenses (walk these when relevant)

You do not need every lens every time. You do need to consciously skip a lens, not forget it.

- **Races & idempotency** — mark-after-send vs claim-before-send; TTL cron vs late payment callback; double fan-out from cron + sync.
- **Auth & tenancy** — can clinic A act on clinic B’s row? Can a patient hit an admin action? Is the check only in UI?
- **Migrations before code** — new columns, CHECKs, enums. Does TypeScript allow a value the DB will reject (or the reverse)?
- **Fail-open gates** — missing flag → treat as safe? Unknown → allow? That pattern is how Rx/payment/permission bugs ship.
- **Cron & duration** — batch claimed then killed mid-run by `maxDuration`.
- **Join shape bugs** — Supabase/PostgREST returning object `|` array; phone silently undefined; “works in the happy fixture.”
- **Copy honesty** — UI says “delivered” / “verified” / “reserved” when the code only attempted or soft-failed.
- **Money & holds** — initiate vs callback consistency; free path vs paid path asymmetry; holds that never release.

When parking notification / multi-channel sends, also load [notification-idempotency.md](notification-idempotency.md).

### Predict output shape (always produce this)

```markdown
## Park predict — <feature>

**Scope:** NEW … / MOD …
**Baseline:** <cmd> → N pass; typecheck <clean|fail>
**Verdict:** <one honest line>

### P0
1. **<title>** — confirmed-from-code
   Evidence: `path:symbol` …
   Failure mode: …

### P1
…

### P2
…

### P3
…

### Explicit non-findings
| Area | Result |
|------|--------|
| Auth on admin actions | requireX on page + server action — ok |
| Clinic scoping | clinic_id check before mutate — ok |
```

Non-findings matter. They prove you looked. Without them, a short “no P0” report is indistinguishable from laziness.

### Predict prompt template (for a helper agent)

Write long prompts to a temp markdown file in the project, then pass them with `$(cat …)`. Do not trust giant nested shell heredocs with apostrophes.

```markdown
# Park predict (READ-ONLY)

Do NOT edit files. Output severity-ranked P0–P3 only.

## Scope (NEW / MOD)
- …

## DO NOT touch
- …

## Baseline (already run — trust these numbers)
- tests: …
- typecheck: …

## Business rules for this product
- …

## Focus
- races / idempotency
- auth + tenancy
- migrations-before-code
- fail-open safety gates
- cron TTL vs late callbacks
- double fan-out
- copy honesty vs actual behavior

## Required output
- P0–P3 with confirmed-from-code vs speculative on every item
- concrete failure modes (not adjectives)
- explicit non-findings table for areas checked and cleared
```

Optional CLI second pair of eyes when `agent` is on PATH:

```bash
agent --print --trust --mode ask --model <strong-coding-model> \
  --workspace <app-root> \
  "$(cat .park-predict-prompt.md)"
```

If the agent hangs with empty output for ~2–3 minutes, kill it and retry with a faster high-tier model. Delete the temp prompt when the pass finishes. Prefer ask/plan/read-only modes for predict — never yolo for predict.

You may also do the entire predict yourself in-session. The standard is the artifact quality, not which process typed it.

---

## 5. Fix — only confirmed P0/P1, surgically

After predict, resist the urge to “clean the list.” Most P2/P3 items are leftovers for the report.

### What you may fix

- P0/P1
- tagged **confirmed-from-code**
- with a concrete failure mode and a concrete direction

### What you must not fix (during park)

- Speculative remote/env issues (put on ship checklist)
- P2/P3 polish
- Unrelated dirty WIP
- “While we’re here” refactors
- Rewriting a stack or provider without a product ask (leave ops notes as comments if that is the house style)

### How to fix well

1. Batch only the confirmed items you will actually close in this park.
2. For each item, state the smallest patch that closes the failure mode (e.g. “fail closed when Rx flag unknown”, “call `router.refresh()` after successful action”, “release claim when provider did not settle”).
3. Paste DO NOT touch into the fix prompt every time.
4. After the edit pass, **you** run the continuous test loop (next section). Do not proceed to exhaustive QA on faith.

### Fix prompt template

```markdown
# Park fix

Address ONLY these confirmed issues:

1. <title> — <concrete direction pointing at file/symbol>
2. …

DO NOT touch:
- …

Constraints:
- Surgical only. No refactors. No new features.
- Do not re-drive the feature.
- After edits, run: <same baseline test commands> + typecheck
- Report: what you fixed + leftover risks
```

If using CLI: `--print --trust --yolo` is appropriate for fix, still with a tight prompt. Verify on disk with `git diff` afterward — agents sometimes claim writes they did not make.

---

## 6. Continuous testing loop — you own the green

This is not “run tests once at the end.” This is the heartbeat of parking.

```
baseline (step 3) ── records commands + counts
        │
        ▼
     predict
        │
        ▼
   fix batch (confirmed P0/P1)
        │
        ▼
 YOU re-run the SAME test cmds + typecheck
        │
        ├─ fail → failures become the next fix input (still in boundary)
        │         loop again
        │
        └─ pass → proceed to exhaustive QA
```

### Rules that make the loop real

- **Same commands.** If baseline was `npx tsx --test src/lib/foo/*.test.ts`, do not silently switch to a different glob to make life easier unless you document why.
- **You run them.** Helper agents may run tests; you still re-run (or carefully witness the raw output) before you change park state.
- **Record every iteration.** “After fix 1: 47 pass, typecheck clean.” “After fix 2: 2 fail in gate.test.ts — feeding back.”
- **Ignore self-reports.** “Done, all tests passed” from an agent is a rumor until your terminal says so.
- **Verify writes.** If an agent says it created or patched files, `git diff` / read the file. Hallucinated writes are common enough to assume.
- **Typecheck is in the loop.** A green unit suite with a red typecheck is not parked.
- **Boundary holds under failure.** If your fix breaks tests outside the park boundary, stop and report instead of expanding into a second feature unless the human expands scope.

### Stop conditions

Stop looping when either:

1. **Green** — parked surface tests + typecheck match or beat baseline, and confirmed P0/P1 from predict are closed or consciously deferred with reason; or
2. **Blocked** — you hit a ship blocker you cannot close in code alone (migration not applied remotely, missing provider creds in target env, product decision required). Write it as a ship blocker. Do not fake green.

Do not infinite-loop on P3 nits. Do not widen into a rewrite because the third retest annoyed you.

---

## 7. Exhaustive QA — read-only truth pass

Only after the test loop is green or honestly blocked.

Exhaustive QA is a second read-only pass with a different job than predict:

- Predict asks: “What could break?”
- Exhaustive asks: “Given what we fixed and what we left, can we ship this surface?”

Rules:

- **READ-ONLY.** No sneaky fixes. If you find a new P0, say so and optionally start another tiny fix+retest cycle — but do not silently edit during the QA writeup.
- Return **PASS** or **FAIL** on the parked surface.
- List leftover **P0/P1 only** (open confirmed issues).
- Produce a **ship checklist** aimed at ops reality, not code poetry:
  - migrations applied on the environment that will run the code?
  - env vars present **and** valid there (local `.env` ≠ deploy)?
  - cron routes still pointed at the right handlers?
  - any claim of “delivered” / “synced” that is actually stub/401?
- Suppress dual-role / speculative noise that business rules already kill.

### Exhaustive prompt template

```markdown
# Exhaustive QA (READ-ONLY)

NO edits.

## Parked files
- …

## Retest numbers (final)
- …

## Predict leftovers still open
- …

Return:
1. PASS or FAIL for the parked surface
2. leftover P0/P1 only
3. ship checklist (migrations, env, cron, ops honesty)
```

---

## 8. Blunt report — short, true, ship-shaped

Talk to the human like a chauffeur handing back the keys, not like a consultancy deck.

Include:

```text
Parked: <feature>
Boundary: <one line>
Baseline → final: <N pass> / typecheck <ok|fail>
Fixed: <bullets of confirmed P0/P1 closed>
Leftovers: <P2/P3 or deferred items worth knowing>
Ship blockers: <migrations/env/cron/product — or none>
```

No essay. No heroic narrative of every tool call. No push unless they asked. If you blocked ship, say the blocker in plain language (“107 not verified on prod; holds soft-fail closed → oversell risk”).

---

## Optional Cursor CLI usage

When the `agent` binary is available (often `~/.local/bin/agent`):

| Pass | Suggested flags | Notes |
|------|-----------------|-------|
| Predict / exhaustive | `--print --trust --mode ask` | Read-only. Strong model first. |
| Fix | `--print --trust --yolo` | Tight prompt + DO NOT touch. |

You can park entirely in-session with no CLI. Same sequence. Same loop. Same standards.

Always:

- Put long prompts in a temp `.md` and `$(cat file)`
- Delete temp prompt files after the pass
- Prefer killing a hung empty agent over waiting forever
- Prefer verifying disk state over trusting the agent’s closing paragraph

---

## Domain checklists

When the parked work sends SMS / WhatsApp / email / in-app follow-ups, load and apply [notification-idempotency.md](notification-idempotency.md) during predict and ship checklist. Those patterns (claim-before-send, seed filters, DLT, cron duration) are recurring park killers.

---

## Anti-patterns (if you do these, you failed the park)

- Skipping predict because the diff “looks fine”
- One baseline at the start and no retest after fixes
- Trusting “done” / “tests passed” without your own run
- Re-driving the feature to make it cleaner
- Fixing unrelated dirty files to feel productive
- Claiming ship-ready when migrations or env are unverified on the target
- Fixing speculative P2/P3 noise so the list looks empty
- Editing during a read-only predict/exhaustive pass
- Pushing without an explicit ask
- Inventing a fake PASS/FAIL matrix for a client-only surface with zero tests

---

## Quick self-check before you say “parked”

Ask yourself out loud:

1. Do I have a written NEW/MOD boundary and a DO NOT touch list?
2. Did I record baseline commands and counts?
3. Did I produce a P0–P3 predict with confirmed vs speculative and non-findings?
4. Did I only patch confirmed P0/P1?
5. Did I personally re-run the same tests + typecheck after fixes, looping on failures?
6. Did I give a PASS/FAIL + ship blockers without lying about prod?

If any answer is no, you are not done.
