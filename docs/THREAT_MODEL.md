# Threat model

Assets: bot token, identity secret, participant privacy, correct quorum counts, creator/admin permissions, service availability, and database integrity. Actors: ordinary members, malicious members, users outside a group, Telegram, the bot operator, and a host attacker.

| Threat | Boundary and mitigation | Residual risk |
|---|---|---|
| Callback replay or double-click inflation | Join/Leave set membership; unique scoped vote key; state checked in a transaction | A user can deliberately alternate intent |
| Card ID guessing | Match callback chat to stored chat and recheck action authority | IDs are not treated as authentication secrets |
| Forwarded card voting | Origin chat binding; original-message checks where available | Forwarded copies can remain visually stale |
| Unauthorised cancellation | Creator HMAC or live group-admin lookup | Compromised creator/admin accounts have their normal power |
| Faked admin response or network failure | Trust only Telegram HTTPS response; deny when verification fails | Telegram and host are trusted dependencies |
| Deadline race | Check server time during mutation and settlement | Bad host time affects cutoffs; use system time synchronisation |
| Polling replay after restart | Persistent offset; creation update uniqueness; intent operations | Outbound sends can duplicate across the send/persist crash window |
| Message/card tampering | Server stores authoritative target and status; escaped rendering | Host compromise defeats local integrity |
| Spam and quota exhaustion | Rate limits, input limits, active-card caps, retention | Sybil accounts and large-scale floods remain possible |
| SQL injection and markup injection | Parameterised statements; no parse mode for dynamic text | New renderers and queries need the same discipline |
| Token leakage via API exceptions | Sanitised structured events, redaction, no raw HTTP logs | External proxies, system tooling, or operator debug changes may leak |
| Membership correlation from DB | Per-card HMAC rather than raw participant IDs | Operator can recompute keys; timestamps/count changes reveal information |
| Small-group inference | Do not publish participant names | Observing one new count or a public Join announcement can identify a voter |
| Secret loss or rotation | Back up secret with DB under restricted access | No seamless key rotation; old votes become unrecognisable |
| Deleted card or lost posting rights | API errors deferred/handled without corrupting votes | UI may remain unavailable until permissions restored |
| Database growth and old personal data | Terminal retention and bounded active cards | Offline databases and unmanaged backups do not self-purge |
| Supply-chain compromise | Minimal runtime dependency, exact lockfile, CI checks | Pinning is not an audit; updates still require review |
| False confidence in attendance | Explicit provisional and final quorum wording | Members may fail to attend despite a commitment |

Out of scope: preventing Telegram from observing users, strong anonymity, one-human-one-vote, secret ballots, payment escrow, compulsory attendance, hostile-host confidentiality, and access to private Telegram information unavailable to a bot. No custom cryptographic primitives are implemented. HMAC-SHA256 is used only for scoped pseudonyms, not as a claim of zero knowledge.

Before a public pilot, test a removed bot, revoked posting rights, a migrated group, administrator changes, callback delivery after the deadline, and restart during an API outage. These require live Telegram behaviour and complement mocked tests.
