#!/usr/bin/env python3
"""park.py — evidence engine for the park-the-car-safely skill.

Stdlib only. All state lives in <git-root>/.park/ as JSON + markdown, so it
survives context compaction, session restarts, and handoffs to independent
judges. The `gate` subcommand is the mechanical completion referee: it exits
non-zero, with reasons, until the park is honestly finished.
"""

import argparse
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

VERSION = "2.0.0"
PARK_DIR_NAME = ".park"
EXCLUDE_PATHSPEC = [":(exclude)" + PARK_DIR_NAME]  # .park never dirties evidence

TIER_BUDGETS = {
    "QUICK": {"preds": 6, "probes": 5, "moves": 4},
    "STANDARD": {"preds": 14, "probes": 12, "moves": 7},
    "DEEP": {"preds": 30, "probes": 24, "moves": 12},
}

RISK_PATTERNS = {
    "auth": r"\b(auth|login|session|token|jwt|password|permission|role|rbac|acl)\b",
    "tenant": r"\b(tenant|org_id|organization|clinic|workspace|account_id|owner_id)\b",
    "money": r"\b(payment|charge|price|amount|invoice|refund|credit|billing|stripe|currency)\b",
    "migration": r"\b(migration|alter table|add column|create table|schema|ddl)\b",
    "concurrency": r"\b(lock|mutex|race|retry|idempoten|queue|worker|cron|celery|async|await)\b",
    "webhook": r"\b(webhook|callback|signature|replay)\b",
    "external": r"\b(api[_ ]?key|provider|sdk|http|request\.|fetch\()\b",
    "messaging": r"\b(email|sms|notify|notification|push|twilio|sendgrid)\b",
    "deletion": r"\b(delete|drop|truncate|purge|destroy)\b",
    "pii": r"\b(ssn|passport|dob|address|phone|pii|gdpr)\b",
    "flags": r"\b(feature[_ ]?flag|flag\.|toggle|rollout)\b",
}
HIGH_RISK = {"auth", "tenant", "money", "migration", "concurrency", "webhook", "deletion"}

LATERAL_MOVES = [
    ("invert", "INVERT — pre-mortem", "It failed in prod six months from now. Write the incident's first paragraph, then work backwards to the guilty line."),
    ("domain-swap", "SWAP THE DOMAIN", "Re-imagine this as a casino payout / air-traffic handoff / bank ledger. Which of that domain's assumptions does this code silently not make?"),
    ("actor", "ROTATE THE ACTOR", "Replay the flow as: attacker with a valid account, 2 a.m. double-tapper, screen reader, 2G retrier, same user in two tabs, the cron job, the retry."),
    ("time-shift", "SHIFT TIME", "DST mid-flow, month/year boundary, token expiry between check and use, deploy skew (old client/new server, new code/old schema), callback before initiation persists."),
    ("scale-shift", "SHIFT SCALE", "Set every quantity to 0, 1, 2, N, absurd. Empty string and 2GB payload. One tenant and ten thousand. Where does the code assume exactly one of these?"),
    ("negative-space", "NEGATIVE SPACE", "List what the feature implies must exist — index, migration, cleanup job, revocation path, error branch, test — and check for absence."),
    ("overload", "SUCCEED TOO HARD", "Assume perfect success and viral adoption. What melts? Cache stampede, provider retrying your slow 200, rate-limit mutes, the popular export."),
    ("cut-wire", "CUT THE WIRE", "Kill each dependency and the process at the worst instant: mid-transaction, after provider accepted, before you acknowledged. Name the contradictory state and its reconciler."),
    ("random-entry", "RANDOM ENTRY", "Force a connection between each seed word below and the feature. Arbitrary bridge, real question."),
    ("liar", "THE LIAR", "Collect every claim shown to a human — saved, delivered, verified, N credits — and find the input/timing that makes it false while still displayed."),
    ("lifecycle", "FIRST TIME / LAST TIME", "Run the flow in a cold universe (empty DB, no cache, unset flag, first post-deploy request) and a dying one (mid-deletion, lapsed, purge racing a session)."),
    ("conservation", "MONEY WALKS", "Follow the conserved quantity — money, slots, credits, permissions, PII — like an auditor. Where can it be created, duplicated, or destroyed without record?"),
]

SEED_WORDS = [
    "lighthouse", "compost", "orchestra", "tide", "scaffold", "beehive", "ledger",
    "airlock", "carousel", "glacier", "relay", "harvest", "mirror", "fuse",
    "archive", "parade", "quarry", "compass", "echo", "lattice", "furnace",
    "monsoon", "turnstile", "origami", "pendulum", "reef", "sieve", "vault",
    "wick", "zipline", "anchor", "biopsy", "curfew", "detour", "eclipse",
    "ferment", "gasket", "hologram", "inkwell", "junction", "keel", "lullaby",
    "membrane", "nomad", "oasis", "propeller", "quill", "rudder",
]

PRED_VERDICTS = {"disproved", "fixed-verified", "blocked-external", "accepted-risk"}
PROBE_VERDICTS = {"disproved", "confirmed", "inconclusive", "blocked-external"}
PROBE_LEVELS = {"static", "unit", "api", "journey", "concurrency", "env"}
EVIDENCE_TAGS = {"code-confirmed", "supported", "speculative"}

CONTRACT_TEMPLATE = """PARK COMPLETION CONTRACT
Outcome:
  TODO(name the single concrete state that must be true at completion)

Verification:
  TODO(exact commands, probes, artifacts, environment checks that prove it)

Constraints:
  TODO(what must not regress or be touched; no unauthorized external mutations)

Boundaries:
  See .park/boundary.json plus hand-added runtime surface and DO NOT TOUCH.
  TODO(add runtime surface + DO NOT TOUCH)

Stop when:
  TODO(user-owned decisions or definitive external barriers that end the park)
"""

# ---------------------------------------------------------------- utilities

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd, cwd=None, timeout=1800):
    """Run a command, return (exit_code, combined_output)."""
    try:
        p = subprocess.run(cmd, cwd=cwd, timeout=timeout,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return p.returncode, p.stdout.decode("utf-8", "replace")
    except FileNotFoundError:
        return 127, f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"timeout after {timeout}s"


def git(args, root=None):
    code, out = run(["git"] + args, cwd=root)
    return code, out.strip()


def git_root():
    code, out = git(["rev-parse", "--show-toplevel"])
    return out if code == 0 else os.getcwd()


def park_dir(root):
    return os.path.join(root, PARK_DIR_NAME)


def load(root, name, default):
    path = os.path.join(park_dir(root), name)
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save(root, name, data):
    os.makedirs(park_dir(root), exist_ok=True)
    path = os.path.join(park_dir(root), name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path


def fingerprint(root):
    """Bind evidence to the exact code state, excluding .park itself."""
    _, head = git(["rev-parse", "--short=12", "HEAD"], root)
    head = head or "NO-HEAD"
    _, status = git(["status", "--porcelain", "-uall", "--"] + ["."] + EXCLUDE_PATHSPEC, root)
    _, diff = git(["diff", "HEAD", "--"] + ["."] + EXCLUDE_PATHSPEC, root)
    tree = hashlib.sha256((status + "\n" + diff).encode()).hexdigest()[:12]
    return {"head": head, "tree": tree}


def next_id(items, prefix):
    return f"{prefix}-{len(items) + 1:03d}"


def die(msg, code=1):
    print(f"park: {msg}", file=sys.stderr)
    sys.exit(code)


def ok(msg):
    try:
        print(msg)
    except BrokenPipeError:  # output piped to head/less that closed early
        try:
            sys.stdout.close()
        finally:
            os._exit(0)


# ---------------------------------------------------------------- commands

def cmd_init(args):
    root = git_root()
    pd = park_dir(root)
    os.makedirs(pd, exist_ok=True)
    state = load(root, "state.json", None)
    if state and not args.force:
        die(f"already initialized at {pd} (use --force to reset state.json)")
    state = {"version": VERSION, "created": now(), "tier": None,
             "budgets": None, "tier_reason": None, "stopped": False}
    save(root, "state.json", state)
    for name, default in [("predictions.json", []), ("probes.json", []),
                          ("baselines.json", []), ("unfunded.json", [])]:
        if not os.path.exists(os.path.join(pd, name)):
            save(root, name, default)
    cpath = os.path.join(pd, "contract.md")
    if not os.path.exists(cpath) or args.force:
        with open(cpath, "w", encoding="utf-8") as f:
            f.write(CONTRACT_TEMPLATE)
    ok(f"initialized {pd}")
    ok(f"contract stub: {cpath}  (fill every TODO before the gate will pass)")
    ok(f"tip: add '{PARK_DIR_NAME}/' to .gitignore; evidence fingerprints already exclude it")


def _scan_risk(text):
    tags = set()
    low = text.lower()
    for tag, pat in RISK_PATTERNS.items():
        if re.search(pat, low):
            tags.add(tag)
    return tags


def _diff_stats(root):
    _, numstat = git(["diff", "HEAD", "--numstat", "--"] + ["."] + EXCLUDE_PATHSPEC, root)
    files, lines = 0, 0
    for row in numstat.splitlines():
        parts = row.split("\t")
        if len(parts) >= 2:
            files += 1
            for p in parts[:2]:
                if p.isdigit():
                    lines += int(p)
    _, untracked = git(["ls-files", "--others", "--exclude-standard", "--"] + ["."] + EXCLUDE_PATHSPEC, root)
    untracked_files = [u for u in untracked.splitlines() if u]
    return files, lines, untracked_files


def cmd_triage(args):
    root = git_root()
    state = load(root, "state.json", None) or die("run `park.py init` first")
    files, lines, untracked = _diff_stats(root)
    _, diff = git(["diff", "HEAD", "--"] + ["."] + EXCLUDE_PATHSPEC, root)
    corpus = diff
    for u in untracked[:200]:
        corpus += "\n" + u
        try:
            with open(os.path.join(root, u), "r", encoding="utf-8", errors="replace") as f:
                corpus += "\n" + f.read(20000)
        except OSError:
            pass
    tags = _scan_risk(corpus)
    if args.set:
        tier, reason = args.set, args.why or "manually set"
    elif tags & HIGH_RISK:
        tier = "DEEP"
        reason = f"high-risk surface touched: {', '.join(sorted(tags & HIGH_RISK))}"
    elif files <= 3 and lines + len(untracked) * 5 < 40 and not tags:
        tier, reason = "QUICK", f"small diff ({files} files, ~{lines} lines), no risk tags"
    else:
        tier, reason = "STANDARD", f"{files} files, ~{lines} lines, tags: {', '.join(sorted(tags)) or 'none'}"
    state.update({"tier": tier, "budgets": TIER_BUDGETS[tier], "tier_reason": reason})
    save(root, "state.json", state)
    ok(f"TIER: {tier}  ({reason})")
    ok(f"budgets: {state['budgets']['preds']} funded predictions, "
       f"{state['budgets']['probes']} probes, {state['budgets']['moves']} lateral moves")
    if tags:
        ok(f"risk tags for lens selection: {', '.join(sorted(tags))}")


def cmd_boundary(args):
    root = git_root()
    load(root, "state.json", None) or die("run `park.py init` first")
    files, lines, untracked = _diff_stats(root)
    _, diff = git(["diff", "HEAD", "-U0", "--"] + ["."] + EXCLUDE_PATHSPEC, root)
    mod = {}
    current = None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            mod.setdefault(current, {"hunks": [], "risk": []})
        elif line.startswith("@@") and current:
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if m:
                start = int(m.group(1))
                count = int(m.group(2) or 1)
                mod[current]["hunks"].append(f"{start}-{start + max(count - 1, 0)}")
        elif current and (line.startswith("+") or line.startswith("-")):
            mod[current]["risk"] = sorted(set(mod[current]["risk"]) | _scan_risk(line))
    new_files = {}
    for u in untracked:
        text = ""
        try:
            with open(os.path.join(root, u), "r", encoding="utf-8", errors="replace") as f:
                text = f.read(40000)
        except OSError:
            pass
        new_files[u] = {"risk": sorted(_scan_risk(u + "\n" + text))}
    all_paths = list(mod) + list(new_files)
    all_risk = sorted({t for v in list(mod.values()) + list(new_files.values()) for t in v["risk"]})
    hints = []
    schema_touched = any(re.search(r"(model|schema|entities|\.sql)", p, re.I) for p in all_paths)
    migration_touched = any(re.search(r"migrat", p, re.I) for p in all_paths)
    if schema_touched and not migration_touched:
        hints.append("negative-space: schema/model files touched but no migration file in the diff")
    test_touched = any(re.search(r"(test|spec)", p, re.I) for p in all_paths)
    if all_paths and not test_touched:
        hints.append("negative-space: no test file touched anywhere in the boundary")
    boundary = {
        "generated": now(), "fingerprint": fingerprint(root),
        "stats": {"modified_files": files, "changed_lines": lines, "new_files": len(untracked)},
        "MOD": mod, "NEW": new_files, "risk_tags": all_risk, "hints": hints,
        "RUNTIME_SURFACE": ["TODO(add by hand: callers, jobs, storage, flags, UI paths)"],
        "DO_NOT_TOUCH": ["TODO(add by hand: unrelated dirty WIP)"],
    }
    path = save(root, "boundary.json", boundary)
    ok(f"boundary written: {path}")
    ok(f"MOD: {len(mod)} files (hunk-level)   NEW: {len(new_files)}   risk: {', '.join(all_risk) or 'none'}")
    for h in hints:
        ok(f"hint: {h}")
    ok("now hand-edit RUNTIME_SURFACE and DO_NOT_TOUCH in boundary.json")


def _extract_counts(output):
    counts = {}
    for key, pat in [("passed", r"(\d+)\s+pass(?:ed|ing)?"), ("failed", r"(\d+)\s+fail(?:ed|ing)?"),
                     ("errors", r"(\d+)\s+error")]:
        m = re.search(pat, output, re.I)
        if m:
            counts[key] = int(m.group(1))
    return counts


def cmd_baseline(args):
    root = git_root()
    load(root, "state.json", None) or die("run `park.py init` first")
    cmd = args.cmd
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        die("usage: park.py baseline <id> -- <command...>")
    start = time.time()
    code, out = run(cmd, cwd=root)
    dur = round(time.time() - start, 1)
    entry = {
        "id": args.id, "cmd": " ".join(cmd), "exit": code, "duration_s": dur,
        "counts": _extract_counts(out), "tail": out[-2000:], "ts": now(),
        "fingerprint": fingerprint(root),
    }
    baselines = load(root, "baselines.json", [])
    baselines.append(entry)
    save(root, "baselines.json", baselines)
    verdict = "GREEN" if code == 0 else f"RED (exit {code})"
    ok(f"{args.id}: {verdict}  {entry['counts'] or ''}  [{dur}s]  "
       f"fp {entry['fingerprint']['head']}/{entry['fingerprint']['tree']}")
    if code != 0:
        ok("classify this red: caused | pre-existing | environmental | unknown "
           "(record parked failures as confirmed predictions)")


def cmd_lateral(args):
    root = git_root()
    state = load(root, "state.json", None) or die("run `park.py init` first")
    budgets = state.get("budgets") or TIER_BUDGETS["STANDARD"]
    n = args.n or budgets["moves"]
    rng = random.Random(args.seed if args.seed is not None else time.time_ns())
    hand = rng.sample(LATERAL_MOVES, min(n, len(LATERAL_MOVES)))
    if not any(k == "random-entry" for k, _, _ in hand):
        hand[-1] = next(m for m in LATERAL_MOVES if m[0] == "random-entry")
    seeds = rng.sample(SEED_WORDS, 3)
    ok(f"LATERAL BATTERY — {len(hand)} moves dealt "
       f"(tier {state.get('tier') or 'unset'}; fund at most {budgets['preds']} predictions)")
    ok("Play every move ≥2 honest minutes. Diverge freely; converge via `pred add`.\n")
    for key, name, prompt in hand:
        ok(f"  [{key}] {name}\n      {prompt}")
    ok(f"\n  random-entry seeds: {', '.join(seeds)}")
    save(root, "lateral-last.json",
         {"ts": now(), "moves": [k for k, _, _ in hand], "seeds": seeds,
          "seed_arg": args.seed})


def cmd_pred(args):
    root = git_root()
    state = load(root, "state.json", None) or die("run `park.py init` first")
    preds = load(root, "predictions.json", [])
    if args.action == "add":
        if args.sev not in {"P0", "P1", "P2", "P3"}:
            die("--sev must be P0..P3")
        if args.evidence_tag not in EVIDENCE_TAGS:
            die(f"--evidence-tag must be one of {sorted(EVIDENCE_TAGS)}")
        rec = {
            "id": None, "sev": args.sev, "claim": args.claim,
            "invariant": args.invariant, "move": args.move,
            "evidence_tag": args.evidence_tag, "trigger": args.trigger,
            "expected": args.expected, "status": "open", "verdict": None,
            "evidence": None, "ts": now(),
        }
        if args.unfunded:
            unfunded = load(root, "unfunded.json", [])
            rec["id"] = next_id(unfunded, "UNF")
            unfunded.append(rec)
            save(root, "unfunded.json", unfunded)
            ok(f"{rec['id']} recorded as UNFUNDED (visible in handoff, honestly unprobed)")
            return
        budget = (state.get("budgets") or TIER_BUDGETS["STANDARD"])["preds"]
        if len(preds) >= budget:
            die(f"funded budget ({budget}) reached — add --unfunded, close something, "
                f"or raise tier via `triage --set`")
        rec["id"] = next_id(preds, "PRED")
        preds.append(rec)
        save(root, "predictions.json", preds)
        ok(f"{rec['id']} [{rec['sev']}/{rec['evidence_tag']}/{rec['move'] or 'lens'}] funded: {rec['claim']}")
    elif args.action == "list":
        for p in preds:
            ok(f"{p['id']} {p['sev']:>2} {p['status']:<14} "
               f"[{p['evidence_tag']}/{p.get('move') or 'lens'}] {p['claim']}")
        unfunded = load(root, "unfunded.json", [])
        if unfunded:
            ok(f"-- unfunded: {len(unfunded)} (see .park/unfunded.json)")
    elif args.action == "close":
        p = next((x for x in preds if x["id"] == args.id), None) or die(f"no {args.id}")
        if args.verdict not in PRED_VERDICTS:
            die(f"--verdict must be one of {sorted(PRED_VERDICTS)}")
        if not args.evidence:
            die("closing requires --evidence (what proved this verdict)")
        if args.verdict == "accepted-risk" and p["sev"] in {"P0", "P1"} and not args.user_accepted:
            die("accepted-risk on P0/P1 requires --user-accepted (the USER accepts, never you); "
                "the park then ends STOPPED, not ship-ready")
        p.update({"status": args.verdict, "verdict": args.verdict,
                  "evidence": args.evidence, "closed_ts": now()})
        if args.verdict == "accepted-risk" and p["sev"] in {"P0", "P1"}:
            state["stopped"] = True
            save(root, "state.json", state)
        save(root, "predictions.json", preds)
        ok(f"{p['id']} -> {args.verdict}")


def cmd_probe(args):
    root = git_root()
    load(root, "state.json", None) or die("run `park.py init` first")
    probes = load(root, "probes.json", [])
    if args.action == "add":
        preds = load(root, "predictions.json", [])
        if not any(p["id"] == args.pred for p in preds):
            die(f"unknown prediction {args.pred}")
        if args.level not in PROBE_LEVELS:
            die(f"--level must be one of {sorted(PROBE_LEVELS)}")
        if not (args.expect_pass and args.expect_fail):
            die("a probe needs --expect-pass AND --expect-fail written before running; "
                "if you can't say what failure looks like, it can't falsify anything")
        budget = (load(root, "state.json", {}).get("budgets") or TIER_BUDGETS["STANDARD"])["probes"]
        if len(probes) >= budget:
            die(f"probe budget ({budget}) reached — close probes or raise tier")
        rec = {"id": next_id(probes, "PROBE"), "pred": args.pred, "level": args.level,
               "setup": args.setup, "cmd": args.cmd, "expect_pass": args.expect_pass,
               "expect_fail": args.expect_fail, "status": "open", "verdict": None,
               "observed": None, "ts": now()}
        probes.append(rec)
        save(root, "probes.json", probes)
        ok(f"{rec['id']} ({rec['level']}) -> {args.pred} added; run it, then `probe close`")
    elif args.action == "list":
        for p in probes:
            ok(f"{p['id']} {p['level']:<11} {p['status']:<12} -> {p['pred']}  {p.get('cmd') or ''}")
    elif args.action == "close":
        p = next((x for x in probes if x["id"] == args.id), None) or die(f"no {args.id}")
        if args.verdict not in PROBE_VERDICTS:
            die(f"--verdict must be one of {sorted(PROBE_VERDICTS)} "
                "(inconclusive is a real verdict; it keeps the prediction open)")
        if not args.observed:
            die("closing requires --observed (raw evidence: what actually happened)")
        p.update({"status": "closed", "verdict": args.verdict,
                  "observed": args.observed, "closed_ts": now(),
                  "fingerprint": fingerprint(root)})
        save(root, "probes.json", probes)
        ok(f"{p['id']} -> {args.verdict}")


def _gate_reasons(root):
    reasons = []
    state = load(root, "state.json", None)
    if not state:
        return ["not initialized — run `park.py init`"]
    if not state.get("tier"):
        reasons.append("no tier — run `park.py triage`")
    cpath = os.path.join(park_dir(root), "contract.md")
    if not os.path.exists(cpath):
        reasons.append("contract.md missing")
    else:
        with open(cpath, encoding="utf-8") as f:
            if "TODO(" in f.read():
                reasons.append("contract.md still contains TODO( placeholders")
    boundary = load(root, "boundary.json", None)
    if not boundary:
        reasons.append("boundary missing — run `park.py boundary`")
    else:
        joined = json.dumps(boundary)
        if "TODO(" in joined:
            reasons.append("boundary.json RUNTIME_SURFACE / DO_NOT_TOUCH still TODO")
    baselines = load(root, "baselines.json", [])
    if not baselines:
        reasons.append("no baselines recorded — run `park.py baseline`")
    else:
        current = fingerprint(root)
        latest_by_id = {}
        for b in baselines:
            latest_by_id[b["id"]] = b
        stale = [bid for bid, b in latest_by_id.items() if b["fingerprint"] != current]
        if stale:
            reasons.append(f"evidence stale vs working tree for {sorted(stale)} — rerun those baselines "
                           f"(current fp {current['head']}/{current['tree']})")
        red = [bid for bid, b in latest_by_id.items() if b["exit"] != 0]
        if red:
            reasons.append(f"latest baseline red for {sorted(red)} — classify and disposition, never hide")
    preds = load(root, "predictions.json", [])
    material_open = [p["id"] for p in preds if p["sev"] in {"P0", "P1", "P2"} and p["status"] == "open"]
    if material_open:
        reasons.append(f"material predictions without disposition: {material_open}")
    bad_close = [p["id"] for p in preds
                 if p["sev"] in {"P0", "P1"} and p["status"] not in
                 {"open", "disproved", "fixed-verified", "blocked-external", "accepted-risk"}]
    if bad_close:
        reasons.append(f"invalid P0/P1 states: {bad_close}")
    probes = load(root, "probes.json", [])
    pred_by_id = {p["id"]: p for p in preds}
    open_probes = [pr["id"] for pr in probes if pr["status"] == "open"
                   and pred_by_id.get(pr["pred"], {}).get("sev") in {"P0", "P1", "P2"}]
    if open_probes:
        reasons.append(f"open probes on material predictions: {open_probes}")
    confirmed_unfixed = [pr["pred"] for pr in probes if pr.get("verdict") == "confirmed"
                         and pred_by_id.get(pr["pred"], {}).get("status") == "open"]
    if confirmed_unfixed:
        reasons.append(f"confirmed defects still open: {sorted(set(confirmed_unfixed))}")
    return reasons


def cmd_gate(args):
    root = git_root()
    reasons = _gate_reasons(root)
    state = load(root, "state.json", {})
    if not reasons:
        verdict = "STOPPED (user accepted P0/P1 risk — not ship-ready)" if state.get("stopped") else "PASS"
        ok(f"GATE: {verdict}")
        if not state.get("stopped"):
            ok("mechanics clean — now run `park.py judgepack` and face the independent judge")
        sys.exit(0)
    ok("GATE: FAIL — this is your work queue:")
    for r in reasons:
        ok(f"  - {r}")
    sys.exit(1)


def cmd_status(args):
    root = git_root()
    state = load(root, "state.json", None) or die("run `park.py init` first")
    preds = load(root, "predictions.json", [])
    probes = load(root, "probes.json", [])
    baselines = load(root, "baselines.json", [])
    unfunded = load(root, "unfunded.json", [])
    current = fingerprint(root)
    by_status = {}
    for p in preds:
        by_status[p["status"]] = by_status.get(p["status"], 0) + 1
    open_p01 = [p["id"] for p in preds if p["sev"] in {"P0", "P1"} and p["status"] == "open"]
    ok("PARK STATE")
    ok(f"  tier: {state.get('tier')}  ({state.get('tier_reason')})")
    ok(f"  fingerprint now: {current['head']}/{current['tree']}")
    ok(f"  baselines: {len(baselines)} runs, ids: {sorted({b['id'] for b in baselines})}")
    ok(f"  predictions: {len(preds)} funded {dict(sorted(by_status.items()))}, {len(unfunded)} unfunded")
    ok(f"  probes: {len(probes)} ({sum(1 for p in probes if p['status'] == 'open')} open)")
    ok(f"  open P0/P1: {open_p01 or 'none'}")
    reasons = _gate_reasons(root)
    ok(f"  gate: {'PASS' if not reasons else 'FAIL — ' + str(len(reasons)) + ' reasons (run `park.py gate`)'}")
    ok(f"  next action: {reasons[0] if reasons else 'judgepack + independent judge'}")


def cmd_judgepack(args):
    root = git_root()
    state = load(root, "state.json", None) or die("run `park.py init` first")
    parts = ["# JUDGE PACK — try to REJECT this completion claim\n",
             f"Generated {now()}  fingerprint {json.dumps(fingerprint(root))}\n",
             "You are an independent judge with no memory of writing these fixes. "
             "Your job is to reject the claim of completion if any evidence allows it. "
             "Answer the seven questions in references/JUDGE.md against ONLY what is below.\n"]
    cpath = os.path.join(park_dir(root), "contract.md")
    if os.path.exists(cpath):
        parts.append("\n## Contract\n```\n" + open(cpath, encoding="utf-8").read() + "\n```\n")
    for name, title in [("boundary.json", "Boundary"), ("baselines.json", "Baseline ledger"),
                        ("predictions.json", "Prediction ledger"), ("probes.json", "Probe ledger"),
                        ("unfunded.json", "Unfunded hypotheses")]:
        data = load(root, name, None)
        parts.append(f"\n## {title}\n```json\n{json.dumps(data, indent=2)}\n```\n")
    parts.append("\n## State\n```json\n" + json.dumps(state, indent=2) + "\n```\n")
    path = os.path.join(park_dir(root), "judgepack.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("".join(parts))
    ok(f"judge pack written: {path}")
    ok("hand it to the most independent reviewer available (fresh subagent > fresh context > "
       "explicit read-only adversarial self-review)")


# ---------------------------------------------------------------- argparse

def main():
    ap = argparse.ArgumentParser(prog="park.py", description=__doc__)
    ap.add_argument("--version", action="version", version=VERSION)
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="create .park/ state and contract stub")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("triage", help="assign tier + budgets from diff and risk scan")
    p.add_argument("--set", choices=list(TIER_BUDGETS), help="override tier explicitly")
    p.add_argument("--why", help="reason for override")
    p.set_defaults(fn=cmd_triage)

    p = sub.add_parser("boundary", help="hunk-level boundary + risk tags + negative-space hints")
    p.set_defaults(fn=cmd_boundary)

    p = sub.add_parser("baseline", help="run a command, record fingerprinted evidence")
    p.add_argument("id", help="ledger id, e.g. B1")
    p.add_argument("cmd", nargs=argparse.REMAINDER, help="-- command to run")
    p.set_defaults(fn=cmd_baseline)

    p = sub.add_parser("lateral", help="deal a randomized lateral-thinking battery")
    p.add_argument("--n", type=int, help="number of moves (default: tier budget)")
    p.add_argument("--seed", type=int, help="reproducible deal")
    p.set_defaults(fn=cmd_lateral)

    p = sub.add_parser("pred", help="prediction ledger")
    p.add_argument("action", choices=["add", "list", "close"])
    p.add_argument("id", nargs="?", help="prediction id (for close)")
    p.add_argument("--sev"); p.add_argument("--claim"); p.add_argument("--invariant")
    p.add_argument("--move"); p.add_argument("--evidence-tag", default="supported")
    p.add_argument("--trigger"); p.add_argument("--expected")
    p.add_argument("--unfunded", action="store_true")
    p.add_argument("--verdict"); p.add_argument("--evidence")
    p.add_argument("--user-accepted", action="store_true")
    p.set_defaults(fn=cmd_pred)

    p = sub.add_parser("probe", help="probe ledger")
    p.add_argument("action", choices=["add", "list", "close"])
    p.add_argument("id", nargs="?", help="probe id (for close)")
    p.add_argument("--pred"); p.add_argument("--level"); p.add_argument("--setup")
    p.add_argument("--cmd"); p.add_argument("--expect-pass"); p.add_argument("--expect-fail")
    p.add_argument("--verdict"); p.add_argument("--observed")
    p.set_defaults(fn=cmd_probe)

    p = sub.add_parser("status", help="render PARK STATE")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("gate", help="mechanical completion gate (exit 1 = not done)")
    p.set_defaults(fn=cmd_gate)

    p = sub.add_parser("judgepack", help="bundle everything for an independent judge")
    p.set_defaults(fn=cmd_judgepack)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
