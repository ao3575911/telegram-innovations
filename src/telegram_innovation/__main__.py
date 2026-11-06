"""CLI, single-worker lease, polling, reconciliation, and graceful shutdown."""

import argparse
import asyncio
import fcntl
import json
import logging
import os
import signal
import sys
import time
from pathlib import Path

from telegram_innovation.bot.app import Bot
from telegram_innovation.core.config import Config
from telegram_innovation.integrations.telegram import TelegramAPI, TelegramError
from telegram_innovation.observability.logging import configure
from telegram_innovation.storage import Store

LOG = logging.getLogger(__name__)


async def run(config: Config) -> None:
    store = Store(config.database_path, config.secret)
    api = TelegramAPI(config.token)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    try:
        me = await api.call("getMe")
        webhook = await api.call("getWebhookInfo")
        if not isinstance(me, dict) or not isinstance(me.get("username"), str):
            raise TelegramError(0)
        if not isinstance(webhook, dict) or webhook.get("url"):
            raise ValueError(
                "Polling requires an empty webhook; remove it deliberately before starting"
            )
        bot = Bot(config, store, api, username=me["username"])
        await api.call(
            "setMyCommands",
            commands=[
                {"command": "start", "description": "How RallyPoint works"},
                {"command": "pact", "description": "Create: 3 60m | Your plan"},
                {"command": "pacts", "description": "Active group cards"},
                {"command": "cancel", "description": "Cancel a card by its ID"},
                {"command": "privacy", "description": "Data and privacy policy"},
                {"command": "forget", "description": "Erase your participation records privately"},
                {"command": "settings", "description": "Operator policy"},
                {"command": "help", "description": "Commands and examples"},
            ],
        )
        LOG.info("", extra={"event": "startup"})
        retry_until = 0.0
        failures = 0
        next_purge = 0.0
        while not stop.is_set():
            store.tick()
            if time.monotonic() >= next_purge:
                count = store.purge(int(time.time()) - config.retention_days * 86400)
                LOG.info("", extra={"event": "retention_sweep", "count": count})
                if store.health()["database"] != "ok":
                    raise RuntimeError("Database integrity check failed")
                LOG.info("", extra={"event": "database_healthy"})
                next_purge = time.monotonic() + 3600
            if time.monotonic() >= retry_until:
                try:
                    await bot.reconcile()
                    updates = await api.call(
                        "getUpdates",
                        offset=store.get_offset(),
                        timeout=10,
                        limit=50,
                        allowed_updates=["message", "callback_query"],
                    )
                    if not isinstance(updates, list):
                        raise TelegramError(0)
                    for update in updates:
                        if stop.is_set():
                            break
                        if isinstance(update, dict):
                            await bot.handle(update)
                    failures = 0
                except TelegramError as exc:
                    LOG.warning("", extra={"event": "api_failure", "error_code": exc.code})
                    if exc.code in {401, 404, 409}:
                        raise
                    failures += 1
                    delay = exc.retry_after or min(60, 2 ** min(failures, 6))
                    retry_until = time.monotonic() + delay
            try:
                await asyncio.wait_for(
                    stop.wait(), timeout=min(5, max(0.05, retry_until - time.monotonic()))
                )
            except TimeoutError:
                pass
    finally:
        await api.close()
        store.close()
        LOG.info("", extra={"event": "shutdown"})


def main() -> None:
    os.umask(0o077)
    parser = argparse.ArgumentParser(description="RallyPoint conditional commitment bot")
    parser.add_argument(
        "command", choices=["run", "check-config", "health"], nargs="?", default="run"
    )
    args = parser.parse_args()
    try:
        if args.command == "health":
            # Health probes don't need the Telegram credential or identity key.
            path = Path(os.environ.get("DATABASE_PATH", "data/rallypoint.sqlite3"))
            if not path.is_file():
                raise ValueError("Database does not exist; health checks never create one")
            import sqlite3

            connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=5)
            try:
                result = connection.execute("PRAGMA quick_check").fetchone()
                if result != ("ok",):
                    raise ValueError("Database integrity check failed")
                connection.execute("SELECT count(*) FROM cards").fetchone()
            finally:
                connection.close()
            print(
                json.dumps(
                    {"database": "ok", "scope": "database only; not Telegram or worker liveness"}
                )
            )
            return
        config = Config.from_env()
        configure(config.log_level, config.log_file)
        if args.command == "check-config":
            print("Configuration is valid (credentials have not been checked against Telegram).")
            return
        destination = Path(config.database_path)
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with Path(str(destination) + ".lock").open("a") as lease:
            try:
                fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError("Another worker already holds this database lease") from None
            asyncio.run(run(config))
    except ValueError as exc:
        # Only locally produced configuration errors reach this branch.
        configure()
        LOG.error("", extra={"event": "configuration_failure"})
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from None
    except Exception:
        configure()
        LOG.error("", extra={"event": "fatal_failure"})
        print(
            "Startup/runtime failed. Inspect structured events and the deployment runbook.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
