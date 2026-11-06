# RallyPoint

**Tagline:** Enough of us? Then let's do it.

RallyPoint turns “I'd help if enough people joined” into a visible, time-bounded commitment. In a Telegram group, an organiser posts a pact with a target and deadline. Members tap Join or Leave. A single shared card shows progress, becomes provisionally ready at the target, and closes with a clear outcome at the deadline.

The product addresses a coordination problem rather than a scheduling problem: people hesitate to commit to activities that require a minimum viable team. Volunteer shifts, neighbourhood cleanups, study sessions, shared practice, and community projects all suffer from repeated “who's interested?” messages with ambiguous outcomes. A conditional commitment card gives the group a common decision rule.

The signature capability is **a quorum that can be joined, withdrawn from, and settled on one Telegram message**. Counts are public; participant names are not published by the bot. This is a privacy-conscious interaction, not an anonymity system. Telegram receives user identities, and the operator handles updates containing those identities.

RallyPoint uses Python 3.12+, SQLite, and the standard Telegram Bot API. It runs on one Debian Linux machine without AI services, a public webhook endpoint, an external database, or bot administrator privileges. The deliverable is a working MVP with deployment materials and automated validation. Actual attendance, commercial demand, and live Telegram reliability remain pilot questions.

Suggested usernames, subject to availability: `RallyPointPactsBot`, `OurQuorumBot`, `EnoughOfUsBot`.

See [concept selection](CONCEPTS.md), [product definition](PRD.md), and [validation evidence](TEST_REPORT.md).
