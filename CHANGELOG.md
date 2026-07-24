# Changelog

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
