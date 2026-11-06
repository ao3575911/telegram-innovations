# RallyPoint

**I’m in if enough others are.** RallyPoint gives Telegram groups one shared card for a conditional commitment. Create a card with `/pact 3 60m | Saturday park cleanup`; members tap **I’m in** or **Leave**. The target can be met and reopened before the deadline. At the deadline, the bot records whether the target was met.

This is useful when a plan only works with a minimum team: study sessions, community repairs, game nights, volunteer shifts, and neighborhood projects. A Join tap records intent, not attendance. The bot shows counts without a public member list. Telegram and the operator still receive account identifiers during Bot API interactions; RallyPoint makes no anonymity claim.

## Install on one Linux machine

Requires Python 3.12+, [uv](https://docs.astral.sh/uv/getting-started/installation/), outbound HTTPS to Telegram, and a token from [@BotFather](https://t.me/BotFather). No AI account, cloud database, domain, webhook, or administrator rights in the group are required. Keep BotFather privacy mode enabled. Set the bot's command list automatically at startup.

```bash
unzip telegram-innovation.zip
cd telegram-innovation
./scripts/install.sh
cp .env.example .env
chmod 600 .env
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

Put the BotFather token in `BOT_TOKEN` and the generated 64-character hex value in `IDENTITY_SECRET` inside `.env`. Protect both. Then run:

```bash
set -a
. ./.env
set +a
.venv/bin/python -m telegram_innovation check-config
./scripts/run.sh
```

In a group with the bot, send `/pact 3 60m | Saturday park cleanup`. The title may contain up to 200 characters. Targets are 2–100 people and durations are 1 minute–7 days (`m`, `h`, `d`). `/pacts` lists active cards; the creator or a verified group administrator may `/cancel CARD_ID`. `/forget` works in a private chat with the bot and erases your retained participation/ownership references. `/privacy`, `/settings`, `/help`, and `/start` explain the policy and commands. Optional `ADMIN_IDS` grants private `/diagnostics` access to named operator accounts.

`./scripts/check.sh` runs formatting, lint, type checks, and all tests using the committed lockfile. `DATABASE_PATH=data/rallypoint.sqlite3` is the default. `.env` is trusted shell syntax and is deliberately not loaded automatically by the bot or scripts. See [deployment](docs/DEPLOYMENT.md) for systemd, backups, health checks, and troubleshooting.

## How it works

The single polling process uses the standard Telegram Bot API over HTTPS and a local SQLite database. Updates are processed sequentially. Card creation and votes are idempotent in storage; a durable dirty flag retries card edits after transient failures. Telegram has no idempotency key for outbound `sendMessage`, so a crash after Telegram accepts a send but before its message ID is stored can duplicate a card. The bot does not claim exactly-once message delivery.

The database stores card titles, required routing IDs, deadlines, aggregate counts, and per-card HMAC pseudonyms for creators and participants. Raw participant IDs, names, usernames, and unrelated messages are not stored. The operator can infer a pseudonym if they already know the account ID and secret. Titles are intentionally persisted and should not contain secrets. Final records are purged after `RETENTION_DAYS` (default 7); Telegram messages and external backups have separate retention. Logs use an allowlist of event fields and never include update bodies or token-bearing URLs.

The MVP is intended for one Debian host and modest group usage. It has not been validated against a live Telegram account in this build. See [product definition](docs/PRD.md), [architecture](docs/ARCHITECTURE.md), [security model](docs/SECURITY.md), [concept decision](docs/CONCEPTS.md), and [test report](docs/TEST_REPORT.md).

MIT licensed. Contributions should preserve the explicit API and privacy limits described in the docs.
