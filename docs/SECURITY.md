# Security and privacy

## Trust model

Telegram authenticates accounts and transports updates. The bot trusts Telegram HTTPS responses and the local host. Telegram and the operator can observe identities and interactions. A visible aggregate is not a privacy proof, an anonymous ballot, or an attendance guarantee.

The bot needs ordinary membership and permission to send messages in its group/topic. Keep BotFather privacy mode enabled. Do not grant administrator rights unless a separately reviewed future feature needs them. Cancellation by someone other than the creator requires a current administrator check; failure to verify must deny that path.

## Data inventory

| Data | Purpose | Handling |
|---|---|---|
| Pact title | Render the activity | Stored; never deliberately logged; tell users not to include secrets |
| Chat, topic, and message IDs | Deliver and update the card | Stored locally; not application log fields |
| Scoped participant/creator HMAC | One vote per account, ownership, forgetting | Stored; no raw account ID in vote rows |
| Target, count, status, timestamps | Quorum computation | Stored until retention cleanup |
| Polling offset and creation update ID | Restart and duplicate handling | Operational database metadata |
| Raw Telegram update | Command authorisation | Processed in memory; not stored as a raw object |
| Bot token and HMAC secret | API access and identity derivation | Environment/configuration only; never commit |
| Operator account IDs | Restrict diagnostics | Environment configuration; not public diagnostics |

Scoped HMACs reduce casual database correlation. They do not protect against an operator with the secret, a compromised running process, or guessing account IDs with the secret. Use a random 32-byte secret represented as 64 hexadecimal characters. Keep it stable with the database: changing it makes previous ownership and membership unrecognisable. Restore database and secret together; there is no transparent key-rotation migration in this MVP.

## Erasure and retention

Private `/forget` removes the caller's retained participation rows and creator references across cards. Active counts can change; final aggregate outcomes retain their historical meaning. The command does not remove already sent Telegram messages, Telegram's own storage, logs outside this application, or backups. Creator erasure relinquishes creator cancellation rights; administrators retain their authorised path.

Terminal-card retention defaults to 7 days. Retention runs while the bot is operating, so an offline database does not erase itself. Restrict and expire backups separately. Filesystem encryption and encrypted backups are operator choices, not supplied cryptographic guarantees.

## Controls

- Validate command length, target range, duration, title characters, callback version, action, and card identifier.
- Bind mutations to the stored originating chat; do not trust a forwarded card or callback text as authority.
- Send dynamic text without a Telegram parse mode and use parameterised SQL.
- Rate-limit interactive actions and cap active cards. Multiple Telegram accounts can still coordinate abuse.
- Use explicit outbound HTTPS methods, TLS verification, and timeouts. No arbitrary URL fetching occurs.
- Persist vote intent transactionally. Repeated Join and Leave have stable meaning.
- Avoid raw exception text and update bodies in logs; redact sensitive tokens and fields at the logging boundary.
- Restrict diagnostics to configured operators in private chat. Operator configuration does not grant pact-owner privileges.

## Host and secret operations

Run as a dedicated account. Restrict the environment file and data directory to that account. Do not pass secrets in shell command arguments, put them in screenshots, enable HTTP wire debugging, or publish database backups. Copy `.env.example` to a private local file and configure real credentials there.

If the bot token leaks, revoke it with BotFather and replace it. If the identity secret leaks, treat stored membership privacy as compromised and plan a documented database reset or reviewed migration. If the host is compromised, redeploy from a trusted host rather than assuming a token change is enough.

Report suspected defects privately to the deployment operator or repository maintainer using their published contact route. This project does not invent a security contact address. Include a minimal reproduction without real credentials or participant data.

The repository is production-oriented, not independently audited or certified production-ready. See [THREAT_MODEL.md](THREAT_MODEL.md) and the validation report.
