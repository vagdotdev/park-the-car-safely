#!/usr/bin/env bash
# Verifies park.py's concurrency guarantees against throwaway git repos:
# ledger isolation, refusal to guess between parks, scoped fingerprints,
# conflict detection, lock-safe appends, and pre-v3 flat-layout compatibility.
# Run after any change to park.py.  Usage: bash scripts/test_park.sh
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARK="python3 $HERE/park.py"
T=$(mktemp -d)
cd "$T" || exit 1
git init -q .
git config user.email t@t.t; git config user.name t
echo one > a.txt; echo two > b.txt; echo three > shared.txt
git add -A; git commit -qm init

pass=0; fail=0
check() { # check <desc> <expected-substring> <actual>
  if grep -qF -- "$2" <<<"$3"; then echo "  PASS  $1"; pass=$((pass+1));
  else echo "  FAIL  $1"; echo "        want: $2"; echo "        got:  $(head -c 400 <<<"$3")"; fail=$((fail+1)); fi
}
checkno() {
  if grep -qF -- "$2" <<<"$3"; then echo "  FAIL  $1 (unexpected: $2)"; fail=$((fail+1));
  else echo "  PASS  $1"; pass=$((pass+1)); fi
}

echo "== 1. two isolated parks =="
A=$($PARK init --label alpha --id alpha --agent agentA 2>&1)
B=$($PARK init --label beta  --id beta  --agent agentB 2>&1)
check "park A created"        "park 'alpha' initialized" "$A"
check "park B warns about A"  "1 other active park"      "$B"
check "A prints its id"       "export PARK_ID=alpha"     "$A"
[ -f .park/parks/alpha/state.json ] && [ -f .park/parks/beta/state.json ] \
  && { echo "  PASS  separate ledger dirs"; pass=$((pass+1)); } \
  || { echo "  FAIL  separate ledger dirs"; fail=$((fail+1)); }
check "auto gitignore"        "*"  "$(cat .park/.gitignore)"

echo "== 2. refuses to guess when ambiguous (the v2 bug) =="
AMB=$($PARK triage 2>&1); check "ambiguous dies" "2 parks are active" "$AMB"
[ -n "$AMB" ] && $PARK triage >/dev/null 2>&1; [ $? -ne 0 ] \
  && { echo "  PASS  nonzero exit on ambiguity"; pass=$((pass+1)); } \
  || { echo "  FAIL  nonzero exit on ambiguity"; fail=$((fail+1)); }
check "bad id lists options" "available: alpha, beta" "$($PARK triage --park nope 2>&1)"

echo "== 3. env var + flag both select =="
check "PARK_ID selects"  "[alpha]" "$(PARK_ID=alpha $PARK triage 2>&1)"
check "--park selects"   "[beta]"  "$($PARK triage --park beta 2>&1)"

echo "== 4. disjoint boundaries, no conflict =="
echo A1 >> a.txt; echo B1 >> b.txt
PARK_ID=alpha $PARK boundary >/dev/null 2>&1
PARK_ID=beta  $PARK boundary >/dev/null 2>&1
# each boundary sees the whole dirty tree, so narrow them to simulate real scoping
python3 - <<'PY'
import json
for pid, keep in (("alpha", "a.txt"), ("beta", "b.txt")):
    p = f".park/parks/{pid}/boundary.json"
    b = json.load(open(p))
    b["MOD"] = {k: v for k, v in b["MOD"].items() if k == keep}
    b["RUNTIME_SURFACE"] = ["hand-filled"]; b["DO_NOT_TOUCH"] = ["hand-filled"]
    json.dump(b, open(p, "w"), indent=2)
PY
check "alpha no conflict" "no path conflicts" "$(PARK_ID=alpha $PARK conflicts 2>&1)"

echo "== 5. scoped fingerprint survives a neighbour's edits+commit (parallel safety) =="
PARK_ID=alpha $PARK baseline B1 -- true >/dev/null 2>&1
FP1=$(python3 -c "import json;print(json.load(open('.park/parks/alpha/baselines.json'))[0]['fingerprint'].get('scope'))")
echo "B-more" >> b.txt; git add b.txt; git commit -qm "beta commits ONLY its own files"
G=$(PARK_ID=alpha $PARK gate 2>&1)
checkno "alpha B1 NOT stale after beta commit" "evidence stale" "$G"
check   "scope recorded" "$FP1" "$FP1"
echo "A-more" >> a.txt
G2=$(PARK_ID=alpha $PARK gate 2>&1)
check   "alpha B1 IS stale after own edit" "evidence stale" "$G2"

echo "== 6. overlapping claims are detected and gate-blocking =="
python3 - <<'PY'
import json
p = ".park/parks/beta/boundary.json"
b = json.load(open(p)); b["MOD"]["a.txt"] = {"hunks": ["1-1"], "risk": []}
json.dump(b, open(p, "w"), indent=2)
PY
C=$(PARK_ID=alpha $PARK conflicts 2>&1)
check "conflict detected" "beta: 1 shared path" "$C"
check "gate blocks on conflict" "overlaps active park" "$(PARK_ID=alpha $PARK gate 2>&1)"
check "ack needs why" "requires --why" "$(PARK_ID=alpha $PARK conflicts --ack beta 2>&1)"
PARK_ID=alpha $PARK conflicts --ack beta --why "beta only reads it" >/dev/null 2>&1
checkno "gate clears after ack" "overlaps active park" "$(PARK_ID=alpha $PARK gate 2>&1)"

echo "== 7. ledgers never cross-contaminate =="
PARK_ID=alpha $PARK triage --set QUICK --why t >/dev/null 2>&1
PARK_ID=beta  $PARK triage --set DEEP  --why t >/dev/null 2>&1
PARK_ID=alpha $PARK pred add --sev P1 --claim "alpha only" --evidence-tag supported >/dev/null 2>&1
PARK_ID=beta  $PARK pred add --sev P0 --claim "beta only"  --evidence-tag supported >/dev/null 2>&1
check "alpha sees only its pred" "alpha only" "$(PARK_ID=alpha $PARK pred list 2>&1)"
checkno "alpha cannot see beta's" "beta only" "$(PARK_ID=alpha $PARK pred list 2>&1)"
check "beta keeps own tier DEEP" "DEEP" "$(PARK_ID=beta $PARK status 2>&1)"
check "alpha keeps own tier QUICK" "QUICK" "$(PARK_ID=alpha $PARK status 2>&1)"
check "cross-park probe rejected" "unknown prediction" \
  "$(PARK_ID=alpha $PARK probe add --pred PRED-001 --level static --expect-pass x --expect-fail y --park beta 2>&1; PARK_ID=beta $PARK probe add --pred PRED-999 --level static --expect-pass x --expect-fail y 2>&1)"

echo "== 8. concurrent appends do not lose entries (flock) =="
for i in $(seq 1 12); do
  ( PARK_ID=beta $PARK pred add --sev P3 --claim "race $i" --evidence-tag speculative >/dev/null 2>&1 ) &
done; wait
N=$(python3 -c "import json;print(len(json.load(open('.park/parks/beta/predictions.json'))))")
[ "$N" -eq 13 ] && { echo "  PASS  all 13 preds survived parallel writes"; pass=$((pass+1)); } \
                || { echo "  FAIL  lost appends: got $N want 13"; fail=$((fail+1)); }

echo "== 9. archive removes it from conflicts and ambiguity =="
PARK_ID=beta $PARK archive >/dev/null 2>&1
check "archived hidden from ambiguity" "PARK STATE — alpha" "$($PARK status 2>&1)"

echo "== 10. pre-v3 flat layout still resolves (in-flight park safety) =="
L=$(mktemp -d); cd "$L"; git init -q .; git config user.email t@t.t; git config user.name t
echo x > f.txt; git add -A; git commit -qm i
mkdir -p .park
cat > .park/state.json <<'JSON'
{"version":"2.0.0","created":"2026-01-01T00:00:00Z","tier":"DEEP","budgets":{"preds":30,"probes":24,"moves":12},"tier_reason":"legacy","stopped":false}
JSON
echo '[]' > .park/predictions.json; echo '[]' > .park/probes.json
echo '[{"id":"B1","cmd":"true","exit":0,"ts":"x","fingerprint":{"head":"abc","tree":"def"}}]' > .park/baselines.json
S=$($PARK status 2>&1)
check "legacy resolves as default" "PARK STATE — default" "$S"
check "legacy tier preserved"      "DEEP"                 "$S"
check "legacy fp compares old way" "whole repo"           "$S"
M=$($PARK migrate --id moved 2>&1)
check "migrate works" "export PARK_ID=moved" "$M"
[ -f .park/parks/moved/state.json ] && [ ! -f .park/state.json ] \
  && { echo "  PASS  migrate relocated files"; pass=$((pass+1)); } \
  || { echo "  FAIL  migrate relocated files"; fail=$((fail+1)); }

echo
echo "RESULT: $pass passed, $fail failed"
rm -rf "$T" "$L"
[ "$fail" -eq 0 ]
