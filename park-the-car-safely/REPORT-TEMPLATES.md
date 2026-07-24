# Park artifacts and report templates

`SKILL.md` is authoritative. These templates record its evidence and verdicts.

Use these templates to preserve state and prevent evidence from disappearing
between phases. Keep working artifacts detailed; keep the final user handoff
short.

## 1. Completion contract

```text
PARK COMPLETION CONTRACT

Feature:
Outcome:
Verification:
Constraints:
Boundaries:
Stop when:
Additional criteria:
Target environment:
```

## 2. Boundary

```text
PARK BOUNDARY

NEW:
- path — purpose

MOD:
- path:lines/symbol — parked hunk

RUNTIME SURFACE:
- entrypoint
- auth/validation
- domain logic
- storage/migration
- external integration
- callback/job
- user/operator surface

DO NOT TOUCH:
- path/system — reason

AMBIGUITIES:
- question — chosen assumption/evidence
```

## 3. Baseline ledger

```text
BASELINE

ID | Command | Scope | Result | Count | Ownership
---|---------|-------|--------|-------|----------
B1 | ... | targeted | pass | 47/47 | parked
B2 | ... | typecheck | fail | 1 error | unrelated WIP
B3 | ... | browser | fail | 7/8 | stale fixture

Environment:
- cwd:
- runtime/version:
- server/base URL:
- relevant flags:
```

## 4. Runtime map and invariants

```text
RUNTIME MAP

Path family:
entry → validation → auth → domain → persistence → provider
      → callback/retry → UI/operator state → recovery

Authoritative data:
State transitions:
Side effects:
Failure/retry:

INVARIANTS
INV-01:
INV-02:
INV-03:
```

## 5. Predict report

```markdown
## Park predict — <feature>

**Contract:** <one-line outcome>
**Boundary:** <NEW/MOD/runtime summary>
**Baseline:** <commands and counts>
**Verdict:** <current risk statement>

### P0
#### PRED-001 — <title>
- Evidence class:
- Invariant:
- Evidence path:
- Trigger:
- Failure:
- Blast radius:
- Probe:
- Status:

### P1
...

### P2
...

### P3
...

### External unknowns
- ...

### Explicit non-findings
- NF-001 — area / trace / probe / result

### Lens coverage
- applied:
- skipped with reason:
```

## 6. Prediction ledger

```text
ID | Sev | Claim | Evidence | Probe | Status | Fix | Final evidence
---|-----|-------|----------|-------|--------|-----|---------------
P1 | P0 | ... | code trace | PR-01 | confirmed | FX-01 | test ...
P2 | P1 | ... | hypothesis | PR-02 | disproved | — | trace ...
```

Allowed status:

- unprobed
- confirmed
- disproved
- inconclusive
- blocked-external
- accepted-risk
- fix-in-progress
- fixed-verified

## 7. Probe record

```text
PROBE-###
Prediction:
Invariant:
Level:
Setup:
Command/action:
Expected pass:
Expected fail:
Observed:
Raw evidence:
Verdict:
Next:
```

## 8. Fix wave

```text
FIX WAVE <A|B|C>-N

Confirmed predictions:
Root cause:
Smallest patch:
Files/hunks:
Regression signal:
Targeted probe:
Frozen baseline commands:
Dependent paths:
Constraints rechecked:
Diff reviewed:
```

## 9. Iteration log

```text
ITERATION N
Phase:
Action:
Evidence:
Predictions closed:
Predictions opened/reopened:
P0 open:
P1 open:
Baseline delta:
External unknowns:
Judge verdict:
Next concrete action:
```

## 10. Red classification

```text
RED-###
Command:
Failure:
Ownership: parked | pre-existing | environmental | unknown
Evidence:
Effect on contract:
Action:
```

## 11. Wait barrier

```text
WAIT BARRIER
Job/process:
Reason:
Release signal:
Expected range:
Current evidence:
Parallel work:
Escalation threshold:
```

## 12. Completion proof matrix

```text
Requirement | Prediction IDs | Probe IDs | Evidence | State
------------|----------------|-----------|----------|------
...         | ...            | ...       | ...      | proved
```

States:

- proved
- contradicted
- incomplete
- inconclusive
- accepted-risk

## 13. Exhaustive completion judge

```markdown
# Exhaustive park judge — READ ONLY

## Contract
...

## Boundary and constraints
...

## Final checks
...

## Prediction disposition
- total:
- disproved:
- fixed-verified:
- blocked:
- accepted:
- still open:

## Fixes
...

## External unknowns
...

Return:
1. WAIT, PAUSED, CONTINUE, BLOCKED, or DONE
2. Missing proof
3. Open P0/P1
4. Constraint violations
5. Ship checklist
6. Exact next action if not DONE
```

## 14. Blocked audit

```text
PARK BLOCKED

Feature:
Contract status:
Blocking condition:
Why definitive:
Attempts:
Evidence:
Completed safely:
Open P0/P1:
Blast radius:
Owner/action required:
Exact resume point:
Unauthorized actions not taken:
```

## 15. Final user handoff

```text
Parked: <feature>
Boundary: <one line>
Verdict: parked surface PASS/FAIL; repository PASS/FAIL
Baseline → final: <tests/typecheck/build/browser>
Predictions: <total / disproved / fixed / blocked / accepted>
Fixed:
- ...
Open P0/P1:
- none | ...
Leftovers:
- ...
Ship blockers:
- none | ...
External verification:
- verified | not verified
Commit/push/deploy:
- not performed | details
```

Final tone:

- lead with verdict;
- state blockers without padding;
- distinguish code proof from target-environment proof;
- do not narrate every tool call;
- do not say “ship-ready” if repository checks, migrations, env, cron, provider,
  or product decisions remain unverified.
