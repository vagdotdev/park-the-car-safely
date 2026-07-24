# Park the car v2 — v2.0 "Valet Edition"

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

**A mechanical completion gate.** `park.py gate` exits non-zero — with a
work-queue of reasons — while any material prediction lacks a disposition,
any probe is open, the contract has TODOs, or the latest baseline's
HEAD/tree fingerprint doesn't match the working tree (stale evidence).
"Looks done" is no longer an available verdict.

**Lateral prediction as a first-class engine.** `park.py lateral` deals a
randomized hand from twelve divergence operators (Invert/pre-mortem, Swap the
Domain, Rotate the Actor, Shift Time, Shift Scale, Negative Space, Succeed
Too Hard, Cut the Wire, Random Entry, The Liar, First/Last Time, Money Walks)
plus de Bono random-entry seed words — deliberate entropy so the agent
escapes its training-data ruts — followed by a strict convergence funnel into
budgeted, falsifiable prediction records. See `references/LATERAL.md`.

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
./install.sh --claude     # -> ~/.claude/skills/park-the-car-v2
./install.sh --cursor     # -> ~/.cursor/skills/park-the-car-v2
./install.sh --project    # -> ./.cursor/skills + ./.agents/skills (as park-the-car-v2)
```

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
park-the-car-v2/
├── SKILL.md                  # orchestrator (218 lines)
├── scripts/park.py           # state, triage, boundary, baselines, ledgers,
│                             # lateral dealer, gate, judgepack
├── references/
│   ├── LATERAL.md            # the twelve operators + convergence funnel
│   ├── PROBES.md             # probe levels + recipes
│   ├── LENSES.md             # stack-keyed domain lenses
│   ├── JUDGE.md              # gate semantics + independent judge protocol
│   └── TEMPLATES.md          # contract + handoff
└── evals/                    # seeded-bug scenarios + scorer
```

## Verification

Everything below is exercised by an end-to-end run in a scratch repo (see
CHANGELOG for the tested flow): init → triage → boundary → red/green
baselines → lateral deal → budget enforcement → pred/probe lifecycle
(including the refusals: closing without evidence, accepted-risk on P0
without user flag, probes without expect-fail) → gate failing with reasons →
gate passing → judgepack. The eval scorer is validated against a synthetic
perfect run and a lossy run.

## License

MIT. Derived from vagdotdev/park-the-car-safely (MIT) — use it, fork it,
make it stricter.
