# Notification / multi-channel idempotency (park checklist)

Use this when the parked work sends or schedules **SMS, WhatsApp, email, or in-app** follow-ups — especially from cron, webhooks, or “sync” jobs that can overlap.

Multi-channel notify code fails in boring, expensive ways: double texts at 2am, permanent mute after a provider blip, seed users getting real outreach, India DLT silently dropping free-text SMS. During predict, walk the send path with these patterns in mind. During ship checklist, verify ops reality (creds valid in the *target* env, not just locally).

## How to audit a notify path

1. Find every entrypoint that can send (cron route, sync job, server action, queue worker).
2. For each channel, ask: **when do we claim?** **when do we mark sent?** **what happens if the provider fails after claim?**
3. Check whether two entrypoints can fan out the same logical event (cron + webhook, retry + manual resend).
4. Check seed/test data filters on every query that leads to send.
5. Check that category enums in TypeScript match DB CHECK constraints (deploy order matters).
6. Never believe UI copy that says “delivered” unless the code checked a real provider success.

## Pattern table

| Pattern | Risk | Prefer |
|--------|------|--------|
| Mark-after-send | Concurrent cron/sync double-sends the same row | Claim-before-send (`UPDATE … IS NULL RETURNING` or equivalent lease) |
| Claim-before-send, ignore channel result | Permanent mute if provider fails after claim | Release claim when send did not settle (or hard-fail with creds present) |
| Claim release after successful in-app only | Retry re-fires other channels (SMS/WA/email) | Document the tradeoff as leftover P1, or use a per-channel settled column |
| FK join cast as object only | Phone/email silently `undefined` when API returns an array | Shared helper that accepts object \| array |
| Missing seed filter | Seed/demo users get real outreach | Filter seeds out of cron **and** notify guards |
| Category CHECK vs TS union | Deploy code before migration (or drop an enum value) | Keep DB CHECK in sync with the TS union; park should flag drift |
| Cron `maxDuration` too low | Process dies mid-batch after claim → stuck or partial fan-out | Raise duration when fan-out grows; predict should notice claimed-then-killed shapes |
| Free-text SMS → India | DLT registry drop | Messaging Service + approved templates; don’t silently rewire providers without a product ask |

## Ship checklist (notifications)

Work these as yes/no against the **environment that will actually send**:

1. Migrations applied (idempotency / claim flags + category CHECK).
2. Provider creds present **and** valid in that env (local `.env` ≠ Vercel/prod).
3. `CRON_SECRET` (or equivalent) and the app base URL the cron will hit.
4. Cron entries still point at the right routes after the drive.
5. Region ops ready if going live (e.g. India DLT / sender registration).
6. Auth-check the provider before promising a live demo send — never claim “delivered” on stub/401. Keys present ≠ keys valid.

## Predict notes specific to notify

- Prefer **confirmed-from-code** findings like “mark sent only after Twilio 201” vs “might double-send somehow.”
- A missing `is_seed` (or equivalent) filter on a cron query is usually at least **P1**, **P0** if the cron is already live.
- Claim-without-release that can mute a user after a transient 5xx is **P1** with a concrete failure mode.
- Put “prod missing Messaging Service SID” on the ship checklist as speculative until verified — still a blocker for a live demo.
