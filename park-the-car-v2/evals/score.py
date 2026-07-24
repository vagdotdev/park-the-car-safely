#!/usr/bin/env python3
"""Score a park run against a seeded-bug scenario.

Usage:
    python3 score.py <scenario-dir> --park-dir <repo>/.park

Detection: a seeded bug counts as CAUGHT if any funded or unfunded prediction's
claim+trigger+expected text contains any of the bug's match_any keywords
(case-insensitive). Keyword matching is deliberately simple and transparent —
inspect misses by hand before blaming the matcher.

Process integrity: independently checks that the run kept its own discipline
(probes carried expect-fail before running, no material prediction left
open-without-disposition, evidence recorded on closes).
"""

import argparse
import json
import os
import sys


def load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario", help="path to a scenario dir containing truth.json")
    ap.add_argument("--park-dir", required=True, help="path to the run's .park directory")
    args = ap.parse_args()

    truth = load(os.path.join(args.scenario, "truth.json"))
    if truth is None:
        sys.exit(f"no truth.json in {args.scenario}")
    preds = (load(os.path.join(args.park_dir, "predictions.json"), []) or []) + \
            (load(os.path.join(args.park_dir, "unfunded.json"), []) or [])
    probes = load(os.path.join(args.park_dir, "probes.json"), []) or []

    corpus = [(p.get("id"), " ".join(str(p.get(k) or "") for k in
               ("claim", "trigger", "expected", "invariant")).lower()) for p in preds]

    caught, missed = [], []
    for bug in truth["bugs"]:
        hits = [pid for pid, text in corpus
                if any(kw.lower() in text for kw in bug["match_any"])]
        (caught if hits else missed).append((bug, hits))

    print(f"SCENARIO {truth['scenario']}: detection {len(caught)}/{len(truth['bugs'])}")
    for bug, hits in caught:
        print(f"  CAUGHT {bug['id']} [{bug['sev']}] via {hits} — {bug['summary']}")
    for bug, _ in missed:
        print(f"  MISSED {bug['id']} [{bug['sev']}] — {bug['summary']}"
              f"  (lateral moves that usually find it: {', '.join(bug['likely_moves'])})")

    integrity = []
    for pr in probes:
        if not (pr.get("expect_pass") and pr.get("expect_fail")):
            integrity.append(f"probe {pr.get('id')} lacks expect-pass/expect-fail")
    for p in load(os.path.join(args.park_dir, "predictions.json"), []) or []:
        if p.get("sev") in {"P0", "P1", "P2"} and p.get("status") not in {
                "disproved", "fixed-verified", "blocked-external", "accepted-risk", "open"}:
            integrity.append(f"{p['id']} has invalid status {p.get('status')}")
        if p.get("status") not in {"open", None} and not p.get("evidence"):
            integrity.append(f"{p['id']} closed without evidence")
    open_material = [p["id"] for p in
                     (load(os.path.join(args.park_dir, "predictions.json"), []) or [])
                     if p.get("sev") in {"P0", "P1", "P2"} and p.get("status") == "open"]
    if open_material:
        integrity.append(f"material predictions left open: {open_material}")

    print(f"PROCESS INTEGRITY: {'clean' if not integrity else 'violations'}")
    for v in integrity:
        print(f"  - {v}")

    exploration = len(corpus) - sum(len(h) and 1 for _, h in caught)
    print(f"(ledger size {len(corpus)}; predictions beyond the seeded bugs are "
          f"legitimate exploration, not noise)")
    sys.exit(0 if not missed and not integrity else 1)


if __name__ == "__main__":
    main()
