# Notification / multi-channel idempotency (park checklist)

Use this when the parked work sends or schedules **SMS, WhatsApp, email, or in-app** follow-ups — especially from cron, webhooks, or “sync” jobs that can overlap.

Multi-channel notify code fails in boring, expensive ways: double texts at 2am, permanent mute after a provider blip, seed users getting real outreach, India DLT silently dropping free-text SMS. During predict, walk the send path with these patterns in mind. During ship checklist, verify ops reality (creds valid in the *target* env, not just locally).

`SKILL.md` is authoritative. Live sends, production mutations, and provider
credential tests require explicit authorization.

## Model the logical event first

Do not begin with “send an SMS.” Begin with the event:

```text
logical event
  → recipient eligibility and consent
  → per-channel plan
  → durable channel claim/outbox
  → provider submission
  → provider acceptance
  → delivery callback or terminal failure
  → reconciliation and user/operator status
```

Define:

- logical event key, e.g. `appointment-reminder:<appointment-id>:24h`;
- recipient and tenant;
- channel-specific idempotency key;
- template/version;
- scheduled window and quiet-hours rule;
- provider message ID;
- durable state and attempt count.

If the event key is unstable, every retry is a new message.

## Per-channel state machine

Prefer explicit durable states:

```text
planned
  → claimed
  → submitted
  → accepted
  → delivered
  → failed_terminal

claimed/submitted → unknown → reconciled → accepted|delivered|failed_terminal
```

Rules:

- `claimed` means a worker owns the attempt, not that the provider received it;
- `submitted` means the request left the process;
- `accepted` means the provider returned an accepted/message ID response;
- `delivered` requires provider delivery evidence where available;
- `unknown` means timeout/connection loss after possible submission;
- never retry `unknown` blindly when the provider may have accepted;
- release a claim only when evidence proves no submission occurred, or a
  provider idempotency key makes retry safe;
- store per-channel state so partial WhatsApp/SMS/email success does not replay
  already-settled channels.

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
| Claim-before-send, ignore channel result | Permanent mute or blind duplicate after timeout | Durable per-channel state; reconcile unknown outcomes; release only known-not-submitted claims |
| Claim release after successful in-app only | Retry re-fires other channels (SMS/WA/email) | Document the tradeoff as leftover P1, or use a per-channel settled column |
| One global `sent_at` for many channels | One success hides another failure; retry duplicates successful channels | Per-channel claims, attempts, provider IDs, and terminal states |
| Random idempotency key per attempt | Every retry is a new provider request | Stable logical-event + channel key, backed by a unique constraint |
| Lease without owner/version | Late worker settles a claim stolen by a newer worker | Lease owner/token checked on settle and release |
| Timeout treated as failed | Provider may have accepted; retry duplicates | `unknown` state + provider lookup/webhook reconciliation |
| Accepted treated as delivered | UI/operator overstates provider result | Separate accepted and delivered states/copy |
| FK join cast as object only | Phone/email silently `undefined` when API returns an array | Shared helper that accepts object \| array |
| Missing seed filter | Seed/demo users get real outreach | Filter seeds out of cron **and** notify guards |
| Category CHECK vs TS union | Deploy code before migration (or drop an enum value) | Keep DB CHECK in sync with the TS union; park should flag drift |
| Cron `maxDuration` too low | Process dies mid-batch after claim → stuck or partial fan-out | Raise duration when fan-out grows; predict should notice claimed-then-killed shapes |
| Free-text SMS → India | DLT registry drop | Messaging Service + approved templates; don’t silently rewire providers without a product ask |

## Consent, policy, and recipient safety

Audit at send time, not only schedule time:

- current opt-in/opt-out and channel preference;
- tenant/clinic ownership;
- seed/demo/test suppression;
- quiet hours and time zone;
- frequency/rate caps;
- template category and regional registration;
- recipient address/phone verification;
- appointment/order still eligible and not cancelled;
- sensitive content minimized for lock-screen/email exposure.

A previously eligible scheduled message can become ineligible before send.

## Provider request and callback

Check:

- provider idempotency key support and retention window;
- timeout boundary and retry policy;
- 400/401/403 terminal handling;
- 429/retry-after handling;
- 5xx/backoff with cap and jitter;
- message ID persistence before local success response;
- webhook signature, timestamp tolerance, replay protection, and event ordering;
- duplicate callbacks;
- delivered callback arriving before accepted persistence;
- terminal failure after initial acceptance;
- reconciliation for messages stuck in `submitted` or `unknown`;
- dead-letter/operator path after retry exhaustion.

## Crash-window and concurrency matrix

Probe in a fake/sandbox unless live sends are explicitly authorized:

| Scenario | Required invariant |
|---|---|
| Two workers claim same event | One channel submission |
| Process dies after claim, before request | Lease recovers; no permanent mute |
| Process dies after provider accepts, before local settle | Reconcile by provider/idempotency key; no blind duplicate |
| Provider times out after receiving request | State becomes unknown; retry is safe or withheld |
| Cron and manual resend overlap | Explicit manual override or one logical winner |
| WhatsApp succeeds, SMS fails | WhatsApp not replayed when SMS retries |
| Callback delivered twice | Terminal state remains stable |
| Failure callback arrives after delivered | Delivered is not regressed |
| User opts out after scheduling | Send is suppressed |
| Appointment cancelled after scheduling | Reminder is suppressed |
| Rate limit mid-batch | Remaining work retries without duplicating settled rows |

Capture provider request count, durable rows, state transitions, and copy—not
only endpoint status.

## Observability without PII leakage

Log:

- logical event ID;
- tenant ID;
- channel;
- attempt number;
- lease owner/token;
- provider message ID;
- state transition;
- normalized provider error class;
- correlation ID.

Do not log message bodies, auth headers, OTPs, full phone/email, medical detail,
or provider secrets. Operators need enough data to reconcile without creating a
second privacy incident.

## Ship checklist (notifications)

Work these as yes/no against the **environment that will actually send**:

1. Migrations applied (idempotency / claim flags + category CHECK).
2. Provider creds present **and** valid in that env (local `.env` ≠ Vercel/prod).
3. `CRON_SECRET` (or equivalent) and the app base URL the cron will hit.
4. Cron entries still point at the right routes after the drive.
5. Region ops ready if going live (e.g. India DLT / sender registration).
6. Auth-check the provider before promising a live demo send — never claim “delivered” on stub/401. Keys present ≠ keys valid.
7. Unique constraint/outbox/idempotency key deployed before overlapping workers.
8. Unknown-outcome reconciliation and dead-letter ownership assigned.
9. Consent, opt-out, quiet-hours, and seed suppression verified in target data.
10. UI/operator wording distinguishes queued, submitted, accepted, and delivered.

## Predict notes specific to notify

- Prefer **confirmed-from-code** findings like “mark sent only after Twilio 201” vs “might double-send somehow.”
- A missing `is_seed` (or equivalent) filter on a cron query is usually at least **P1**, **P0** if the cron is already live.
- Claim-without-release that can mute a user after a transient 5xx is **P1** with a concrete failure mode.
- Blind release/retry after an ambiguous timeout is **P1** because it can
  duplicate a provider-accepted message.
- Missing stable logical-event uniqueness is **P1**, and **P0** when messages
  carry money, medical urgency, OTP/security, or live high-volume outreach.
- Put “prod missing Messaging Service SID” on the ship checklist as speculative until verified — still a blocker for a live demo.
