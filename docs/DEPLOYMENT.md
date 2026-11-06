# Deployment

## Requirements and credentials

Use a single Debian Linux host with Python 3.12+, `uv`, outbound HTTPS to `api.telegram.org`, a persistent local filesystem, and a BotFather token. The bot uses long polling, so there is no inbound port. Leave BotFather privacy mode enabled; commands and button callbacks suffice. The bot needs no chat administrator privileges for normal cards. `getChatMember` verifies a group administrator attempting to cancel someone else's card; if Telegram cannot verify the role, cancellation fails safely.

Set `BOT_TOKEN` to a BotFather token and `IDENTITY_SECRET` to 32 cryptographically random bytes encoded as 64 hex digits. Generate the latter once with `python3 -c 'import secrets; print(secrets.token_hex(32))'`. Keep it with database backups: changing it invalidates matching of retained votes and creators. `DATABASE_PATH` defaults to `data/rallypoint.sqlite3`. `RETENTION_DAYS` may be 1–90. `ADMIN_IDS` is an optional comma-separated list of numeric Telegram account IDs for private diagnostics. No other external service or credential is required.

Install and run from the extracted archive:

```bash
./scripts/install.sh
cp .env.example .env
chmod 600 .env
# Edit BOT_TOKEN and IDENTITY_SECRET in .env
set -a
. ./.env
set +a
.venv/bin/python -m telegram_innovation check-config
./scripts/run.sh
```

The archive includes `uv.lock`; `install.sh` uses `uv sync --frozen --no-dev`. The first install still needs package-index access unless the required wheels are already cached. `check-config` validates syntax without contacting Telegram. Startup calls `getMe` and checks that no webhook is configured. If a webhook exists, remove it deliberately with the Bot API before starting polling; the bot does not silently change an existing deployment. An invalid token, competing polling process, or missing Telegram access stops the service with a structured error event.

## Dedicated service account

The included [service unit](../deploy/rallypoint.service) runs as a non-root `rallypoint` user, restricts writes to `/var/lib/rallypoint`, and expects project files in `/opt/rallypoint` and environment variables in `/etc/rallypoint.env`. Place the Python interpreter and virtual environment under `/opt/rallypoint` so systemd's home-directory restrictions do not hide them. The environment file must be owned by root and mode `0600`. The SQLite file and containing directory must be writable by `rallypoint`; use a local disk. Review [deploy/README.md](../deploy/README.md) for exact systemd commands.

One process per database/token is required. A lock file next to the database prevents two local workers sharing it. Do not run a webhook consumer and the polling worker against the same bot token. On SIGTERM/SIGINT the process closes its HTTP client and database. A stopped bot settles deadlines when it resumes; members will see stale cards during downtime.

## Operations

`DATABASE_PATH=/var/lib/rallypoint/rallypoint.sqlite3 .venv/bin/python -m telegram_innovation health` performs a read-only SQLite quick check. It reports database integrity only, not Telegram reachability or worker liveness. Configured operator accounts can send `/diagnostics` in a private chat for aggregate database counts. Logs are JSON to stderr; set `LOG_FILE` for a 1 MiB rotating file with five backups. Set `LOG_LEVEL` to DEBUG/INFO/WARNING/ERROR/CRITICAL. Even DEBUG excludes raw updates, HTTP URLs, credentials, and exception text. Journal or host-level retention is the operator's responsibility.

Back up the SQLite database with SQLite's online backup command/API, including WAL consistency, and protect the identity secret separately with equivalent access controls. Do not copy a live database file without a consistent backup method. Restore both together. No automatic database downgrade is supported; migrations run forward on startup. Terminal card rows are purged hourly once their deadline is older than configured retention. Telegram messages and your backup copies need their own deletion policy.

If Telegram replies 429, the worker honors `retry_after` up to 3600 seconds. Transient failures back off, preserving committed card changes for later reconciliation. `sendMessage` can be ambiguous across network errors or a crash; inspect the group if a duplicate card appears. Permanent 400/403 delivery failures retire that card's pending edit, as the original destination may be gone. In that case, create a new card if needed. See [ARCHITECTURE.md](ARCHITECTURE.md) and [THREAT_MODEL.md](THREAT_MODEL.md) for the consistency and privacy boundaries.
