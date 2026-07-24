# Evals — the skill judges itself

A QA skill that cannot be falsified is exactly the kind of unprobed claim it
exists to eliminate. These scenarios are tiny fixture apps with **seeded,
documented defects** chosen so that ordinary happy-path review misses at
least some of them while specific Lateral Battery operators find them.

## Scenarios

| Scenario | Seeded defects | Lateral moves that catch them |
|---|---|---|
| `s1-tenant-leak` | cross-tenant IDOR read; client-trusted admin flag; fail-open None role | actor, liar, lifecycle |
| `s2-webhook-double` | client-trusted amount; retry double-processing; missing transaction boundary | conservation, cut-wire, overload |
| `s3-fail-open` | missing flag fails open; DST day-window math; unbounded in-memory export | negative-space, time-shift, scale-shift |

## Running an eval

1. Copy a scenario into a fresh git repo and commit it, then make a trivial
   "feature" commit or leave the file staged so there is a diff to park:

   ```bash
   mkdir /tmp/eval-run && cd /tmp/eval-run && git init -q
   cp <skill>/evals/scenarios/s1-tenant-leak/app.py .
   git add -A && git commit -qm base
   ```

2. Give a fresh agent (with the skill installed, without truth.json) the
   scenario's `brief` from truth.json as the task, and let it run the full
   park against `app.py`.

3. Score the resulting ledger:

   ```bash
   python3 <skill>/evals/score.py <skill>/evals/scenarios/s1-tenant-leak \
       --park-dir /tmp/eval-run/.park
   ```

The scorer reports **detection** (seeded bugs matched by any funded or
unfunded prediction, via transparent keyword matching — inspect misses by
hand before blaming the matcher) and **process integrity** (the run kept its
own rules: expect-fail written before probes ran, no material prediction left
undispositioned, evidence on every close). Exit 0 only when both are clean.

## Honest limits

Three scenarios measure floor, not ceiling; keyword matching can miss a
correctly-worded catch or accept a lucky phrase. Add scenarios from your own
production incidents — each truth.json needs only `brief`, `bugs[].sev`,
`bugs[].summary`, `bugs[].match_any`, and the `likely_moves` you'd expect to
find it. A skill change that drops detection on any scenario is a regression,
whatever it does for style.
