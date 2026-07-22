# Notification / multi-channel idempotency (park checklist)

Use when parking SMS / WhatsApp / email / in-app follow-ups.

| Pattern | Risk | Prefer |
|--------|------|--------|
| Mark-after-send | concurrent cron/sync double-sends | Claim-before-send (`UPDATE … IS NULL RETURNING`) |
| Claim-before-send, ignore channel result | permanent mute if provider fails | Release claim when send didn't settle |
| Claim release after successful in-app | retry re-fires other channels | Document tradeoff or separate settled column |
| FK join cast as object only | phone silently undefined | Shared helper for object \| array |
| Missing seed filter | seed data gets real outreach | Filter seeds out of cron + notify |
| Category CHECK vs TS union | deploy without migration | Keep DB CHECK in sync with TS |
| Cron `maxDuration` too low | mid-batch kill after claim | Raise when fan-out grows |
| Free-text SMS → India | DLT drop | Messaging Service + approved content |

## Ship checklist (notifications)

1. Migrations applied (idempotency flags + category CHECK)
2. Provider creds present **and** valid in the target env (local ≠ Vercel)
3. `CRON_SECRET`, app URL
4. Cron entries point at the right routes
5. Region ops (e.g. India DLT) if going live
6. Never claim "delivered" on stub/401 — auth-check first
