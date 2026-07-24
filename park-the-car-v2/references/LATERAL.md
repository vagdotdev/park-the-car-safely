# The Lateral Battery — divergent failure prediction

Ordinary QA prediction is convergent: it walks the code and asks "what could
go wrong here?" — and finds the failures the author's mental model already
contains. Lateral prediction deliberately breaks the frame first, then walks
back to the code. The payoff is the class of bugs that survive review after
review: the ones nobody in the rut can see.

The battery has two strictly separated halves. **Divergence** generates
without judging. **Convergence** judges without mercy. Mixing them kills
both — self-censoring during divergence loses the weird winners; skipping
convergence turns the park into unfalsifiable brainstorming.

Run `park.py lateral` to get your hand: a randomized subset of the operators
below plus three random-entry seed words. The randomization is a feature, not
decoration — a deterministic checklist produces the same predictions on every
park, which is exactly the rut this phase exists to escape. Play every dealt
operator for at least two minutes of honest effort before discarding it, even
(especially) the ones that seem irrelevant to this feature.

## The twelve operators

Each operator is a reframing move. Apply it to the runtime graph and
invariants from Phase 3, not to the file list.

**1. INVERT — the pre-mortem.** It is six months from now and this feature
caused a serious incident. Write the incident report's first paragraph, then
work backwards to today: what has to be true in the code for that report to
exist? Don't ask "is it safe?"; ask "given that it failed, how?"
*Example: "Postmortem: 4,000 users double-charged" → works back to a webhook
handler with no idempotency key.*

**2. SWAP THE DOMAIN.** Re-imagine the feature as the same mechanism in an
unforgiving domain — a casino payout, an air-traffic handoff, a bank ledger,
a pharmacy dispensing system — and import that domain's failure taxonomy.
Casinos assume every client is hostile; aviation assumes every handoff can be
dropped; ledgers assume every write needs a compensating entry. Which of
those assumptions does this code silently not make?

**3. ROTATE THE ACTOR.** Replay the flow as someone the author never
imagined: an attacker with a valid account, an exhausted user at 2 a.m.
double-tapping everything, a screen-reader user, someone on 2G who retries on
timeout, the same user in two tabs, the cron job, the retry, the intern with
a production console. Each actor is a different input distribution; most code
is tested against exactly one.

**4. SHIFT TIME.** Move the clock, not the code: DST transition mid-flow,
month/year boundary, leap day, token expiring between validation and use,
deploy skew (old client + new server, new code + old schema, cache carrying
yesterday's shape), a callback arriving before its initiation is persisted,
90 days of accumulated data. Time is an input nobody fuzzes.

**5. SHIFT SCALE.** Set every quantity to 0, 1, 2, N, and absurd: zero items
in the cart, one, two simultaneous, a million; empty string and a 2 GB
payload; one tenant and ten thousand. Behavior at 1 and at N are different
programs; find where the code assumes exactly one of them.

**6. NEGATIVE SPACE.** Stop reading what the diff contains; list what the
feature *implies must exist* and check for absence: the index for the new
query, the migration for the new column, the cleanup job for the new rows,
the revocation path for the new grant, the unsubscribe for the new email, the
error branch for the new call, the test for the new invariant. The most
expensive bugs are files that don't exist.

**7. SUCCEED TOO HARD.** Assume the feature works perfectly and everyone
loves it. Now what breaks? Viral adoption stampedes the cache; the provider
retries your slow-but-successful 200 into a duplicate; the popular export
melts the DB; success emails hit rate limits and mute the account. Success is
a load profile, and load profiles are failure modes.

**8. CUT THE WIRE.** Kill each external dependency and each process at the
worst possible instant: mid-transaction, after the provider accepted but
before you persisted, after you persisted but before you acknowledged. For
every cut, name the contradictory state left behind and who reconciles it.
Partial success is the default state of distributed systems, not the edge
case.

**9. RANDOM ENTRY** (de Bono). Take a seed word from `park.py lateral` —
"lighthouse", "compost", "orchestra" — and force a connection to the feature.
A lighthouse warns before the rocks: where does this feature warn *after*?
Compost: what data rots here and who takes it out? Orchestra: what conducts
these async parts, and what happens when the conductor is late? The
connection is arbitrary; the question it surfaces usually isn't. This
operator exists purely to inject entropy your pattern-matching can't supply.

**10. THE LIAR.** Collect every claim the UI or API makes to a human —
"saved", "delivered", "verified", "secure", "reserved", "you have 3
credits" — and for each, hunt for the input, timing, or failure that makes
the claim false while it still displays. Copy is a promise; find the perjury.

**11. FIRST TIME / LAST TIME.** Run the flow in a cold universe — empty DB,
no cache, flag unset, brand-new tenant, first request after deploy — and in a
dying one: account mid-deletion, subscription just lapsed, offboarding, data
retention purge racing an active session. Steady state is where testing
lives; the edges of a lifecycle are where bugs do.

**12. MONEY WALKS.** Pick the conserved quantity — money, inventory, slots,
credits, permissions, PII — and follow it through the whole graph like an
auditor: where can it be created from nothing, duplicated, destroyed without
record, or moved without authority? Conservation-law violations are always
P0.

## Divergence rules

- Work from the runtime graph and invariant list, with the diff closed.
- Generate at least three candidate failures per dealt operator; write them
  as one-line hypotheses, no justification yet.
- No self-censoring, no feasibility checks, no "the framework handles that".
  Feasibility is convergence's job.
- If an operator produces nothing after honest effort, write "played, dry"
  next to it — silence must be earned, not assumed.

## Convergence funnel

Now judge. In order:

1. **Dedupe** hypotheses that threaten the same invariant via the same
   mechanism.
2. **Bind** each survivor to a named invariant from Phase 3. Can't name one?
   Either add the missing invariant (that's a finding in itself) or discard.
3. **Tag evidence proximity** honestly: `code-confirmed` (you can point at
   the guilty line right now), `supported` (mechanism is plausible in this
   specific code), `speculative` (pure lateral leap).
4. **Score** = severity × likelihood × cheapness-to-probe. A speculative P0
   with a 30-second static probe outranks a supported P2 needing an hour of
   harness.
5. **Fund** the top scorers up to the tier budget with
   `park.py pred add --move <operator> ...`; everything else goes to the
   unfunded list via `park.py pred add --unfunded`. Unfunded ideas appear in
   the handoff — visibly unprobed, never silently dropped.
6. **Spend probes by tag**: `code-confirmed` earns any probe level;
   `supported` earns up to integration; `speculative` earns cheap probes
   only (static trace, one focused unit test) unless a cheap probe upgrades
   its tag.

The output of this phase is not insight. It is a ledger of falsifiable,
funded prediction records that Phase 5 can attack — plus an honest list of
the ideas you couldn't afford. Lateral thinking that never becomes a probe is
just decoration.
