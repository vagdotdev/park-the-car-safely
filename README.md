# Park the car safely

**User drove. You park.**

A Cursor Agent Skill for the post-drive QA loop — written as a full how-to, not a skinny checklist.

The blood of it:

1. **Predict** — how to run a real read-only P0–P3 audit (evidence, confirmed-from-code vs speculative, non-findings)
2. **Continuous testing** — how to own the fail → fix → re-run loop; never trust an agent’s “green”

## Install

### Cursor (recommended)

1. Open **Cursor Settings → Rules**
2. Click **Add Rule → Remote Rule (GitHub)**
3. Paste:

```text
https://github.com/vagdotdev/park-the-car-safely
```

### Manual (personal skill)

```bash
git clone https://github.com/vagdotdev/park-the-car-safely.git
mkdir -p ~/.cursor/skills
cp -R park-the-car-safely/park-the-car-safely ~/.cursor/skills/park-the-car-safely
```

### Manual (project skill)

```bash
mkdir -p .cursor/skills
cp -R /path/to/park-the-car-safely/park-the-car-safely .cursor/skills/park-the-car-safely
```

Works the same under `.agents/skills/` if that is how your workspace is set up.

## Use

In Agent chat:

```text
/park-the-car-safely
```

Or say things like:

- “Park the car safely”
- “Park my car safely”
- “Driver, park the car safely”
- “I drove today — you do the checks”

## Loop

```text
Park progress:
- [ ] 1. Discover scope
- [ ] 2. Ignore unrelated dirty WIP
- [ ] 3. Baseline (YOU run tests + typecheck)
- [ ] 4. Predict P0–P3 (read-only)
- [ ] 5. Fix confirmed P0/P1 only
- [ ] 6. Continuous test loop (fail → fix → re-run)
- [ ] 7. Exhaustive QA (read-only)
- [ ] 8. Blunt report (fixed · leftovers · ship blockers)
```

## Contents

| Path | Purpose |
|------|---------|
| [`park-the-car-safely/SKILL.md`](./park-the-car-safely/SKILL.md) | Main skill — predict methodology + continuous testing |
| [`park-the-car-safely/notification-idempotency.md`](./park-the-car-safely/notification-idempotency.md) | Extra checklist for SMS / WhatsApp / email / in-app send paths |

## License

MIT — use it, fork it, share it.
