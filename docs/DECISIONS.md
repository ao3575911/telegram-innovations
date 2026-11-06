# Architecture and product decisions

| Decision | Evidence and trade-off |
|---|---|
| Conditional commitment as core | A concrete recurring coordination problem maps to one shared Telegram card; validate demand in a pilot |
| Reversible READY state | Members can withdraw before cutoff; avoids silently locking a casual click into an irrevocable promise |
| Deadline settlement | Produces an explicit decision; deadlines are processed after recovery if offline |
| Separate Join and Leave | Intent is naturally idempotent under duplicate callbacks; a toggle is not |
| Count-only public cards | Reduces roster exposure and social pressure; participants still need the group conversation to organise |
| Per-card HMAC identity | Avoids raw participant IDs in vote storage using standard HMAC; operator anonymity is not claimed |
| Store title and routing metadata | Required to restore cards after restart; explicitly disclosed rather than claiming content-free storage |
| Python 3.12 and one HTTP dependency | Async transport and SQLite without a large bot framework; application owns a small, explicit API adapter |
| SQLite WAL and one worker | Easy to audit and deploy on Debian; not a multi-node architecture |
| Polling | No public webhook or TLS endpoint to operate; only one polling worker per bot |
| Dirty-card reconciliation | Recoverable edits and persistent intent; outbound send exactly-once delivery remains impossible to promise |
| Group privacy mode and ordinary membership | Commands and callbacks suffice; no need to read the full conversation |
| Verify non-owner cancellation with Telegram | Local claims do not establish group-admin status; API failures deny access |
| `/forget` in private chat | Avoids exposing a privacy action to the group and provides one authenticated account context |
| Retention after terminal state | Limits accumulation while keeping short-term outcomes available; backups require separate expiry |
| No AI, custom proofs, Mini App, or payment | None improves the essential quorum action enough to justify cost, credentials, or new trust boundaries |
| Pinned dependencies and packaged tests | Reproducible reviewable installation; pins need deliberate updates rather than permanent neglect |

Revisit decisions with measured pilot evidence. Platform constraints are not roadmap promises: no Bot API-only design can atomically transfer usernames, guarantee anonymity from Telegram, scrape private accounts, or infer attendance from a click.
