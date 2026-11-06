"""Validated environment configuration; never render configuration objects."""

import os
import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Config:
    token: str = field(repr=False)
    secret: bytes = field(repr=False)
    database_path: str = "data/rallypoint.sqlite3"
    log_level: str = "INFO"
    log_file: str | None = None
    retention_days: int = 7
    admin_ids: frozenset[int] = frozenset()

    @classmethod
    def from_env(cls) -> "Config":
        token = os.environ.get("BOT_TOKEN", "")
        secret = os.environ.get("IDENTITY_SECRET", "")
        if not re.fullmatch(r"[0-9]{5,15}:[A-Za-z0-9_-]{20,100}", token):
            raise ValueError("BOT_TOKEN must be a BotFather token")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", secret):
            raise ValueError("IDENTITY_SECRET must be 32 random bytes encoded as 64 hex characters")
        level = os.environ.get("LOG_LEVEL", "INFO").upper()
        if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("LOG_LEVEL is invalid")
        try:
            retention = int(os.environ.get("RETENTION_DAYS", "7"))
            admins = frozenset(
                int(v.strip()) for v in os.environ.get("ADMIN_IDS", "").split(",") if v.strip()
            )
        except ValueError:
            raise ValueError("RETENTION_DAYS and ADMIN_IDS must be integers") from None
        if not 1 <= retention <= 90 or any(v <= 0 for v in admins):
            raise ValueError("Retention must be 1..90 days; administrator IDs must be positive")
        path = os.environ.get("DATABASE_PATH", "data/rallypoint.sqlite3")
        if not path or path == ":memory:":
            raise ValueError("DATABASE_PATH must be a persistent filesystem path")
        return cls(
            token,
            bytes.fromhex(secret),
            path,
            level,
            os.environ.get("LOG_FILE") or None,
            retention,
            admins,
        )
