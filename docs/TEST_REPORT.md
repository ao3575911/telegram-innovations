# Implementation and validation report

Build environment: Linux, Python 3.12.14, `uv` 0.13.4. This report records executed checks for the repository delivery; it does not certify a live service or market fit.

## Delivered

RallyPoint provides a group commitment card with a target and deadline, idempotent Join/Leave intent, provisional READY status, terminal MET/MISSED/CANCELLED states, creator or verified administrator cancellation, private `/forget`, private operator diagnostics, and standard Bot API polling. Its SQLite store has a versioned initial migration, durable update offset, duplicate-create guard, dirty-card reconciliation, bounded active cards, and retention. The package also includes configuration validation, JSON event logging with an allowlist, rate limiting, a Bot API adapter, native Linux scripts, a systemd unit, CI, and product/security/architecture documentation.

## Executed checks

| Check | Result |
|---|---|
| `uv lock` and `uv sync --frozen` | Resolved and installed successfully with network access |
| `./scripts/check.sh` | Passed: Ruff lint and format, mypy for 17 source files, pytest 72 tests |
| Command and callback flows | Mocked create/replay, join/leave, refresh, topic routing, owner/admin cancellation, private erasure, diagnostics |
| Security and failures | Tested cross-chat/message binding, malformed updates, 400/403 administrator verification denial, 429 and timeout transport, rate limits, token/content exclusion from logs |
| Shell syntax and Python compilation | `bash -n` and `compileall` passed |
| CLI smoke | Valid synthetic configuration accepted; missing database health exits 2; initialized database health reports ok |
| Build artifact | `uv build --offline --no-sources` produced source distribution and wheel; wheel contains SQL migration |

The tests use synthetic accounts and an HTTP mock. They do not send requests to Telegram. Unit tests exercise database state and permissions; integration tests exercise bot handlers with a recording API; transport tests exercise HTTP serialization and error classification with `httpx.MockTransport`.

## Remaining validation and limits

No real BotFather token, live group, or Telegram service was used. Live posting rights, command visibility under privacy mode, administrator lookup on real groups, group migration, message deletion, Bot API rate limits at scale, and worker recovery during a real outage remain unverified. The included systemd service has not been started on Debian here; this container cannot run systemd verification because `/run/systemd` is read-only. A pilot on a dedicated host should exercise these cases before relying on it for consequential coordination.

The bot does not guarantee attendance, exactly-once outbound message creation, anonymity from Telegram or the operator, or immediate display during an outage. An ambiguous initial send can produce a duplicate card. Permanently inaccessible messages are retired from reconciliation to prevent a backlog; a replacement card must then be created. Backups and Telegram's messages need their own retention policy.

## Recommended next milestone

Run a four-week consented pilot with at least 10 recurring communities. Verify deployment on a real Debian host and measure repeated use, completed activities, and organiser time saved. Interview organisers before building recurring templates or a paid managed-hosting plan.
