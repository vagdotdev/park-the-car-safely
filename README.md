# Park the car safely v2 — v3.0 "Valet Edition, Parallel"

**User drove. You park. No green by omission.**

An evidence-driven post-implementation QA skill for coding agents (Claude
Code, Cursor, and anything that reads `SKILL.md` conventions). The agent
establishes a completion contract, scopes a hunk-level boundary, baselines
with fingerprinted evidence, generates failure predictions with a
**randomized lateral-thinking battery**, probes every material prediction,
repairs in severity waves, and cannot declare DONE until a **mechanical gate**
and an independent judge both pass.

v2 is a ground-up re-engineering of
[vagdotdev/park-the-car-safely](https://github.com/vagdotdev/park-the-car-safely)
(MIT). The original's discipline — every prediction ends disproved,
fixed-verified, blocked, or user-accepted — is preserved. Everything around
it changed.

## What's actually different

**State lives on disk, not in vibes.** `scripts/park.py` (stdlib-only Python)
persists contract, boundary, baselines, prediction/probe ledgers, and tier to
a `.park/` directory. Context compaction, restarts, and judge handoffs stop
being failure modes.

**Parks run in parallel without corrupting each other (3.0).** Every park owns
a private directory under `.park/parks/<id>/`; there is no shared mutable
index. When more than one park is active, commands *refuse to run* without
`--park`/`PARK_ID` rather than silently defaulting into someone else's ledger.
Evidence fingerprints are scoped to your boundary's claimed paths, so a
neighbouring park committing its own files no longer marks your baselines
stale. Overlapping file claims are detected across parks, block the gate until
narrowed or acknowledged, and are printed into the judge pack. A pre-3.0 flat
`.park/` keeps working as the `default` park, so an in-flight park is never
broken by upgrading.

**A mechanical completion gate.** `park.py gate` exits non-zero — with a
work-queue of reasons — while any material prediction lacks a disposition,
any probe is open, the contract has TODOs, or the latest baseline's
HEAD/tree fingerprint doesn't match the working tree (stale evidence).
"Looks done" is no longer an available verdict.

**Lateral prediction as a first-class engine.** `park.py lateral` deals a
randomized hand from thirteen divergence operators (Invert/pre-mortem, Swap
the Domain, Rotate the Actor, Shift Time, Shift Scale, Negative Space, Succeed
Too Hard, Cut the Wire, Random Entry, The Liar, First/Last Time, Money Walks,
The Neighbour) plus de Bono random-entry seed words — deliberate entropy so
the agent escapes its training-data ruts — followed by a strict convergence
funnel into budgeted, falsifiable prediction records. See
`references/LATERAL.md`.

**Triage tiers with hard budgets.** QUICK / STANDARD / DEEP assigned from
diff size and a risk-pattern scan; budgets cap funded predictions and probes
so trivial diffs don't get a siege and payment refactors don't get a skim.
Overflow ideas go to an honest **unfunded list**, visible in the handoff.

**A built-in eval harness.** `evals/` ships fixture apps with seeded,
documented defects and a scorer that measures detection and process
integrity. The skill's quality is a number you can regress, not an adjective.

**~72% fewer instruction lines (651 vs 2,367)** than v1 across SKILL.md + references, with
higher instruction density (dedup, no repeated rules, rhetoric trimmed).

## Install

```bash
git clone <this-repo> && cd <this-repo>
./install.sh --claude     # -> ~/.claude/skills/park-the-car-safely-v2
./install.sh --cursor     # -> ~/.cursor/skills/park-the-car-safely-v2
./install.sh --project    # -> ./.cursor/skills + ./.agents/skills (as park-the-car-safely-v2)
```

Add `--with-v1` to also install the legacy edition from the `v1` branch
alongside it (`./install.sh --cursor --with-v1`). The two register under
different skill names, so they coexist rather than compete.

Requires only `git` and Python 3.8+ on the agent's machine.

## Use

Say any of: "park the car safely" · "I drove, you park" · "review my changes
before I ship" · "is this safe to ship?" · "do a QA pass on this feature".

The agent will drive `park.py` itself:

```
init → triage → boundary → baseline … → lateral → pred/probe ledgers
     → fix waves → gate (must pass) → judgepack → handoff
```

`python3 scripts/park.py status` at any time shows live park state and the
gate's current work queue.

## Layout

```
park-the-car-safely-v2/
├── SKILL.md                  # orchestrator
├── scripts/
│   ├── park.py               # parks, triage, boundary, baselines, ledgers,
│   │                         # lateral dealer, conflicts, gate, judgepack
│   └── test_park.sh          # 30 assertions on the concurrency guarantees
├── references/
│   ├── LATERAL.md            # the thirteen operators + convergence funnel
│   ├── PROBES.md             # probe levels + recipes
│   ├── LENSES.md             # stack-keyed domain lenses
│   ├── NOTIFICATIONS.md      # SMS/WhatsApp/email idempotency + consent
│   ├── JUDGE.md              # gate semantics + independent judge protocol
│   └── TEMPLATES.md          # contract + handoff
└── evals/                    # seeded-bug scenarios + scorer
```

## Versions

`main` carries v2 (current). The original prose-only skill is preserved on the
[`v1` branch](https://github.com/vagdotdev/park-the-car-safely/tree/v1) — it
installs as the separate skill `park-the-car-safely`, so both editions can sit
side by side in one agent's skill directory.

## Verification

Everything below is exercised by an end-to-end run in a scratch repo (see
CHANGELOG for the tested flow): init → triage → boundary → red/green
baselines → lateral deal → budget enforcement → pred/probe lifecycle
(including the refusals: closing without evidence, accepted-risk on P0
without user flag, probes without expect-fail) → gate failing with reasons →
gate passing → judgepack. The eval scorer is validated against a synthetic
perfect run and a lossy run.

The concurrency guarantees have their own suite — run it after any change to
`park.py`:

```bash
bash park-the-car-safely-v2/scripts/test_park.sh   # 30 passed, 0 failed
```

It builds throwaway git repos and asserts ledger isolation, refusal to guess
between parks, scoped fingerprints (a neighbour's commit must not stale your
evidence, your own edit must), conflict detection and gate-blocking, lock-safe
parallel appends, archive semantics, and pre-3.0 flat-layout compatibility
plus `migrate`.

## License

MIT. Derived from vagdotdev/park-the-car-safely (MIT) — use it, fork it,
make it stricter.
