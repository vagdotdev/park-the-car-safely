# Park the car safely

**User drove. You park. No green by omission.**

A long-running Cursor Agent Skill for post-implementation QA. It treats parking
as a standing objective, not a one-turn checklist:

```text
contract → scope → baseline → system map → exhaustive predict
         → prediction probes → severity repair waves
         → continuous retest → re-predict → independent judge → handoff
```

The skill is deliberately aggressive about weak evidence:

- every material prediction must be probed;
- every confirmed defect must be fixed, blocked, or explicitly accepted;
- every fix wave reruns the frozen baseline and affected-path probes;
- every completion claim is judged against a concrete contract;
- whole-branch red cannot be hidden behind feature-level green.

It remains conservative about edits: no redesign, no unrelated cleanup, no
speculative rewrites, and no push/deploy/migration without permission.

## What changed in the long-range edition

The main skill now acts as an orchestrator under 500 lines. Detailed playbooks
load only when relevant:

| File | Purpose |
|---|---|
| [`SKILL.md`](./park-the-car-safely/SKILL.md) | Core standing objective and ten-phase park state machine |
| [`GOAL-LOOP.md`](./park-the-car-safely/GOAL-LOOP.md) | Completion contracts, continuation, wait barriers, conservative judge, blocked audit |
| [`PREDICT-PLAYBOOK.md`](./park-the-car-safely/PREDICT-PLAYBOOK.md) | Runtime graphs, invariants, breadth/depth prediction, P0–P3 records |
| [`PROBE-AND-LOOP.md`](./park-the-car-safely/PROBE-AND-LOOP.md) | Turn predictions into static/unit/API/browser/concurrency/environment probes |
| [`DOMAIN-LENSES.md`](./park-the-car-safely/DOMAIN-LENSES.md) | Auth, tenancy, money, schema, races, integrations, UI, ops, privacy, AI |
| [`REPORT-TEMPLATES.md`](./park-the-car-safely/REPORT-TEMPLATES.md) | State, baseline, prediction, probe, fix-wave, judge, blocked, and handoff artifacts |
| [`notification-idempotency.md`](./park-the-car-safely/notification-idempotency.md) | SMS, WhatsApp, email, in-app, cron, claim, and provider-settlement checks |

The standing-goal design is informed by Ralph-loop systems and Hermes Agent’s
completion-contract pattern: outcome, verification, constraints, boundaries,
stop conditions, continuation, wait, and conservative evidence-based judging.
This repository implements those ideas as agent instructions; it does not
pretend a markdown skill can install Hermes runtime persistence.

## Install

### Cursor remote rule

1. Open **Cursor Settings → Rules**
2. Choose **Add Rule → Remote Rule (GitHub)**
3. Paste:

```text
https://github.com/vagdotdev/park-the-car-safely
```

### Manual personal install

```bash
git clone https://github.com/vagdotdev/park-the-car-safely.git
mkdir -p ~/.cursor/skills
rm -rf ~/.cursor/skills/park-the-car-safely
cp -R park-the-car-safely/park-the-car-safely ~/.cursor/skills/park-the-car-safely
```

### Manual project install

```bash
mkdir -p .cursor/skills
rm -rf .cursor/skills/park-the-car-safely
cp -R /path/to/park-the-car-safely/park-the-car-safely .cursor/skills/park-the-car-safely
```

The same package works under `.agents/skills/` for tools that use that
convention.

## Use

Invoke:

```text
/park-the-car-safely
```

Or say:

- “Park the car safely.”
- “I drove; you park.”
- “Run the full checking loop.”
- “Keep attacking this feature until the evidence says it is safe.”
- “Do a long-range post-drive QA pass.”

## Completion standard

The skill does not stop at “tests pass.” It stops at one of:

- **DONE** — completion contract proved with current evidence;
- **BLOCKED** — definitive external/user-owned stop condition with attempts and
  exact resume point;
- **PAUSED** — iteration budget reached with state preserved.

Anything else means continue.

## License

MIT — use it, fork it, make it stricter.
