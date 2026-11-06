# Product requirements

## Product thesis and audience

RallyPoint helps Telegram groups answer “will enough people commit by this time?” with one live card. The initial audience is volunteer organisers, study groups, local clubs, and small online communities whose activities need a minimum team. Suggested usernames and positioning are in [ABSTRACT.md](ABSTRACT.md).

The problem is coordination uncertainty: ordinary chat replies scatter commitments, and organisers repeatedly recount them. The solution is a target, a deadline, reversible Join/Leave buttons, and a recorded outcome. The differentiator is threshold-based commitment rather than a general poll, calendar, task manager, or attendance tracker. This is a product hypothesis; no exhaustive competitor research or category exclusivity is claimed.

## Core interaction

1. An organiser adds the bot to a group with Telegram privacy mode enabled.
2. They send `/pact 3 60m | Saturday river cleanup`.
3. The bot posts one card with the title, target, current count, and deadline.
4. Members tap Join. Repeated Join does not add votes. Leave removes the account's vote.
5. Below the target, the card is OPEN. At or above it, the card is READY, meaning provisional quorum. A departure can return it to OPEN.
6. At the deadline the card becomes MET or MISSED. Subsequent joins and departures are rejected. The organiser uses the existing group conversation to coordinate the activity.

The organiser is not automatically counted. They must tap Join if participating. The title describes the activity; the deadline is the commitment cutoff, not necessarily the activity start time. The product does not promise attendance or automatically book anything.

## Capabilities and boundaries

| Capability | Acceptance behaviour |
|---|---|
| Create pact | Group/supergroup command, target 2–100, duration 1 minute–7 days, title 1–200 characters |
| Participate | One vote per account and card; Join and Leave are idempotent intents |
| Live status | Durable updates reconcile the Telegram message after transient failures |
| Deadline | Settle using stored UTC time even after a process restart |
| Cancel | Creator or freshly verified group administrator; terminal state |
| Browse | `/pacts` lists current pacts in the current chat |
| Topics | Creation preserves the originating forum topic for replies |
| Privacy | No participant names displayed; scoped HMAC keys stored instead of participant IDs |
| Erasure | Private `/forget` removes the caller's retained participation and creator references |
| Operations | Private operator diagnostics, JSON logs, local health command, retention cleanup |

The bot creates at most 20 active cards per chat and bounds global active storage. No Mini App, inline mode, reactions, webhooks, payment flow, reminders by direct message, or user-authorised Telegram client is needed.

## Journeys, onboarding, settings, and lifecycle

**First-time member:** `/start` or `/help` explains conditional participation and provides the command example. A group invite is handled by Telegram; the bot does not import contacts. The operator configures a public bot username through BotFather.

**Organiser:** Add the bot, create a pact, share the existing card within the group, monitor progress, and cancel if plans change. A forwarded or copied card is not a portable voting endpoint: the originating chat binding is enforced.

**Member:** Read the title and cutoff, tap Join, change their mind with Leave, and see the final outcome. No website, email, password, or separate account registration is required. Telegram's update supplies the account identity used for authorisation.

**Privacy-conscious member:** Read `/privacy`, open a private chat with the bot, and issue `/forget`. This removes retained personal references across cards. It does not delete existing Telegram messages, Telegram's records, operator backups, or reverse an already finalised aggregate outcome. Forgetting ownership can leave a card administrable only by group administrators.

**Operator:** Set environment policy, start one process, inspect health, and review logs. `/settings` displays policy; it does not change global configuration. Operators change retention and logging through environment configuration and restart.

## Telegram surface

The complete command and callback contract is in [COMMANDS.md](COMMANDS.md). Commands support Telegram's `@botusername` suffix. Buttons are Join, Leave, Refresh, and Cancel. Refresh reads current server state. No callback grants authority merely by knowing a card ID.

## Privacy and security

The bot does not publish a roster. It stores necessary card titles and routing metadata; participant and creator references are HMAC-derived separately for each card. Those are pseudonymous, not anonymous: the operator possesses the HMAC secret, and Telegram delivers raw account IDs during processing. No claim of unlinkability against the operator is made. See [SECURITY.md](SECURITY.md) and [THREAT_MODEL.md](THREAT_MODEL.md).

## Commercial and growth hypothesis

The free interaction is the acquisition channel: one organiser introduces a card to many potential organisers. Repeat weekly activities create retention. A future paid community plan could add recurring templates, opt-in organiser analytics, larger operating quotas, and managed hosting. No billing, subscriptions, tracking pixels, or promotional messages are implemented. Pricing should follow willingness-to-pay interviews, not precede them.

The strongest first customer is an organisation coordinating several recurring groups. A managed-hosting pilot can charge for setup and support before adding product complexity. Public results should be aggregated only with community consent.

## Measurable success criteria

These are proposed pilot targets, not observed results:

- At least 10 communities run 3 or more real pacts each over 4 weeks.
- At least 50% of participating organisers create another pact within 14 days.
- At least 30% of valid pacts reach their target by the deadline.
- In interviews, a majority of organisers report less recounting or follow-up effort.
- Median healthy-network callback response under 2 seconds; no lost stored votes in restart tests.
- Zero unauthorised cross-chat mutations in automated tests and pilot incident review.
- No tokens, message bodies, chat IDs, or user IDs in application logs under tested paths.

These measurements require consented pilot collection. The MVP's operational counters do not track an individual's behaviour across groups. Attendance and causal improvement require organiser follow-up; the bot cannot infer them.
