#!/usr/bin/env python3
"""park.py — evidence engine for the park-the-car-safely skill.

Stdlib only. State lives in <git-root>/.park/ as JSON + markdown, so it
survives context compaction, session restarts, and handoffs to independent
judges. The `gate` subcommand is the mechanical completion referee: it exits
non-zero, with reasons, until the park is honestly finished.

Concurrency model (v3): many parks can run in one repo at the same time.
Every park owns a private directory under .park/parks/<id>/ and never writes
to another park's ledger. There is no shared mutable index — `list` and
conflict detection read each park's own files. When more than one park is
active, every command must name one via --park or PARK_ID; the tool refuses
to guess, because silently guessing is what lets two agents corrupt one
ledger. Boundaries are compared across parks so overlapping file claims are
reported instead of discovered as mysterious edits, and evidence
fingerprints are scoped to a park's own claimed paths so a neighbouring
park's commits do not spuriously invalidate your baselines.

A pre-v3 flat .park/state.json layout keeps working untouched as the
"default" park, so an in-flight park is never broken by upgrading.
"""

import argparse
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone

try:
    import fcntl
except ImportError:  # non-POSIX: locking degrades to atomic replace only
    fcntl = None

VERSION = "3.0.0"
PARK_DIR_NAME = ".park"
PARKS_SUBDIR = "parks"
EXCLUDE_PATHSPEC = [":(exclude)" + PARK_DIR_NAME]  # .park never dirties evidence
MAX_SCOPE_PATHS = 400  # keep git pathspec argv sane on huge boundaries
OWNER_FRESH_SECONDS = 900  # heartbeat newer than this = someone is probably live

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
    ("neighbour", "THE NEIGHBOUR", "Another agent, migration, or deploy is touching this repo right now. Which of your assumptions about exclusive ownership of files, schema, env, or vendor state is false?"),
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

LEDGERS = {
    "state": "state.json",
    "boundary": "boundary.json",
    "baselines": "baselines.json",
    "predictions": "predictions.json",
    "probes": "probes.json",
    "unfunded": "unfunded.json",
    "lateral": "lateral-last.json",
    "owner": "owner.json",
    "contract": "contract.md",
    "invariants": "invariants.md",
    "judgepack": "judgepack.md",
}

CONTRACT_TEMPLATE = """PARK COMPLETION CONTRACT
Outcome:
  TODO(name the single concrete state that must be true at completion)

Verification:
  TODO(exact commands, probes, artifacts, environment checks that prove it)

Constraints:
  TODO(what must not regress or be touched; no unauthorized external mutations)

Boundaries:
  See this park's boundary.json plus hand-added runtime surface and DO NOT TOUCH.
  TODO(add runtime surface + DO NOT TOUCH)

Stop when:
  TODO(user-owned decisions or definitive external barriers that end the park)
"""


# ---------------------------------------------------------------- utilities

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def epoch():
    return int(time.time())


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


def park_root(root):
    return os.path.join(root, PARK_DIR_NAME)


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()[:12]


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


def warn(msg):
    print(f"park: {msg}", file=sys.stderr)


def atomic_write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


@contextmanager
def locked(path):
    """Advisory exclusive lock so parallel probes cannot lose ledger appends."""
    if fcntl is None:
        yield
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lock_path = path + ".lock"
    with open(lock_path, "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:32] or "park"


def agent_id(explicit=None):
    return explicit or os.environ.get("PARK_AGENT") or "anon"


# ---------------------------------------------------------------- park object

class Park:
    def __init__(self, root, pid, legacy=False):
        self.root = root
        self.id = pid
        self.legacy = legacy
        self.dir = (park_root(root) if legacy
                    else os.path.join(park_root(root), PARKS_SUBDIR, pid))

    def path(self, key):
        return os.path.join(self.dir, LEDGERS[key])

    def exists(self):
        return os.path.exists(self.path("state"))

    def load(self, key, default=None):
        p = self.path(key)
        if not os.path.exists(p):
            return default
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return default

    def save(self, key, data):
        p = self.path(key)
        atomic_write(p, json.dumps(data, indent=2))
        return p

    def append(self, key, entry):
        """Lock-protected read-modify-write so concurrent probes don't clobber."""
        p = self.path(key)
        with locked(p):
            items = self.load(key, []) or []
            items.append(entry)
            atomic_write(p, json.dumps(items, indent=2))
        return entry

    def read_text(self, key, default=""):
        p = self.path(key)
        if not os.path.exists(p):
            return default
        with open(p, "r", encoding="utf-8") as f:
            return f.read()

    def status(self):
        return (self.load("state", {}) or {}).get("status", "active")

    def label(self):
        return (self.load("state", {}) or {}).get("label") or self.id

    def owner(self):
        return self.load("owner", {}) or {}

    def touch_owner(self, agent=None, claim=False):
        info = self.owner()
        if claim or not info:
            info = {"agent": agent_id(agent), "host": os.uname().nodename,
                    "created": now(), "created_epoch": epoch()}
        info["heartbeat"] = now()
        info["heartbeat_epoch"] = epoch()
        info["last_agent"] = agent_id(agent)
        self.save("owner", info)
        return info

    def claimed_paths(self):
        b = self.load("boundary", None)
        if not b:
            return []
        return sorted(set(list(b.get("MOD", {})) + list(b.get("NEW", {}))))


def discover_parks(root):
    parks = []
    pr = park_root(root)
    if os.path.exists(os.path.join(pr, LEDGERS["state"])):
        parks.append(Park(root, "default", legacy=True))
    pdir = os.path.join(pr, PARKS_SUBDIR)
    if os.path.isdir(pdir):
        for name in sorted(os.listdir(pdir)):
            if os.path.isdir(os.path.join(pdir, name)):
                parks.append(Park(root, name))
    return parks


def resolve_park(root, requested=None):
    """Never guess between multiple parks — guessing is how ledgers collide."""
    parks = discover_parks(root)
    by_id = {p.id: p for p in parks}
    req = requested or os.environ.get("PARK_ID")
    if req:
        if req in by_id:
            return by_id[req]
        avail = ", ".join(by_id) or "none"
        die(f"no park '{req}' in {park_root(root)} (available: {avail})")
    if not parks:
        die("no park in this repo — run `park.py init --label \"<what you are parking>\"`")
    active = [p for p in parks if p.status() != "archived"]
    if len(active) == 1:
        return active[0]
    if not active:
        die(f"all {len(parks)} parks are archived — `park.py init` a new one")
    listing = "\n".join(f"    {p.id:<24} {p.status():<9} {p.label()}" for p in active)
    die(f"{len(active)} parks are active — name one with --park <id> or PARK_ID=<id>:\n{listing}")


# ---------------------------------------------------------------- evidence

def fingerprint(root, park=None):
    """Bind evidence to code state.

    `tree` covers the whole repo (kept for pre-v3 ledgers). `scope` covers
    only this park's claimed paths — committed blobs, working-tree status and
    unstaged diff — so a parallel park editing or committing elsewhere does
    not invalidate evidence that is still true for your own files.
    """
    _, head = git(["rev-parse", "--short=12", "HEAD"], root)
    head = head or "NO-HEAD"
    _, status = git(["status", "--porcelain", "-uall", "--"] + ["."] + EXCLUDE_PATHSPEC, root)
    _, diff = git(["diff", "HEAD", "--"] + ["."] + EXCLUDE_PATHSPEC, root)
    fp = {"head": head, "tree": sha(status + "\n" + diff)}
    paths = park.claimed_paths() if park else []
    if paths:
        sel = paths[:MAX_SCOPE_PATHS]
        _, blobs = git(["ls-tree", "-r", "HEAD", "--"] + sel, root)
        _, sstat = git(["status", "--porcelain", "-uall", "--"] + sel, root)
        _, sdiff = git(["diff", "HEAD", "--"] + sel, root)
        fp["scope"] = sha(blobs + "\n" + sstat + "\n" + sdiff)
        fp["scope_paths"] = len(sel)
        if len(paths) > MAX_SCOPE_PATHS:
            fp["scope_truncated"] = len(paths)
    return fp


def fp_stale(stored, current):
    """Scoped comparison when both sides have it; pre-v3 ledgers keep old rules."""
    if not stored:
        return True
    if "scope" in stored and "scope" in current:
        return stored["scope"] != current["scope"]
    return (stored.get("head"), stored.get("tree")) != (current.get("head"), current.get("tree"))


def next_id(items, prefix):
    return f"{prefix}-{len(items) + 1:03d}"


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
    return files, lines, [u for u in untracked.splitlines() if u]


def conflicts_for(root, me):
    """Which other live parks claim the same files? Computed from their own
    boundaries — there is no shared index to corrupt."""
    mine = set(me.claimed_paths())
    out = {}
    if not mine:
        return out
    for other in discover_parks(root):
        if other.id == me.id or other.status() == "archived":
            continue
        overlap = mine & set(other.claimed_paths())
        if overlap:
            out[other.id] = sorted(overlap)
    return out


# ---------------------------------------------------------------- commands

def cmd_init(args):
    root = git_root()
    pr = park_root(root)
    os.makedirs(pr, exist_ok=True)
    gi = os.path.join(pr, ".gitignore")
    if not os.path.exists(gi):
        atomic_write(gi, "*\n")  # park state never dirties the repo it audits

    existing = discover_parks(root)
    if args.id:
        pid = slugify(args.id)
    elif args.label:
        pid = f"{slugify(args.label)}-{os.urandom(2).hex()}"
    else:
        pid = f"park-{os.urandom(2).hex()}"

    park = Park(root, pid)
    if park.exists() and not args.force:
        die(f"park '{pid}' already exists (use --force to reset its state)")
    os.makedirs(park.dir, exist_ok=True)

    park.save("state", {"version": VERSION, "id": pid, "label": args.label or pid,
                        "created": now(), "status": "active", "tier": None,
                        "budgets": None, "tier_reason": None, "stopped": False,
                        "conflicts_ack": {}})
    for key in ("predictions", "probes", "baselines", "unfunded"):
        if not os.path.exists(park.path(key)):
            park.save(key, [])
    if not os.path.exists(park.path("contract")) or args.force:
        atomic_write(park.path("contract"), CONTRACT_TEMPLATE)
    park.touch_owner(args.agent, claim=True)

    ok(f"park '{pid}' initialized at {park.dir}")
    ok(f"contract stub: {park.path('contract')}  (fill every TODO before the gate will pass)")
    ok("")
    ok(f"  USE THIS PARK ID ON EVERY COMMAND:   export PARK_ID={pid}")
    ok(f"  (or pass --park {pid})")
    others = [p for p in existing if p.status() != "archived"]
    if others:
        ok("")
        ok(f"note: {len(others)} other active park(s) in this repo: {', '.join(p.id for p in others)}")
        ok("      your ledger is separate from theirs; run `park.py list` to see overlap")


def cmd_list(args):
    root = git_root()
    parks = discover_parks(root)
    if not parks:
        ok("no parks in this repo")
        return
    ok(f"PARKS in {park_root(root)}")
    for p in parks:
        st = p.load("state", {}) or {}
        preds = p.load("predictions", []) or []
        probes = p.load("probes", []) or []
        openp01 = [x["id"] for x in preds if x["sev"] in {"P0", "P1"} and x["status"] == "open"]
        own = p.owner()
        hb = own.get("heartbeat_epoch")
        age = f"{(epoch() - hb) // 60}m ago" if hb else "unknown"
        live = "LIVE" if hb and (epoch() - hb) < OWNER_FRESH_SECONDS else "idle"
        flag = " (pre-v3 flat layout)" if p.legacy else ""
        ok(f"  {p.id:<24} {p.status():<9} {live:<5} tier={str(st.get('tier')):<9} "
           f"preds={len(preds):<3} probes={len(probes):<3} openP0P1={len(openp01)}{flag}")
        ok(f"      label: {p.label()}")
        ok(f"      agent: {own.get('last_agent', '?')}  heartbeat: {age}  claims: {len(p.claimed_paths())} paths")
        conf = conflicts_for(root, p)
        if conf:
            for other, paths in conf.items():
                ok(f"      CONFLICT with {other}: {len(paths)} shared path(s), e.g. {paths[0]}")
    ok("")
    ok("two parks may run side by side; they must not claim the same files without an "
       "explicit ack (`park.py conflicts --ack <id> --why ...`)")


def cmd_conflicts(args):
    root = git_root()
    park = resolve_park(root, args.park)
    conf = conflicts_for(root, park)
    if args.ack:
        state = park.load("state", {}) or {}
        if args.ack not in conf and not args.force:
            die(f"no live conflict with '{args.ack}' to acknowledge (use --force to record anyway)")
        if not args.why:
            die("--ack requires --why (how are you avoiding the collision?)")
        state.setdefault("conflicts_ack", {})[args.ack] = {"why": args.why, "ts": now()}
        park.save("state", state)
        ok(f"acknowledged overlap with {args.ack}: {args.why}")
        return
    if not conf:
        ok(f"{park.id}: no path conflicts with other active parks")
        return
    ok(f"{park.id}: path conflicts with {len(conf)} other active park(s)")
    for other, paths in conf.items():
        ok(f"  {other}: {len(paths)} shared path(s)")
        for p in paths[:20]:
            ok(f"    {p}")
        if len(paths) > 20:
            ok(f"    ... and {len(paths) - 20} more")
    ok("resolve by narrowing a boundary, sequencing the work, or "
       "`park.py conflicts --ack <id> --why \"...\"`")


def cmd_archive(args):
    root = git_root()
    park = resolve_park(root, args.park)
    state = park.load("state", {}) or {}
    state["status"] = "archived"
    state["archived_ts"] = now()
    park.save("state", state)
    ok(f"park '{park.id}' archived — it no longer participates in conflict checks")


def cmd_triage(args):
    root = git_root()
    park = resolve_park(root, args.park)
    state = park.load("state", None) or die("run `park.py init` first")
    park.touch_owner(args.agent)
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
    park.save("state", state)
    ok(f"[{park.id}] TIER: {tier}  ({reason})")
    ok(f"budgets: {state['budgets']['preds']} funded predictions, "
       f"{state['budgets']['probes']} probes, {state['budgets']['moves']} lateral moves")
    if tags:
        ok(f"risk tags for lens selection: {', '.join(sorted(tags))}")
    if len([p for p in discover_parks(root) if p.status() != "archived"]) > 1:
        ok("note: auto-triage reads the whole dirty tree. With parallel parks, confirm the "
           "tier reflects YOUR surface and override with --set/--why if not.")


def cmd_boundary(args):
    root = git_root()
    park = resolve_park(root, args.park)
    park.load("state", None) or die("run `park.py init` first")
    park.touch_owner(args.agent)
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

    prev = park.load("boundary", {}) or {}
    boundary = {
        "generated": now(), "park": park.id,
        "stats": {"modified_files": files, "changed_lines": lines, "new_files": len(untracked)},
        "MOD": mod, "NEW": new_files, "risk_tags": all_risk, "hints": hints,
        "RUNTIME_SURFACE": prev.get("RUNTIME_SURFACE")
            or ["TODO(add by hand: callers, jobs, storage, flags, UI paths)"],
        "DO_NOT_TOUCH": prev.get("DO_NOT_TOUCH")
            or ["TODO(add by hand: unrelated dirty WIP)"],
    }
    park.save("boundary", boundary)
    # fingerprint now that claims exist, so it is scoped to this park
    boundary["fingerprint"] = fingerprint(root, park)
    park.save("boundary", boundary)

    ok(f"[{park.id}] boundary written: {park.path('boundary')}")
    ok(f"MOD: {len(mod)} files (hunk-level)   NEW: {len(new_files)}   risk: {', '.join(all_risk) or 'none'}")
    for h in hints:
        ok(f"hint: {h}")
    conf = conflicts_for(root, park)
    for other, paths in conf.items():
        warn(f"CONFLICT: park '{other}' also claims {len(paths)} of these paths "
             f"(e.g. {paths[0]}) — narrow, sequence, or ack before editing")
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
    park = resolve_park(root, args.park)
    park.load("state", None) or die("run `park.py init` first")
    park.touch_owner(args.agent)
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
        "fingerprint": fingerprint(root, park),
    }
    park.append("baselines", entry)
    verdict = "GREEN" if code == 0 else f"RED (exit {code})"
    fp = entry["fingerprint"]
    ok(f"[{park.id}] {args.id}: {verdict}  {entry['counts'] or ''}  [{dur}s]  "
       f"fp {fp['head']}/{fp.get('scope') or fp['tree']}"
       f"{' (scoped)' if 'scope' in fp else ''}")
    if code != 0:
        ok("classify this red: caused | pre-existing | environmental | unknown "
           "(record parked failures as confirmed predictions)")


def cmd_lateral(args):
    root = git_root()
    park = resolve_park(root, args.park)
    state = park.load("state", None) or die("run `park.py init` first")
    park.touch_owner(args.agent)
    budgets = state.get("budgets") or TIER_BUDGETS["STANDARD"]
    n = args.n or budgets["moves"]
    rng = random.Random(args.seed if args.seed is not None else time.time_ns())
    hand = rng.sample(LATERAL_MOVES, min(n, len(LATERAL_MOVES)))
    if not any(k == "random-entry" for k, _, _ in hand):
        hand[-1] = next(m for m in LATERAL_MOVES if m[0] == "random-entry")
    seeds = rng.sample(SEED_WORDS, 3)
    ok(f"[{park.id}] LATERAL BATTERY — {len(hand)} moves dealt "
       f"(tier {state.get('tier') or 'unset'}; fund at most {budgets['preds']} predictions)")
    ok("Play every move ≥2 honest minutes. Diverge freely; converge via `pred add`.\n")
    for key, name, prompt in hand:
        ok(f"  [{key}] {name}\n      {prompt}")
    ok(f"\n  random-entry seeds: {', '.join(seeds)}")
    park.save("lateral", {"ts": now(), "moves": [k for k, _, _ in hand], "seeds": seeds,
                          "seed_arg": args.seed})


def cmd_pred(args):
    root = git_root()
    park = resolve_park(root, args.park)
    state = park.load("state", None) or die("run `park.py init` first")
    park.touch_owner(args.agent)
    if args.action == "add":
        if args.sev not in {"P0", "P1", "P2", "P3"}:
            die("--sev must be P0..P3")
        if args.evidence_tag not in EVIDENCE_TAGS:
            die(f"--evidence-tag must be one of {sorted(EVIDENCE_TAGS)}")
        if not args.claim:
            die("--claim is required")
        rec = {
            "id": None, "sev": args.sev, "claim": args.claim,
            "invariant": args.invariant, "move": args.move,
            "evidence_tag": args.evidence_tag, "trigger": args.trigger,
            "expected": args.expected, "status": "open", "verdict": None,
            "evidence": None, "ts": now(),
        }
        if args.unfunded:
            with locked(park.path("unfunded")):
                unfunded = park.load("unfunded", []) or []
                rec["id"] = next_id(unfunded, "UNF")
                unfunded.append(rec)
                park.save("unfunded", unfunded)
            ok(f"[{park.id}] {rec['id']} recorded as UNFUNDED (visible in handoff, honestly unprobed)")
            return
        budget = (state.get("budgets") or TIER_BUDGETS["STANDARD"])["preds"]
        with locked(park.path("predictions")):
            preds = park.load("predictions", []) or []
            if len(preds) >= budget:
                die(f"funded budget ({budget}) reached — add --unfunded, close something, "
                    f"or raise tier via `triage --set`")
            rec["id"] = next_id(preds, "PRED")
            preds.append(rec)
            park.save("predictions", preds)
        ok(f"[{park.id}] {rec['id']} [{rec['sev']}/{rec['evidence_tag']}/{rec['move'] or 'lens'}] "
           f"funded: {rec['claim']}")
    elif args.action == "list":
        for p in park.load("predictions", []) or []:
            ok(f"{p['id']} {p['sev']:>2} {p['status']:<14} "
               f"[{p['evidence_tag']}/{p.get('move') or 'lens'}] {p['claim']}")
        unfunded = park.load("unfunded", []) or []
        if unfunded:
            ok(f"-- unfunded: {len(unfunded)} (see {park.path('unfunded')})")
    elif args.action == "close":
        if args.verdict not in PRED_VERDICTS:
            die(f"--verdict must be one of {sorted(PRED_VERDICTS)}")
        if not args.evidence:
            die("closing requires --evidence (what proved this verdict)")
        with locked(park.path("predictions")):
            preds = park.load("predictions", []) or []
            p = next((x for x in preds if x["id"] == args.id), None) or die(f"no {args.id}")
            if args.verdict == "accepted-risk" and p["sev"] in {"P0", "P1"} and not args.user_accepted:
                die("accepted-risk on P0/P1 requires --user-accepted (the USER accepts, never you); "
                    "the park then ends STOPPED, not ship-ready")
            p.update({"status": args.verdict, "verdict": args.verdict,
                      "evidence": args.evidence, "closed_ts": now()})
            park.save("predictions", preds)
        if args.verdict == "accepted-risk" and p["sev"] in {"P0", "P1"}:
            state["stopped"] = True
            park.save("state", state)
        ok(f"[{park.id}] {p['id']} -> {args.verdict}")


def cmd_probe(args):
    root = git_root()
    park = resolve_park(root, args.park)
    state = park.load("state", None) or die("run `park.py init` first")
    park.touch_owner(args.agent)
    if args.action == "add":
        preds = park.load("predictions", []) or []
        if not any(p["id"] == args.pred for p in preds):
            die(f"unknown prediction {args.pred} in park '{park.id}'")
        if args.level not in PROBE_LEVELS:
            die(f"--level must be one of {sorted(PROBE_LEVELS)}")
        if not (args.expect_pass and args.expect_fail):
            die("a probe needs --expect-pass AND --expect-fail written before running; "
                "if you can't say what failure looks like, it can't falsify anything")
        budget = (state.get("budgets") or TIER_BUDGETS["STANDARD"])["probes"]
        with locked(park.path("probes")):
            probes = park.load("probes", []) or []
            if len(probes) >= budget:
                die(f"probe budget ({budget}) reached — close probes or raise tier")
            rec = {"id": next_id(probes, "PROBE"), "pred": args.pred, "level": args.level,
                   "setup": args.setup, "cmd": args.cmd, "expect_pass": args.expect_pass,
                   "expect_fail": args.expect_fail, "status": "open", "verdict": None,
                   "observed": None, "ts": now()}
            probes.append(rec)
            park.save("probes", probes)
        ok(f"[{park.id}] {rec['id']} ({rec['level']}) -> {args.pred} added; run it, then `probe close`")
    elif args.action == "list":
        for p in park.load("probes", []) or []:
            ok(f"{p['id']} {p['level']:<11} {p['status']:<12} -> {p['pred']}  {p.get('cmd') or ''}")
    elif args.action == "close":
        if args.verdict not in PROBE_VERDICTS:
            die(f"--verdict must be one of {sorted(PROBE_VERDICTS)} "
                "(inconclusive is a real verdict; it keeps the prediction open)")
        if not args.observed:
            die("closing requires --observed (raw evidence: what actually happened)")
        with locked(park.path("probes")):
            probes = park.load("probes", []) or []
            p = next((x for x in probes if x["id"] == args.id), None) or die(f"no {args.id}")
            p.update({"status": "closed", "verdict": args.verdict,
                      "observed": args.observed, "closed_ts": now(),
                      "fingerprint": fingerprint(root, park)})
            park.save("probes", probes)
        ok(f"[{park.id}] {p['id']} -> {args.verdict}")


def _gate_reasons(root, park):
    reasons = []
    state = park.load("state", None)
    if not state:
        return ["not initialized — run `park.py init`"]
    if not state.get("tier"):
        reasons.append("no tier — run `park.py triage`")
    if not os.path.exists(park.path("contract")):
        reasons.append("contract.md missing")
    elif "TODO(" in park.read_text("contract"):
        reasons.append("contract.md still contains TODO( placeholders")
    boundary = park.load("boundary", None)
    if not boundary:
        reasons.append("boundary missing — run `park.py boundary`")
    elif "TODO(" in json.dumps(boundary):
        reasons.append("boundary.json RUNTIME_SURFACE / DO_NOT_TOUCH still TODO")
    baselines = park.load("baselines", []) or []
    if not baselines:
        reasons.append("no baselines recorded — run `park.py baseline`")
    else:
        current = fingerprint(root, park)
        latest_by_id = {}
        for b in baselines:
            latest_by_id[b["id"]] = b
        stale = [bid for bid, b in latest_by_id.items() if fp_stale(b.get("fingerprint"), current)]
        if stale:
            reasons.append(f"evidence stale vs working tree for {sorted(stale)} — rerun those baselines "
                           f"(current fp {current['head']}/{current.get('scope') or current['tree']})")
        red = [bid for bid, b in latest_by_id.items() if b["exit"] != 0]
        if red:
            reasons.append(f"latest baseline red for {sorted(red)} — classify and disposition, never hide")
    preds = park.load("predictions", []) or []
    material_open = [p["id"] for p in preds if p["sev"] in {"P0", "P1", "P2"} and p["status"] == "open"]
    if material_open:
        reasons.append(f"material predictions without disposition: {material_open}")
    bad_close = [p["id"] for p in preds
                 if p["sev"] in {"P0", "P1"} and p["status"] not in
                 {"open"} | PRED_VERDICTS]
    if bad_close:
        reasons.append(f"invalid P0/P1 states: {bad_close}")
    probes = park.load("probes", []) or []
    pred_by_id = {p["id"]: p for p in preds}
    open_probes = [pr["id"] for pr in probes if pr["status"] == "open"
                   and pred_by_id.get(pr["pred"], {}).get("sev") in {"P0", "P1", "P2"}]
    if open_probes:
        reasons.append(f"open probes on material predictions: {open_probes}")
    confirmed_unfixed = [pr["pred"] for pr in probes if pr.get("verdict") == "confirmed"
                         and pred_by_id.get(pr["pred"], {}).get("status") == "open"]
    if confirmed_unfixed:
        reasons.append(f"confirmed defects still open: {sorted(set(confirmed_unfixed))}")
    acked = (state.get("conflicts_ack") or {})
    unacked = [o for o in conflicts_for(root, park) if o not in acked]
    if unacked:
        reasons.append(f"boundary overlaps active park(s) {unacked} with no acknowledgement — "
                       f"another agent may be editing your surface (`park.py conflicts --ack <id> --why ...`)")
    return reasons


def cmd_gate(args):
    root = git_root()
    park = resolve_park(root, args.park)
    reasons = _gate_reasons(root, park)
    state = park.load("state", {}) or {}
    if not reasons:
        verdict = "STOPPED (user accepted P0/P1 risk — not ship-ready)" if state.get("stopped") else "PASS"
        ok(f"[{park.id}] GATE: {verdict}")
        if not state.get("stopped"):
            ok("mechanics clean — now run `park.py judgepack` and face the independent judge")
        sys.exit(0)
    ok(f"[{park.id}] GATE: FAIL — this is your work queue:")
    for r in reasons:
        ok(f"  - {r}")
    sys.exit(1)


def cmd_status(args):
    root = git_root()
    park = resolve_park(root, args.park)
    state = park.load("state", None) or die("run `park.py init` first")
    preds = park.load("predictions", []) or []
    probes = park.load("probes", []) or []
    baselines = park.load("baselines", []) or []
    unfunded = park.load("unfunded", []) or []
    current = fingerprint(root, park)
    by_status = {}
    for p in preds:
        by_status[p["status"]] = by_status.get(p["status"], 0) + 1
    open_p01 = [p["id"] for p in preds if p["sev"] in {"P0", "P1"} and p["status"] == "open"]
    ok(f"PARK STATE — {park.id}  ({park.label()})")
    ok(f"  tier: {state.get('tier')}  ({state.get('tier_reason')})")
    if "scope" in current:
        extent = f"scoped to {current.get('scope_paths')} claimed paths"
    else:
        extent = "whole repo — no boundary claims yet"
    ok(f"  fingerprint now: {current['head']}/{current.get('scope') or current['tree']}  ({extent})")
    ok(f"  baselines: {len(baselines)} runs, ids: {sorted({b['id'] for b in baselines})}")
    ok(f"  predictions: {len(preds)} funded {dict(sorted(by_status.items()))}, {len(unfunded)} unfunded")
    ok(f"  probes: {len(probes)} ({sum(1 for p in probes if p['status'] == 'open')} open)")
    ok(f"  open P0/P1: {open_p01 or 'none'}")
    conf = conflicts_for(root, park)
    ok(f"  path conflicts: { {k: len(v) for k, v in conf.items()} or 'none'}")
    others = [p.id for p in discover_parks(root) if p.id != park.id and p.status() != "archived"]
    ok(f"  other active parks: {others or 'none'}")
    reasons = _gate_reasons(root, park)
    ok(f"  gate: {'PASS' if not reasons else 'FAIL — ' + str(len(reasons)) + ' reasons (run `park.py gate`)'}")
    ok(f"  next action: {reasons[0] if reasons else 'judgepack + independent judge'}")


def cmd_judgepack(args):
    root = git_root()
    park = resolve_park(root, args.park)
    state = park.load("state", None) or die("run `park.py init` first")
    parts = ["# JUDGE PACK — try to REJECT this completion claim\n",
             f"Park `{park.id}` — {park.label()}\n",
             f"Generated {now()}  fingerprint {json.dumps(fingerprint(root, park))}\n",
             "You are an independent judge with no memory of writing these fixes. "
             "Your job is to reject the claim of completion if any evidence allows it. "
             "Answer the seven questions in references/JUDGE.md against ONLY what is below.\n"]
    if os.path.exists(park.path("contract")):
        parts.append("\n## Contract\n```\n" + park.read_text("contract") + "\n```\n")
    for key, title in [("boundary", "Boundary"), ("baselines", "Baseline ledger"),
                       ("predictions", "Prediction ledger"), ("probes", "Probe ledger"),
                       ("unfunded", "Unfunded hypotheses")]:
        parts.append(f"\n## {title}\n```json\n{json.dumps(park.load(key, None), indent=2)}\n```\n")
    conf = conflicts_for(root, park)
    if conf:
        parts.append("\n## Concurrent parks claiming the same files\n```json\n"
                     + json.dumps(conf, indent=2) + "\n```\n"
                     "Evidence for shared paths may have been invalidated by another agent.\n")
    parts.append("\n## State\n```json\n" + json.dumps(state, indent=2) + "\n```\n")
    path = park.path("judgepack")
    atomic_write(path, "".join(parts))
    ok(f"[{park.id}] judge pack written: {path}")
    ok("hand it to the most independent reviewer available (fresh subagent > fresh context > "
       "explicit read-only adversarial self-review)")


def cmd_migrate(args):
    """Move a pre-v3 flat .park/ into .park/parks/<id>/ once nothing is mid-run."""
    root = git_root()
    pr = park_root(root)
    if not os.path.exists(os.path.join(pr, LEDGERS["state"])):
        die("no pre-v3 flat park found — nothing to migrate")
    pid = slugify(args.id or "default-migrated")
    dest = os.path.join(pr, PARKS_SUBDIR, pid)
    if os.path.exists(dest):
        die(f"destination park '{pid}' already exists")
    os.makedirs(dest, exist_ok=True)
    moved = []
    for name in LEDGERS.values():
        src = os.path.join(pr, name)
        if os.path.exists(src):
            shutil.move(src, os.path.join(dest, name))
            moved.append(name)
    state = Park(root, pid).load("state", {}) or {}
    state.setdefault("id", pid)
    state.setdefault("label", pid)
    state.setdefault("status", "active")
    state["version"] = VERSION
    Park(root, pid).save("state", state)
    ok(f"migrated flat park -> {dest}  ({len(moved)} files)")
    ok(f"use: export PARK_ID={pid}")


# ---------------------------------------------------------------- argparse

def main():
    ap = argparse.ArgumentParser(prog="park.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=VERSION)
    sub = ap.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-p", "--park", help="park id (default: PARK_ID env; "
                                             "required when >1 park is active)")
    common.add_argument("--agent", help="agent label recorded in the heartbeat "
                                        "(default: PARK_AGENT env)")

    p = sub.add_parser("init", parents=[common], help="create a NEW isolated park")
    p.add_argument("--label", help="what this park is auditing (used in the id)")
    p.add_argument("--id", help="explicit park id instead of a generated one")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_init)

    p = sub.add_parser("list", help="all parks in this repo + path conflicts")
    p.set_defaults(fn=cmd_list)

    p = sub.add_parser("conflicts", parents=[common],
                       help="show/acknowledge boundary overlap with other parks")
    p.add_argument("--ack", help="park id whose overlap you are acknowledging")
    p.add_argument("--why", help="how the collision is being avoided")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_conflicts)

    p = sub.add_parser("archive", parents=[common], help="retire a finished park")
    p.set_defaults(fn=cmd_archive)

    p = sub.add_parser("migrate", help="move a pre-v3 flat .park/ into parks/<id>/")
    p.add_argument("--id", help="destination park id")
    p.set_defaults(fn=cmd_migrate)

    p = sub.add_parser("triage", parents=[common],
                       help="assign tier + budgets from diff and risk scan")
    p.add_argument("--set", choices=list(TIER_BUDGETS), help="override tier explicitly")
    p.add_argument("--why", help="reason for override")
    p.set_defaults(fn=cmd_triage)

    p = sub.add_parser("boundary", parents=[common],
                       help="hunk-level boundary + risk tags + negative-space hints")
    p.set_defaults(fn=cmd_boundary)

    p = sub.add_parser("baseline", parents=[common],
                       help="run a command, record fingerprinted evidence")
    p.add_argument("id", help="ledger id, e.g. B1")
    p.add_argument("cmd", nargs=argparse.REMAINDER, help="-- command to run")
    p.set_defaults(fn=cmd_baseline)

    p = sub.add_parser("lateral", parents=[common],
                       help="deal a randomized lateral-thinking battery")
    p.add_argument("--n", type=int, help="number of moves (default: tier budget)")
    p.add_argument("--seed", type=int, help="reproducible deal")
    p.set_defaults(fn=cmd_lateral)

    p = sub.add_parser("pred", parents=[common], help="prediction ledger")
    p.add_argument("action", choices=["add", "list", "close"])
    p.add_argument("id", nargs="?", help="prediction id (for close)")
    p.add_argument("--sev"); p.add_argument("--claim"); p.add_argument("--invariant")
    p.add_argument("--move"); p.add_argument("--evidence-tag", default="supported")
    p.add_argument("--trigger"); p.add_argument("--expected")
    p.add_argument("--unfunded", action="store_true")
    p.add_argument("--verdict"); p.add_argument("--evidence")
    p.add_argument("--user-accepted", action="store_true")
    p.set_defaults(fn=cmd_pred)

    p = sub.add_parser("probe", parents=[common], help="probe ledger")
    p.add_argument("action", choices=["add", "list", "close"])
    p.add_argument("id", nargs="?", help="probe id (for close)")
    p.add_argument("--pred"); p.add_argument("--level"); p.add_argument("--setup")
    p.add_argument("--cmd"); p.add_argument("--expect-pass"); p.add_argument("--expect-fail")
    p.add_argument("--verdict"); p.add_argument("--observed")
    p.set_defaults(fn=cmd_probe)

    p = sub.add_parser("status", parents=[common], help="render PARK STATE")
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("gate", parents=[common],
                       help="mechanical completion gate (exit 1 = not done)")
    p.set_defaults(fn=cmd_gate)

    p = sub.add_parser("judgepack", parents=[common],
                       help="bundle everything for an independent judge")
    p.set_defaults(fn=cmd_judgepack)

    args = ap.parse_args()
    for attr in ("park", "agent"):
        if not hasattr(args, attr):
            setattr(args, attr, None)
    args.fn(args)


if __name__ == "__main__":
    main()
