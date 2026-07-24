# Changelog

## 3.0.0 — "Valet Edition, Parallel"

Motivated by a real incident: two agents ran the skill in one repo at the same
time, silently shared `.park/`, and overwrote each other's boundary and
ledgers. Root cause was three separate defects, all fixed here.

- **Per-park isolation.** Each park owns `.park/parks/<id>/`. No shared mutable
  index exists — `list` and conflict detection read each park's own boundary,
  so there is nothing left to corrupt.
- **No silent defaulting.** With more than one active park, every command
  requires `--park` or `PARK_ID` and exits non-zero listing the options.
  Previously any command opened whatever sat at the shared path.
- **Scoped evidence fingerprints.** Baselines hash only the boundary's claimed
  paths (committed blobs + status + unstaged diff), so a parallel park's
  commits no longer stale your green while your own edits still do. Pre-3.0
  ledgers without a `scope` key keep the old head+tree comparison.
- **Cross-park conflict detection.** Overlapping file claims are reported by
  `boundary`, `status`, and `list`, block the gate, and appear in the judge
  pack. Clear them with `conflicts --ack <id> --why "..."`.
- **Lock-safe ledger appends** via `flock` plus atomic temp-file replace, so
  concurrent probes cannot lose entries.
- New commands: `list`, `conflicts`, `archive`, `migrate`; global `--park` /
  `--agent` with `PARK_ID` / `PARK_AGENT` env support; owner heartbeats.
- `init` now creates a *new* park each time and prints its id, and writes
  `.park/.gitignore` so park state never dirties the repo it audits.
- Added lateral operator 13, **The Neighbour** — attack the assumption of
  exclusive ownership over files, rows, schema, env, and vendor state.
- Added `references/NOTIFICATIONS.md` (multi-channel idempotency/consent
  lens, carried forward from v1) and wired it into Phase 3.
- Added `scripts/test_park.sh`: 30 assertions covering every guarantee above,
  including pre-3.0 flat-layout compatibility and `migrate`.
- Backwards compatible: a pre-3.0 flat `.park/` resolves as the `default`
  park, verified against a live in-flight park mid-run.

## 2.0.0 — "Valet Edition"
- Rebuilt as script-first: all state persisted to `.park/` via stdlib-only
  `scripts/park.py` (init, triage, boundary, baseline, lateral, pred, probe,
  status, gate, judgepack).
- Added mechanical completion gate with fingerprinted evidence-currency
  checks (HEAD + tree hash, `.park` excluded).
- Added the Lateral Battery: 12 divergence operators, randomized dealing,
  random-entry seeds, convergence funnel with evidence tags and budgets.
- Added triage tiers (QUICK/STANDARD/DEEP) with hard prediction/probe
  budgets and an honest unfunded-hypotheses ledger.
- Added eval harness: 3 seeded-bug fixture scenarios + detection/process
  scorer.
- Rewrote SKILL.md to ~270 lines; deduped rules; intent-based triggering.
- Generalized domain lenses (v1 clinic-specific examples abstracted).
- Tested end-to-end in a scratch repo, including every ledger refusal path.

## 1.x (upstream, vagdotdev)
- Original ten-phase markdown skill. Discipline preserved; machinery replaced.
